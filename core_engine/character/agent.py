"""
AI角色Agent模块

核心的AI角色控制器，整合记忆、感知、决策等功能
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Awaitable
from datetime import datetime
from enum import Enum

from .memory import MemorySystem, MemoryType
from .inventory import Inventory, Item, ItemTemplates
from .perception import PerceptionSystem, EnvironmentPerception, PhysicalState, EmotionState
from .action_logger import ActionLogger, ActionType, get_action_logger
from ..ai_integration.llm_client import LLMClient, Message, get_llm_client


class AgentState(str, Enum):
    """Agent状态"""
    IDLE = "idle"           # 空闲
    THINKING = "thinking"   # 思考中
    ACTING = "acting"       # 执行行动中
    TALKING = "talking"     # 对话中
    SLEEPING = "sleeping"   # 睡眠中
    WAITING = "waiting"     # 等待中


@dataclass
class CharacterProfile:
    """角色设定"""
    id: int
    name: str
    description: str = ""           # 角色描述/性格设定
    occupation: str = ""            # 职业
    age: int = 25
    gender: str = ""
    personality_traits: List[str] = field(default_factory=list)  # 性格特点
    speaking_style: str = ""        # 说话风格
    goals: List[str] = field(default_factory=list)  # 长期目标
    daily_routine: Dict[str, str] = field(default_factory=dict)  # 日常作息
    
    def to_prompt(self) -> str:
        """转换为提示词格式"""
        lines = [
            f"【角色设定】",
            f"姓名：{self.name}",
        ]
        
        if self.age:
            lines.append(f"年龄：{self.age}岁")
        if self.gender:
            lines.append(f"性别：{self.gender}")
        if self.occupation:
            lines.append(f"职业：{self.occupation}")
        if self.description:
            lines.append(f"描述：{self.description}")
        if self.personality_traits:
            lines.append(f"性格特点：{'、'.join(self.personality_traits)}")
        if self.speaking_style:
            lines.append(f"说话风格：{self.speaking_style}")
        if self.goals:
            lines.append(f"人生目标：{'；'.join(self.goals)}")
        
        return "\n".join(lines)
    
    @classmethod
    def from_db_row(cls, row) -> 'CharacterProfile':
        """从数据库用户行创建"""
        # 尝试解析bio中的JSON设定
        extra_data = {}
        if row.bio:
            try:
                if row.bio.startswith('{'):
                    extra_data = json.loads(row.bio)
            except json.JSONDecodeError:
                extra_data = {'description': row.bio}
        
        # 解析 personality 字段
        personality_traits = []
        if row.personality:
            # personality 可能是逗号分隔的特点，或者是一段描述
            personality_text = row.personality
            if '，' in personality_text or ',' in personality_text:
                # 分割成列表
                personality_traits = [t.strip() for t in personality_text.replace(',', '，').split('，') if t.strip()]
            else:
                personality_traits = [personality_text]
        
        return cls(
            id=row.id,
            name=row.nickname or row.username,
            description=extra_data.get('description', row.bio or ''),
            occupation=extra_data.get('occupation', ''),
            age=extra_data.get('age', 25),
            gender=extra_data.get('gender', ''),
            personality_traits=extra_data.get('personality_traits', personality_traits),
            speaking_style=extra_data.get('speaking_style', ''),
            goals=extra_data.get('goals', []),
            daily_routine=extra_data.get('daily_routine', {})
        )


@dataclass
class ActionResult:
    """行动结果"""
    success: bool
    action: str
    message: str = ""
    duration: int = 0  # 消耗的游戏时间（分钟）
    data: Dict[str, Any] = field(default_factory=dict)


class CharacterAgent:
    """
    AI角色Agent
    
    负责：
    - 环境感知
    - 决策制定
    - 行动执行
    - 对话生成
    - 每日计划
    """
    
    def __init__(
        self,
        profile: CharacterProfile,
        llm_client: LLMClient = None,
        db_session = None
    ):
        self.profile = profile
        self.character_id = profile.id
        self._llm = llm_client or get_llm_client()
        self._db = db_session
        
        # 子系统
        self.memory = MemorySystem(self.character_id, db_session)
        self.inventory = Inventory(self.character_id, db_session=db_session)
        self.perception = PerceptionSystem(db_session=db_session)
        self.action_logger = get_action_logger(db_session)
        
        # 状态
        self.state = AgentState.IDLE
        self.physical_state = PhysicalState()
        
        # 游戏时间跟踪
        self.current_game_day: int = 1
        self.current_game_time: str = "08:00"
        self.current_location_id: Optional[int] = None
        
        # 今日计划
        self.daily_plan: List[Dict[str, Any]] = []
        self.current_plan_index: int = 0
        
        # 对话历史（当前会话）
        self.conversation_history: List[Message] = []
        self.conversation_partner_id: Optional[int] = None
        
        # 今日事件记录
        self.today_events: List[str] = []
        
        # 世界引用
        self._world = None
        
        # 回调
        self._action_handlers: Dict[str, Callable] = {}
    
    def set_world(self, world):
        """设置世界引用"""
        self._world = world
        self.perception.set_world(world)
    
    def register_action_handler(self, action: str, 
                                 handler: Callable[['CharacterAgent', Dict], Awaitable[ActionResult]]):
        """注册行动处理器"""
        self._action_handlers[action] = handler
    
    async def initialize(self):
        """初始化Agent"""
        # 加载记忆
        self.memory.load_from_db()
        
        # 加载物品栏
        self.inventory.load_from_db()
        
        # 确保有手机
        if not self.inventory.get_by_name("手机"):
            phone = ItemTemplates.create_phone()
            self.inventory.add(phone)
        
        print(f"Agent {self.profile.name} initialized")
    
    # ===== 系统提示词 =====
    
    def _build_system_prompt(self, context: str = "") -> str:
        """构建系统提示词"""
        prompt_parts = [
            "你是一个生活在虚拟社区中的AI角色，需要像真人一样生活、思考和行动。",
            "",
            self.profile.to_prompt(),
            "",
            self.memory.build_memory_prompt([MemoryType.COMMON, MemoryType.IMPORTANT]),
        ]
        
        if context:
            prompt_parts.append("")
            prompt_parts.append(context)
        
        prompt_parts.extend([
            "",
            "【行为准则】",
            "1. 根据自己的性格特点做出符合角色的反应",
            "2. 记住之前发生的事情，保持行为的连贯性",
            "3. 与其他角色交流时表现自然",
            "4. 做出决策时考虑当前的身体状态和环境"
        ])
        
        return "\n".join(prompt_parts)
    
    # ===== 每日流程 =====
    
    async def wake_up(self, game_day: int, game_time_str: str, 
                      world_state: Dict[str, Any]) -> str:
        """
        每日醒来流程
        
        清理上下文，提供环境信息，生成今日计划
        """
        self.state = AgentState.THINKING
        
        # 更新游戏时间
        self.current_game_day = game_day
        self.current_game_time = game_time_str
        
        # 清理对话历史
        self.conversation_history.clear()
        self.conversation_partner_id = None
        self.today_events.clear()
        self.current_plan_index = 0
        
        # 恢复疲劳
        self.physical_state.fatigue = 10
        self.physical_state.emotion = EmotionState.NEUTRAL
        
        # 构建醒来时的上下文
        daily_memories = self.memory.get_daily_memory_text()
        
        wake_up_context = f"""
