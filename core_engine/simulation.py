"""
游戏模拟整合层

基于行动结束触发的模拟系统：
- 角色空闲时触发AI决策
- 所有角色忙碌时，时间跳跃到最近的行动结束点
- AI自主决定睡眠、活动等（根据疲劳、环境）
"""

import asyncio
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import heapq

from .engine import GameTime
from .environment.world import World, WorldConfig
from .character.agent import CharacterAgent, AgentManager, AgentState


class SimulationState(str, Enum):
    """模拟状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class AgentTask:
    """
    角色任务
    
    记录角色当前正在执行的行动及结束时间
    """
    character_id: int
    action_name: str
    action_data: Dict[str, Any]
    start_time: int          # 开始时间（总分钟数）
    end_time: int            # 结束时间（总分钟数）
    
    def __lt__(self, other):
        """用于堆排序"""
        return self.end_time < other.end_time


@dataclass
class SimulationConfig:
    """模拟配置"""
    # 最大时间跳跃（防止无限等待）
    max_time_skip: int = 480  # 最多跳8小时
    
    # 决策超时（秒）
    decision_timeout: float = 60.0
    
    # 是否启用详细日志
    verbose: bool = True
    
    # 初始游戏时间
    initial_day: int = 1
    initial_hour: int = 8
    initial_minute: int = 0


class GameSimulation:
    """
    游戏模拟器（基于行动结束触发）
    
    核心逻辑：
    1. 角色空闲时 → 调用LLM决策下一步行动
    2. LLM返回行动（含预计时长）→ 角色进入忙碌
    3. 所有角色都忙碌 → 时间跳到最近的结束时间
    4. 有角色变空闲 → 回到步骤1
    """
    
    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        world_config: Optional[WorldConfig] = None,
        db_session_factory: Optional[Callable] = None
    ):
        self.config = config or SimulationConfig()
        self._db_session_factory = db_session_factory
        
        # 核心组件
        self.world = World(world_config)
        self.agent_manager = AgentManager.get_instance()
        
        # 游戏时间
        self._game_time = GameTime.from_hm(
            self.config.initial_day,
            self.config.initial_hour,
            self.config.initial_minute
        )
        
        # 状态
        self._state = SimulationState.STOPPED
        self._initialized = False
        
        # 任务堆（按结束时间排序）
        self._task_heap: List[AgentTask] = []
        
        # 角色状态跟踪
        self._agent_tasks: Dict[int, Optional[AgentTask]] = {}  # character_id -> current_task
        
        # 回调
        self._on_action_start_callbacks: List[Callable] = []
        self._on_action_end_callbacks: List[Callable] = []
        self._on_time_advance_callbacks: List[Callable] = []
        
        # 运行控制
        self._stop_flag = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
    
    @property
    def game_time(self) -> GameTime:
        return self._game_time
    
    @property
    def is_running(self) -> bool:
        return self._state == SimulationState.RUNNING
    
    @property
    def is_paused(self) -> bool:
        return self._state == SimulationState.PAUSED
    
    # ===== 初始化 =====
    
    async def initialize(self, db_session=None):
        """初始化模拟器"""
        if self._initialized:
            return
        
        # 初始化世界
        self.world.initialize(db_session)
        
        self._initialized = True
        self._log(f"Simulation initialized at {self._game_time}")
    
    async def add_character(
        self,
        character_id: int,
        initial_x: float = 250.0,
        initial_y: float = 250.0,
        initial_location_id: Optional[int] = None
    ) -> CharacterAgent:
        """添加角色到模拟"""
        db_session = self._db_session_factory() if self._db_session_factory else None
        
        try:
            agent = await self.agent_manager.create_agent(character_id, db_session)
            agent.set_world(self.world)
            
            # 设置初始位置
            self.world.set_character_position(
                character_id, initial_x, initial_y, initial_location_id
            )
            
            # 更新时间
            agent.update_game_time(
                self._game_time.day,
                f"{self._game_time.hour:02d}:{self._game_time.minute:02d}",
                initial_location_id
            )
            
            # 初始状态：空闲（无任务）
            self._agent_tasks[character_id] = None
            
            self._log(f"Added character: {agent.profile.name} (ID: {character_id})")
            return agent
            
        finally:
            if db_session:
                db_session.close()
    
    async def remove_character(self, character_id: int):
        """移除角色"""
        # 移除任务
        self._agent_tasks.pop(character_id, None)
        self._task_heap = [t for t in self._task_heap if t.character_id != character_id]
        heapq.heapify(self._task_heap)
        
        await self.agent_manager.remove_agent(character_id)
        self._log(f"Removed character: {character_id}")
    
    # ===== 主循环 =====
    
    async def start(self):
        """启动模拟"""
        if not self._initialized:
            await self.initialize()
        
        self._state = SimulationState.RUNNING
        self._stop_flag = False
        self._log("Simulation started")
        
        await self._main_loop()
    
    async def stop(self):
        """停止模拟"""
        self._stop_flag = True
        self._pause_event.set()  # 解除暂停以便退出
        self._state = SimulationState.STOPPED
        self._log("Simulation stopped")
    
    def pause(self):
        """暂停"""
        if self._state == SimulationState.RUNNING:
            self._state = SimulationState.PAUSED
            self._pause_event.clear()
            self._log("Simulation paused")
    
    def resume(self):
        """恢复"""
        if self._state == SimulationState.PAUSED:
            self._state = SimulationState.RUNNING
            self._pause_event.set()
            self._log("Simulation resumed")
    
    async def _main_loop(self):
        """
        主循环
        
        1. 找出所有空闲角色，触发决策
        2. 如果所有角色都忙碌，跳到最近的结束时间
        3. 处理结束的任务
        4. 重复
        """
        while not self._stop_flag:
            # 等待暂停解除
            await self._pause_event.wait()
            if self._stop_flag:
                break
            
            # 获取所有空闲角色
            idle_agents = self._get_idle_agents()
            
            if idle_agents:
                # 并行触发所有空闲角色的决策
                await self._trigger_decisions(idle_agents)
            
            # 检查是否所有角色都有任务
            if self._all_agents_busy():
                # 跳到最近的任务结束时间
                await self._advance_to_next_task_end()
            elif not idle_agents:
                # 没有角色，短暂等待
                await asyncio.sleep(0.1)
    
    def _get_idle_agents(self) -> List[CharacterAgent]:
        """获取所有空闲角色"""
        idle = []
        for agent in self.agent_manager.get_all_agents():
            task = self._agent_tasks.get(agent.character_id)
            if task is None:
                idle.append(agent)
        return idle
    
    def _all_agents_busy(self) -> bool:
        """检查是否所有角色都忙碌"""
        if not self._agent_tasks:
            return False
        return all(task is not None for task in self._agent_tasks.values())
    
    # ===== 决策触发 =====
    
    async def _trigger_decisions(self, agents: List[CharacterAgent]):
        """并行触发多个角色的决策"""
        tasks = [self._trigger_single_decision(agent) for agent in agents]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _trigger_single_decision(self, agent: CharacterAgent):
        """触发单个角色的决策"""
        try:
            self._log(f"[{agent.profile.name}] Deciding next action...")
            
            # 更新角色的时间信息
            pos = self.world.get_character_position(agent.character_id)
            agent.update_game_time(
                self._game_time.day,
                f"{self._game_time.hour:02d}:{self._game_time.minute:02d}",
                pos.location_id if pos else None
            )
            
            # 调用Agent决策
            decision = await asyncio.wait_for(
                agent.perceive_and_decide(),
                timeout=self.config.decision_timeout
            )
            
            if decision:
                # 获取行动时长
                duration = decision.get('duration', 30)  # 默认30分钟
                action_name = decision.get('name', decision.get('action', 'unknown'))
                
                self._log(f"[{agent.profile.name}] -> {action_name} ({duration} min)")
                
                # 创建任务
                task = AgentTask(
                    character_id=agent.character_id,
                    action_name=action_name,
                    action_data=decision,
                    start_time=self._game_time.total_minutes,
                    end_time=self._game_time.total_minutes + duration
                )
                
                # 记录任务
                self._agent_tasks[agent.character_id] = task
                heapq.heappush(self._task_heap, task)
                
                # 执行行动（可能有副作用，如移动位置）
                await agent.execute_action(decision)
                
                # 触发回调
                await self._fire_action_start(agent, task)
            else:
                # 没有决策，给一个短暂的等待
                self._log(f"[{agent.profile.name}] -> idle (no decision)")
                task = AgentTask(
                    character_id=agent.character_id,
                    action_name="idle",
                    action_data={},
                    start_time=self._game_time.total_minutes,
                    end_time=self._game_time.total_minutes + 5
                )
                self._agent_tasks[agent.character_id] = task
                heapq.heappush(self._task_heap, task)
                
        except asyncio.TimeoutError:
            self._log(f"[{agent.profile.name}] Decision timeout, defaulting to wait")
            task = AgentTask(
                character_id=agent.character_id,
                action_name="wait",
                action_data={},
                start_time=self._game_time.total_minutes,
                end_time=self._game_time.total_minutes + 10
            )
            self._agent_tasks[agent.character_id] = task
            heapq.heappush(self._task_heap, task)
            
        except Exception as e:
            self._log(f"[{agent.profile.name}] Decision error: {e}")
    
    # ===== 时间推进 =====
    
    async def _advance_to_next_task_end(self):
        """推进时间到最近的任务结束点"""
        if not self._task_heap:
            return
        
        # 清理已过期的任务
        while self._task_heap and self._task_heap[0].end_time <= self._game_time.total_minutes:
            heapq.heappop(self._task_heap)
        
        if not self._task_heap:
            return
        
        # 获取最近结束的任务
        next_task = self._task_heap[0]
        time_to_skip = next_task.end_time - self._game_time.total_minutes
        
        # 限制最大跳跃
        time_to_skip = min(time_to_skip, self.config.max_time_skip)
        
        if time_to_skip > 0:
            old_time = str(self._game_time)
            self._game_time.advance(time_to_skip)
            
            # 更新世界状态
            self.world.update(self._game_time.hour, self._game_time.day)
            
            self._log(f"Time: {old_time} -> {self._game_time} (skipped {time_to_skip} min)")
            
            # 触发回调
            await self._fire_time_advance(time_to_skip)
        
        # 处理所有已结束的任务
        await self._process_completed_tasks()
    
    async def _process_completed_tasks(self):
        """处理所有已完成的任务"""
        current_time = self._game_time.total_minutes
        
        while self._task_heap and self._task_heap[0].end_time <= current_time:
            task = heapq.heappop(self._task_heap)
            
            # 标记角色为空闲
            self._agent_tasks[task.character_id] = None
            
            # 获取Agent
            agent = self.agent_manager.get_agent(task.character_id)
            if agent:
                self._log(f"[{agent.profile.name}] Finished: {task.action_name}")
                await self._fire_action_end(agent, task)
    
    # ===== 手动步进 =====
    
    async def step(self) -> Dict[str, Any]:
        """
        手动执行一步模拟
        
        返回这一步的结果
        """
        if not self._initialized:
            await self.initialize()
        
        result = {
            'time_before': str(self._game_time),
            'actions': [],
            'time_after': None,
            'time_skipped': 0
        }
        
        # 处理空闲角色
        idle_agents = self._get_idle_agents()
        for agent in idle_agents:
            await self._trigger_single_decision(agent)
            task = self._agent_tasks.get(agent.character_id)
            if task:
                result['actions'].append({
                    'character': agent.profile.name,
                    'action': task.action_name,
                    'duration': task.end_time - task.start_time
                })
        
        # 时间跳跃
        if self._all_agents_busy() and self._task_heap:
            time_before = self._game_time.total_minutes
            await self._advance_to_next_task_end()
            result['time_skipped'] = self._game_time.total_minutes - time_before
        
        result['time_after'] = str(self._game_time)
        return result
    
    # ===== 回调 =====
    
    def on_action_start(self, callback: Callable):
        """注册行动开始回调"""
        self._on_action_start_callbacks.append(callback)
    
    def on_action_end(self, callback: Callable):
        """注册行动结束回调"""
        self._on_action_end_callbacks.append(callback)
    
    def on_time_advance(self, callback: Callable):
        """注册时间推进回调"""
        self._on_time_advance_callbacks.append(callback)
    
    async def _fire_action_start(self, agent: CharacterAgent, task: AgentTask):
        for cb in self._on_action_start_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(agent, task)
                else:
                    cb(agent, task)
            except Exception as e:
                print(f"Callback error: {e}")
    
    async def _fire_action_end(self, agent: CharacterAgent, task: AgentTask):
        for cb in self._on_action_end_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(agent, task)
                else:
                    cb(agent, task)
            except Exception as e:
                print(f"Callback error: {e}")
    
    async def _fire_time_advance(self, minutes_skipped: int):
        for cb in self._on_time_advance_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(self._game_time, minutes_skipped)
                else:
                    cb(self._game_time, minutes_skipped)
            except Exception as e:
                print(f"Callback error: {e}")
    
    # ===== 状态查询 =====
    
    def get_status(self) -> Dict[str, Any]:
        """获取模拟状态"""
        agents_status = []
        for agent in self.agent_manager.get_all_agents():
            task = self._agent_tasks.get(agent.character_id)
            agents_status.append({
                'id': agent.character_id,
                'name': agent.profile.name,
                'state': 'busy' if task else 'idle',
                'current_action': task.action_name if task else None,
                'action_ends_at': task.end_time if task else None,
                'fatigue': agent.physical_state.fatigue
            })
        
        return {
            'state': self._state.value,
            'game_time': str(self._game_time),
            'game_time_detail': self._game_time.to_dict(),
            'world': self.world.get_world_state(),
            'agents': agents_status,
            'pending_tasks': len(self._task_heap)
        }
    
    def _log(self, message: str):
        """日志输出"""
        if self.config.verbose:
            print(f"[{self._game_time}] {message}")


# ===== 便捷函数 =====

_simulation_instance: Optional[GameSimulation] = None


def get_simulation() -> Optional[GameSimulation]:
    """获取全局模拟实例"""
    return _simulation_instance


def create_simulation(
    config: Optional[SimulationConfig] = None,
    world_config: Optional[WorldConfig] = None,
    db_session_factory: Optional[Callable] = None
) -> GameSimulation:
    """创建全局模拟实例"""
    global _simulation_instance
    _simulation_instance = GameSimulation(config, world_config, db_session_factory)
    return _simulation_instance