【今天是第{game_day}天】
当前时间：{game_time_str}

【环境信息】
天气：{world_state.get('weather', '未知')}
季节：{world_state.get('season', '未知')}
室外温度：{world_state.get('temperature', {}).get('outdoor', 20)}°C
室内温度：{world_state.get('temperature', {}).get('indoor', 22)}°C

【近期记忆】
{daily_memories if daily_memories else '这是新的一天的开始。'}

请制定今天的计划。包含你打算做的事情、大概的时间安排。
用自然的方式表达，就像在写日记或自言自语一样。
"""
        
        response = await self._llm.generate_with_system(
            self._build_system_prompt(),
            wake_up_context,
            temperature=0.8
        )
        
        plan_text = response.content if response.success else "新的一天开始了..."
        
        if response.success:
            # 解析计划（简单版本）
            self.daily_plan = self._parse_daily_plan(response.content)
        
        # 记录醒来日志
        self.action_logger.log_wake_up(
            character_id=self.character_id,
            game_day=game_day,
            game_time=game_time_str,
            plan_summary=plan_text[:200]
        )
            
        self.state = AgentState.IDLE
        return plan_text
    
    def _parse_daily_plan(self, plan_text: str) -> List[Dict[str, Any]]:
        """解析每日计划文本"""
        # 简单实现：提取时间和活动
        plans = []
        
        # 默认计划
        default_plans = [
            {'time': '08:00', 'activity': '吃早餐', 'duration': 30},
            {'time': '09:00', 'activity': '工作/学习', 'duration': 180},
            {'time': '12:00', 'activity': '午餐', 'duration': 60},
            {'time': '13:00', 'activity': '休息', 'duration': 30},
            {'time': '14:00', 'activity': '工作/学习', 'duration': 180},
            {'time': '18:00', 'activity': '晚餐', 'duration': 60},
            {'time': '19:00', 'activity': '自由活动', 'duration': 120},
            {'time': '22:00', 'activity': '准备睡觉', 'duration': 30},
        ]
        
        # TODO: 使用LLM解析实际计划
        return default_plans
    
    async def go_to_sleep(self, game_day: int) -> str:
        """
        睡眠流程
        
        总结今天的内容，生成日常记忆
        """
        self.state = AgentState.SLEEPING
        
        if not self.today_events:
            self.today_events.append("度过了平静的一天")
        
        # 让LLM总结今天
        events_text = "\n".join([f"- {e}" for e in self.today_events])
        
        summary_prompt = f"""
今天（第{game_day}天）发生的事情：
{events_text}

请用1-2句话总结今天最重要或印象最深的事情。
这将作为你的日常记忆保存下来。
"""
        
        response = await self._llm.generate_with_system(
            self._build_system_prompt(),
            summary_prompt,
            temperature=0.7,
            max_tokens=200
        )
        
        summary = response.content if response.success else f"第{game_day}天结束了。"
        
        if response.success:
            # 保存日常记忆
            self.memory.add_daily_memory(response.content, game_day)
        
        # 记录睡觉日志
        self.action_logger.log_sleep(
            character_id=self.character_id,
            game_day=game_day,
            summary=summary
        )
        
        self.state = AgentState.IDLE
        return summary
    
    # ===== 环境感知与决策 =====
    
    async def perceive_and_decide(self) -> Optional[Dict[str, Any]]:
        """
        感知环境并做出决策
        
        Returns:
            决策结果，包含要执行的行动和预计时长（duration）
        """
        self.state = AgentState.THINKING
        
        # 获取环境感知
        perception = self.perception.perceive(
            self.character_id, 
            self.physical_state
        )
        
        # 填充关系记忆
        for char in perception.nearby_characters:
            rel_memory = self.memory.get_relationship_memory(char.id)
            if rel_memory:
                char.relationship_summary = rel_memory.content[:50]
        
        # 获取可用行动
        available_actions = self.perception.get_available_actions(perception)
        
        # 构建决策提示
        perception_text = self.perception.build_perception_prompt(perception)
        actions_text = "\n".join([
            f"{i+1}. {a['name']}: {a['description']}（预计{a.get('duration', 30)}分钟）"
            for i, a in enumerate(available_actions)
        ])
        
        # 获取最近的行动历史
        recent_logs = self.action_logger.get_character_logs(self.character_id, limit=5)
        if recent_logs:
            recent_actions_text = "\n".join([
                f"- [{log.game_time}] {log.action_name}: {log.description or log.result or ''}"
                for log in reversed(recent_logs)  # 时间顺序
            ])
        else:
            recent_actions_text = "（刚刚开始新的一天）"
        
        # 获取今日计划
        if self.daily_plan:
            plan_text = "\n".join([
                f"- {p.get('time', '?')}: {p.get('activity', p.get('description', ''))}"
                for p in self.daily_plan
            ])
        else:
            plan_text = "（尚未制定具体计划）"
        
        # 获取今日已发生的事件
        if self.today_events:
            events_text = "\n".join([f"- {e}" for e in self.today_events[-5:]])
        else:
            events_text = "（今天还没有特别的事件）"
        
        decision_prompt = f"""
【当前时间】第{self.current_game_day}天 {self.current_game_time}

{perception_text}

【最近行动】
{recent_actions_text}

【今日计划】
{plan_text}

【今日事件】
{events_text}

【物品栏】
{self.inventory.get_inventory_text()}

【可用行动】
{actions_text}

根据当前状态、环境和你的计划，选择一个合适的行动。
考虑你最近做了什么，避免重复无意义的行动。
如果你感到疲劳（疲劳值>70），应该考虑休息或睡觉。

请用JSON格式回复：
{{"action_index": 数字, "reason": "选择这个行动的原因", "custom_duration": 可选的自定义时长（分钟）}}
"""
        
        response = await self._llm.generate_json(
            self._build_system_prompt(),
            decision_prompt,
            temperature=0.6
        )
        
        # 将LLM响应转为字符串用于记录
        import json
        llm_response_str = json.dumps(response, ensure_ascii=False) if response else ""
        
        self.state = AgentState.IDLE
        
        if response and 'action_index' in response:
            action_index = response['action_index'] - 1  # 转为0索引
            if 0 <= action_index < len(available_actions):
                selected_action = available_actions[action_index]
                selected_action['reason'] = response.get('reason', '')
                # 使用自定义时长或默认时长
                if 'custom_duration' in response and response['custom_duration']:
                    selected_action['duration'] = response['custom_duration']
                elif 'duration' not in selected_action:
                    selected_action['duration'] = 30  # 默认30分钟
                # 添加prompt和response用于日志记录
                selected_action['_input_prompt'] = decision_prompt
                selected_action['_llm_response'] = llm_response_str
                return selected_action
        
        # 默认返回等待
        return {
            'action': 'wait', 
            'name': '等待', 
            'params': {}, 
            'duration': 10,
            '_input_prompt': decision_prompt,
            '_llm_response': llm_response_str
        }
    
    async def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """
        执行行动
        
        Args:
            action: 行动描述
            
        Returns:
            行动结果
        """
        self.state = AgentState.ACTING
        
        action_type = action.get('action', 'wait')
        params = action.get('params', {})
        reason = action.get('reason', '')
        
        # 检查是否有注册的处理器
        if action_type in self._action_handlers:
            result = await self._action_handlers[action_type](self, params)
        else:
            # 默认处理
            result = await self._default_action_handler(action_type, params)
        
        # 记录事件
        if result.success and result.message:
            self.today_events.append(result.message)
        
        # 记录行动日志
        self._log_action_result(
            action_type, 
            action.get('name', action_type), 
            result, 
            reason,
            input_prompt=action.get('_input_prompt', ''),
            llm_response=action.get('_llm_response', '')
        )
        
        # 消耗疲劳
        fatigue_cost = result.duration * 0.1
        self.physical_state.add_fatigue(fatigue_cost)
        
        self.state = AgentState.IDLE
        return result
    
    def _log_action_result(self, action_type: str, action_name: str,
                           result: ActionResult, reason: str = "",
                           input_prompt: str = "", llm_response: str = ""):
        """记录行动结果到日志"""
        # 映射行动类型
        type_mapping = {
            'wait': ActionType.OTHER,
            'rest': ActionType.REST,
            'look_around': ActionType.OTHER,
            'use_phone': ActionType.USE_PHONE,
            'browse_posts': ActionType.USE_PHONE,
            'create_post': ActionType.POST,
            'check_messages': ActionType.MESSAGE,
            'send_message': ActionType.MESSAGE,
            'view_user_profile': ActionType.USE_PHONE,
            'move': ActionType.MOVE,
            'move_to': ActionType.MOVE,
            'talk': ActionType.TALK,
            'talk_to': ActionType.TALK,
            'greet': ActionType.TALK,
            'eat': ActionType.EAT,
            'work': ActionType.WORK,
            'sleep': ActionType.SLEEP,
        }
        
        log_type = type_mapping.get(action_type, ActionType.OTHER)
        
        self.action_logger.log_action(
            character_id=self.character_id,
            action_type=log_type,
            action_name=action_name,
            description=result.message,
            location_id=self.current_location_id,
            game_day=self.current_game_day,
            game_time=self.current_game_time,
            duration=result.duration,
            reason=reason,
            result=result.message,
            success=result.success,
            input_prompt=input_prompt,
            llm_response=llm_response,
            extra_data=result.data if result.data else None
        )
    
    def update_game_time(self, game_day: int, game_time: str, location_id: int = None):
        """更新游戏时间（供外部调用）"""
        self.current_game_day = game_day
        self.current_game_time = game_time
        if location_id is not None:
            self.current_location_id = location_id
    
    async def _default_action_handler(self, action_type: str, 
                                       params: Dict[str, Any]) -> ActionResult:
        """默认行动处理器"""
        if action_type == 'wait':
            duration = params.get('duration', 5)
            return ActionResult(
                success=True,
                action='wait',
                message=f"等待了{duration}分钟",
                duration=duration
            )
        
        elif action_type == 'rest':
            self.physical_state.recover_fatigue(20)
            return ActionResult(
                success=True,
                action='rest',
                message="休息了一会儿，感觉好多了",
                duration=15
            )
        
        elif action_type == 'look_around':
            return ActionResult(
                success=True,
                action='look_around',
                message="观察了周围的环境",
                duration=2
            )
        
        elif action_type == 'move_to' or action_type == 'move':
            # 移动到指定位置
            location_id = params.get('location_id')
            location_name = params.get('location_name', '目的地')
            
            if not location_id and not self._world:
                return ActionResult(
                    success=False,
                    action='move_to',
                    message="不知道要去哪里",
                    duration=1
                )
            
            # 如果有世界引用，尝试获取位置名称
            if self._world and location_id:
                location = self._world.location_manager.get(location_id)
                if location:
                    location_name = location.name
                    # 计算距离和时间
                    current_pos = self._world.get_character_position(self.character_id)
                    if current_pos:
                        distance = location.distance_to_point(current_pos.x, current_pos.y)
                        walk_time = max(5, int(distance / 5))  # 步行速度约5单位/分钟
                    else:
                        walk_time = 10
                    
                    # 更新角色位置到目标地点中心
                    center_x, center_y = location.center
                    self._world.set_character_position(
                        self.character_id, 
                        center_x, 
                        center_y, 
                        location_id
                    )
                    self.current_location_id = location_id
                    
                    return ActionResult(
                        success=True,
                        action='move_to',
                        message=f"前往了{location_name}",
                        duration=walk_time,
                        data={'location_id': location_id, 'location_name': location_name}
                    )
            
            # 没有世界引用时的简单处理
            duration = params.get('duration', 10)
            return ActionResult(
                success=True,
                action='move_to',
                message=f"前往了{location_name}",
                duration=duration,
                data={'location_id': location_id}
            )
        
        elif action_type == 'browse_posts':
            # 浏览帖子
            from ..social.social_scheduler import get_social_scheduler
            scheduler = get_social_scheduler(self._db)
            results, browsing_summary = await scheduler.browse_feed(self, max_posts=5)
            
            if results:
                total_duration = sum(r.duration for r in results)
                return ActionResult(
                    success=True,
                    action='browse_posts',
                    message=browsing_summary,
                    duration=total_duration or 15,
                    data={'results': [r.data for r in results]}
                )
            return ActionResult(
                success=True,
                action='browse_posts',
                message=browsing_summary or "浏览了社交网络，没有新帖子",
                duration=5
            )
        
        elif action_type == 'create_post':
            # 发帖
            from ..social.social_scheduler import get_social_scheduler
            scheduler = get_social_scheduler(self._db)
            result = await scheduler.create_post(self)
            
            if result and result.success:
                return ActionResult(
                    success=True,
                    action='create_post',
                    message=result.message,
                    duration=result.duration,
                    data=result.data
                )
            return ActionResult(
                success=False,
                action='create_post',
                message="没有想到要发什么帖子",
                duration=2
            )
        
        elif action_type == 'check_messages':
            # 查看私信
            from ..social.social_scheduler import get_social_scheduler
            scheduler = get_social_scheduler(self._db)
            results = await scheduler.check_and_reply_messages(self)
            
            if results:
                messages = [r.message for r in results if r.message]
                total_duration = sum(r.duration for r in results)
                return ActionResult(
                    success=True,
                    action='check_messages',
                    message=f"查看私信：{'; '.join(messages[:3])}",
                    duration=total_duration or 10,
                    data={'results': [r.data for r in results]}
                )
            return ActionResult(
                success=True,
                action='check_messages',
                message="查看了私信，没有新消息",
                duration=2
            )
        
        elif action_type == 'use_phone':
            # 保留旧的use_phone作为兼容，但调用综合社交行为
            from ..social.social_scheduler import get_social_scheduler
            scheduler = get_social_scheduler(self._db)
            results, browsing_summary = await scheduler.use_phone(self, duration_minutes=10)
            
            if results:
                # 非浏览类的消息（私信、发帖等）单独提取
                other_messages = [
                    r.message for r in results 
                    if r.message and r.action_type.value not in ('browse_feed', 'like_post', 'comment_post')
                ]
                # 组合：浏览总结 + 其他行为
                all_parts = []
                if browsing_summary:
                    all_parts.append(browsing_summary)
                all_parts.extend(other_messages[:2])
                
                message = f"看了会儿手机：{'; '.join(all_parts)}" if all_parts else "看了会儿手机"
                return ActionResult(
                    success=True,
                    action='use_phone',
                    message=message,
                    duration=10
                )
            return ActionResult(
                success=True,
                action='use_phone',
                message="查看了手机",
                duration=10
            )
        
        elif action_type == 'send_message':
            # 主动发私信
            from ..social.social_scheduler import get_social_scheduler
            target_id = params.get('target_id')
            target_name = params.get('target_name', '某人')
            
            if not target_id:
                return ActionResult(
                    success=False,
                    action='send_message',
                    message="不知道要给谁发私信",
                    duration=1
                )
            
            scheduler = get_social_scheduler(self._db)
            result = await scheduler.send_proactive_message(self, target_id)
            
            if result and result.success:
                return ActionResult(
                    success=True,
                    action='send_message',
                    message=result.message,
                    duration=result.duration,
                    data=result.data
                )
            return ActionResult(
                success=False,
                action='send_message',
                message=f"没想好要对{target_name}说什么",
                duration=2
            )
        
        elif action_type == 'view_user_profile':
            # 查看用户主页/帖子
            from ..social.social_scheduler import get_social_scheduler
            target_id = params.get('target_id')
            target_name = params.get('target_name', '某人')
            
            if not target_id:
                return ActionResult(
                    success=False,
                    action='view_user_profile',
                    message="不知道要看谁的主页",
                    duration=1
                )
            
            scheduler = get_social_scheduler(self._db)
            results = await scheduler.view_user_profile(self, target_id, max_posts=5)
            
            if results:
                # 汇总所有结果
                total_duration = sum(r.duration for r in results)
                messages = [r.message for r in results if r.message]
                
                return ActionResult(
                    success=True,
                    action='view_user_profile',
                    message=f"查看了{target_name}的主页：" + "；".join(messages[-3:]),
                    duration=total_duration,
                    data={'target_id': target_id, 'results_count': len(results)}
                )
            return ActionResult(
                success=False,
                action='view_user_profile',
                message=f"无法查看{target_name}的主页",
                duration=2
            )
        
        return ActionResult(
            success=False,
            action=action_type,
            message=f"未知行动：{action_type}"
        )
    
    # ===== 对话系统 =====
    
    async def start_conversation(self, partner_id: int, 
                                  partner_name: str,
                                  initial_context: str = "") -> str:
        """
        开始对话
        
        Args:
            partner_id: 对话对象ID
            partner_name: 对话对象名称
            initial_context: 初始上下文（如见面场景）
            
        Returns:
            开场白
        """
        self.state = AgentState.TALKING
        self.conversation_partner_id = partner_id
        self.conversation_history.clear()
        
        # 获取关系记忆
        relationship = self.memory.get_relationship_text(partner_id, partner_name)
        
        context = f"""
你正在与{partner_name}交谈。
{f'你对{partner_name}的印象：{relationship}' if relationship else f'你还不太了解{partner_name}。'}
{initial_context}

请自然地开始这段对话。
"""
        
        response = await self._llm.generate_with_system(
            self._build_system_prompt(context),
            f"开始与{partner_name}的对话",
            temperature=0.8
        )
        
        if response.success:
            self.conversation_history.append(
                Message(role="assistant", content=response.content)
            )
        
        return response.content if response.success else f"你好，{partner_name}。"
    
    async def respond_in_conversation(self, partner_message: str,
                                       partner_name: str = "") -> str:
        """
        在对话中回复
        
        Args:
            partner_message: 对方的消息
            partner_name: 对方名称
            
        Returns:
            回复内容
        """
        if self.state != AgentState.TALKING:
            self.state = AgentState.TALKING
        
        # 添加对方消息到历史
        self.conversation_history.append(
            Message(role="user", content=partner_message)
        )
        
        # 构建对话上下文
        context = f"你正在与{partner_name}交谈。" if partner_name else "你正在进行对话。"
        
        # 准备消息列表
        messages = [
            Message(role="system", content=self._build_system_prompt(context))
        ] + self.conversation_history
        
        response = await self._llm.chat(messages, temperature=0.8)
        
        if response.success:
            self.conversation_history.append(
                Message(role="assistant", content=response.content)
            )
        
        return response.content if response.success else "..."
    
    async def end_conversation(self, partner_id: int, 
                                partner_name: str) -> Optional[str]:
        """
        结束对话，更新关系记忆
        
        Returns:
            对话总结（如果需要更新记忆）
        """
        if not self.conversation_history:
            self.state = AgentState.IDLE
            return None
        
        # 让LLM总结对话
        conversation_text = "\n".join([
            f"{'我' if m.role == 'assistant' else partner_name}：{m.content}"
            for m in self.conversation_history[-10:]  # 最近10条
        ])
        
        summary_prompt = f"""
刚才与{partner_name}的对话：
{conversation_text}

请用一句话总结这次对话的主要内容或你对{partner_name}的新印象。
如果这次对话没有什么特别的，可以回复"普通的交流"。
"""
        
        response = await self._llm.generate_with_system(
            self._build_system_prompt(),
            summary_prompt,
            temperature=0.5,
            max_tokens=100
        )
        
        if response.success and response.content != "普通的交流":
            # 更新关系记忆
            current_rel = self.memory.get_relationship_text(partner_id)
            new_memory = f"{current_rel}\n{response.content}" if current_rel else response.content
            self.memory.set_relationship_memory(partner_id, new_memory[-500:])  # 限制长度
        
        # 记录事件
        self.today_events.append(f"和{partner_name}聊了天")
        
        # 清理
        self.conversation_history.clear()
        self.conversation_partner_id = None
        self.state = AgentState.IDLE
        
        return response.content if response.success else None
    
    # ===== 社交网络行为 =====
    
    async def browse_feed(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        浏览社交网络帖子
        
        Args:
            posts: 帖子列表（包含评论信息）
            
        Returns:
            对每个帖子的反应（是否点赞、评论内容）
        """
        reactions = []
        
        for post in posts[:5]:  # 最多看5条
            author_name = post.get('author_name', '某人')
            content = post.get('content', '')
            comments = post.get('comments', [])
            has_commented = post.get('has_commented', False)
            
            # 构建评论区显示
            comments_text = ""
            if comments:
                comments_text = "\n评论区：\n"
                for c in comments[:10]:  # 最多显示10条评论
                    prefix = "（我的评论）" if c.get('is_mine') else ""
                    comments_text += f"  - {c['author_name']}{prefix}：{c['content']}\n"
            
            # 如果已评论，提示不要重复评论
            comment_instruction = ""
            if has_commented:
                comment_instruction = "\n注意：你已经评论过这条帖子了，不需要再评论。"
            
            reaction_prompt = f"""
你在浏览社交网络，看到了{author_name}发的帖子：
"{content}"
{comments_text}
请决定你的反应：
1. 是否点赞？（true/false）
2. 是否评论？如果是，写什么？（留空表示不评论）{comment_instruction}

用JSON格式回复：
{{"like": true/false, "comment": "评论内容或空字符串"}}
"""
            
            response = await self._llm.generate_json(
                self._build_system_prompt(),
                reaction_prompt,
                temperature=0.7
            )
            
            if response:
                # 如果已评论过，强制不再评论
                comment = response.get('comment', '')
                if has_commented:
                    comment = ''
                
                reactions.append({
                    'post_id': post.get('id'),
                    'like': response.get('like', False),
                    'comment': comment
                })
            else:
                reactions.append({
                    'post_id': post.get('id'),
                    'like': False,
                    'comment': ''
                })
            
            await asyncio.sleep(0.1)  # 避免过快请求
        
        return reactions
    
    async def summarize_browsing_session(
        self, 
        posts: List[Dict[str, Any]], 
        reactions: List[Dict[str, Any]]
    ) -> str:
        """
        总结浏览社交网络的体验
        
        在浏览帖子并做出反应后，调用LLM生成1-2句话的总结，
        用于记录到today_events和action_log，供后续决策参考。
        
        Args:
            posts: 浏览的帖子列表（含content、author_name等）
            reactions: 对每条帖子的反应（含like、comment等）
            
        Returns:
            浏览体验的总结文本
        """
        if not posts:
            return "浏览了社交网络，没有新内容"
        
        # 构建浏览历史描述
        history_lines = []
        for i, (post, reaction) in enumerate(zip(posts, reactions), 1):
            author = post.get('author_name', '某人')
            content = post.get('content', '')
            content_preview = content[:80] + ("..." if len(content) > 80 else "")
            
            # 构建反应描述
            action_parts = []
            if reaction.get('like'):
                action_parts.append("点赞了")
            if reaction.get('comment'):
                comment_preview = reaction['comment'][:30]
                action_parts.append(f'评论了"{comment_preview}"')
            
            reaction_text = "、".join(action_parts) if action_parts else "只是看了看"
            
            history_lines.append(
                f'{i}. {author}的帖子："{content_preview}"\n'
                f'   → 你的反应：{reaction_text}'
            )
        
        browsing_history = "\n".join(history_lines)
        
        summary_prompt = f"""
你刚才浏览了社交网络，看到了以下帖子：

{browsing_history}

请用1-2句话总结这次浏览体验，包括看到了什么、你做了什么反应、整体感受。
用第一人称，符合你的性格来描述。
"""
        
        try:
            response = await self._llm.generate_with_system(
                self._build_system_prompt(),
                summary_prompt,
                temperature=0.6,
                max_tokens=200
            )
            
            if response and response.success and response.content:
                return response.content.strip()
        except Exception:
            pass
        
        # 降级：用简单拼接描述
        parts = []
        for post, reaction in zip(posts, reactions):
            author = post.get('author_name', '某人')
            if reaction.get('comment'):
                parts.append(f"评论了{author}的帖子")
            elif reaction.get('like'):
                parts.append(f"给{author}的帖子点赞")
            else:
                parts.append(f"看了{author}的帖子")
        return f"浏览了社交网络：{'; '.join(parts[:4])}"
    
    async def create_post(self, context: str = "") -> Optional[Dict[str, str]]:
        """
        创建社交网络帖子
        
        Args:
            context: 创建帖子的上下文（如刚发生的事）
            
        Returns:
            帖子内容，包含content字段
        """
        post_prompt = f"""
{context if context else '你想在社交网络上发一条帖子。'}

请创作一条符合你性格的帖子内容。
可以是：
- 分享今天的心情或见闻
- 发表对某事的看法
- 日常生活的记录

用JSON格式回复：
{{"content": "帖子正文内容"}}
"""
        
        response = await self._llm.generate_json(
            self._build_system_prompt(),
            post_prompt,
            temperature=0.9
        )
        
        if response and response.get('content'):
            self.today_events.append("发了一条帖子")
            return response
        
        return None
    
    # ===== 状态查询 =====
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            'character_id': self.character_id,
            'name': self.profile.name,
            'state': self.state.value,
            'physical_state': self.physical_state.to_dict(),
            'inventory_stats': self.inventory.get_stats(),
            'memory_stats': self.memory.get_stats(),
            'today_events_count': len(self.today_events),
            'in_conversation': self.conversation_partner_id is not None
        }
    
    def get_context_for_event(self) -> Dict[str, Any]:
        """获取用于事件处理的上下文"""
        return {
            'agent': self,
            'character_id': self.character_id,
            'profile': self.profile,
            'physical_state': self.physical_state,
            'memory': self.memory,
            'inventory': self.inventory
        }


# ===== Agent管理器 =====

class AgentManager:
    """
    Agent管理器
    
    管理所有AI角色的Agent实例
    """
    
    _instance = None
    
    def __init__(self):
        self._agents: Dict[int, CharacterAgent] = {}
        self._llm_client: Optional[LLMClient] = None
    
    @classmethod
    def get_instance(cls) -> 'AgentManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_llm_client(self, client: LLMClient):
        """设置LLM客户端"""
        self._llm_client = client
    
    async def create_agent(self, character_id: int, 
                           db_session=None) -> CharacterAgent:
        """
        创建或获取Agent
        
        Args:
            character_id: 角色ID
            db_session: 数据库会话
            
        Returns:
            CharacterAgent实例
        """
        if character_id in self._agents:
            return self._agents[character_id]
        
        # 从数据库加载角色信息
        profile = await self._load_profile(character_id, db_session)
        
        if not profile:
            raise ValueError(f"Character {character_id} not found")
        
        agent = CharacterAgent(
            profile=profile,
            llm_client=self._llm_client,
            db_session=db_session
        )
        
        await agent.initialize()
        
        self._agents[character_id] = agent
        return agent
    
    async def _load_profile(self, character_id: int, 
                            db_session) -> Optional[CharacterProfile]:
        """从数据库加载角色配置"""
        if not db_session:
            # 返回默认配置
            return CharacterProfile(
                id=character_id,
                name=f"角色{character_id}",
                description="一个普通的社区居民"
            )
        
        from api_server.models import User
        
        user = db_session.query(User).filter(User.id == character_id).first()
        if user:
            return CharacterProfile.from_db_row(user)
        
        return None
    
    def get_agent(self, character_id: int) -> Optional[CharacterAgent]:
        """获取已存在的Agent"""
        return self._agents.get(character_id)
    
    def get_all_agents(self) -> List[CharacterAgent]:
        """获取所有Agent"""
        return list(self._agents.values())
    
    async def remove_agent(self, character_id: int):
        """移除Agent"""
        if character_id in self._agents:
            del self._agents[character_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计"""
        return {
            'total_agents': len(self._agents),
            'agents': [
                {'id': aid, 'name': a.profile.name, 'state': a.state.value}
                for aid, a in self._agents.items()
            ]
        }
