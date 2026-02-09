"""
游戏引擎核心模块

时间管理器与游戏状态管理
"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime
import json

from .event_system.events import GameEvent, EventStatus, EventType
from .event_system.event_queue import EventQueue
from .event_system.handlers import EventHandlerRegistry


class EngineState(str, Enum):
    """引擎状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class GameTime:
    """
    游戏时间
    
    游戏时间以分钟为最小单位，从游戏开始时（第1天0:00）计算
    """
    total_minutes: int = 0  # 从游戏开始的总分钟数
    
    @property
    def day(self) -> int:
        """当前天数（从1开始）"""
        return self.total_minutes // (24 * 60) + 1
    
    @property
    def hour(self) -> int:
        """当前小时（0-23）"""
        return (self.total_minutes % (24 * 60)) // 60
    
    @property
    def minute(self) -> int:
        """当前分钟（0-59）"""
        return self.total_minutes % 60
    
    @property
    def time_of_day(self) -> str:
        """一天中的时段"""
        hour = self.hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "noon"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    @property
    def is_daytime(self) -> bool:
        """是否是白天（6:00-22:00）"""
        return 6 <= self.hour < 22
    
    def advance(self, minutes: int) -> 'GameTime':
        """推进时间"""
        self.total_minutes += minutes
        return self
    
    def set_to_day_start(self, day: int):
        """设置到某天的开始（0:00）"""
        self.total_minutes = (day - 1) * 24 * 60
    
    def minutes_until(self, hour: int, minute: int = 0) -> int:
        """计算到指定时间还有多少分钟"""
        target = hour * 60 + minute
        current = self.hour * 60 + self.minute
        
        if target > current:
            return target - current
        else:
            # 需要到第二天
            return (24 * 60 - current) + target
    
    def __str__(self) -> str:
        return f"Day {self.day}, {self.hour:02d}:{self.minute:02d}"
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'total_minutes': self.total_minutes,
            'day': self.day,
            'hour': self.hour,
            'minute': self.minute
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'GameTime':
        return cls(total_minutes=data.get('total_minutes', 0))
    
    @classmethod
    def from_hm(cls, day: int, hour: int, minute: int = 0) -> 'GameTime':
        """从天/时/分创建"""
        total = (day - 1) * 24 * 60 + hour * 60 + minute
        return cls(total_minutes=total)


@dataclass
class GameState:
    """
    游戏状态
    
    保存游戏的当前状态，支持序列化和恢复
    """
    game_time: GameTime = field(default_factory=GameTime)
    weather: str = "sunny"
    outdoor_temperature: float = 25.0
    indoor_temperature: float = 22.0
    engine_state: EngineState = EngineState.STOPPED
    
    # 统计信息
    events_processed: int = 0
    last_save_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'game_time': self.game_time.to_dict(),
            'weather': self.weather,
            'outdoor_temperature': self.outdoor_temperature,
            'indoor_temperature': self.indoor_temperature,
            'engine_state': self.engine_state.value,
            'events_processed': self.events_processed,
            'last_save_time': self.last_save_time.isoformat() if self.last_save_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        state = cls()
        state.game_time = GameTime.from_dict(data.get('game_time', {}))
        state.weather = data.get('weather', 'sunny')
        state.outdoor_temperature = data.get('outdoor_temperature', 25.0)
        state.indoor_temperature = data.get('indoor_temperature', 22.0)
        state.engine_state = EngineState(data.get('engine_state', 'stopped'))
        state.events_processed = data.get('events_processed', 0)
        if data.get('last_save_time'):
            state.last_save_time = datetime.fromisoformat(data['last_save_time'])
        return state
    
    def save_to_file(self, filepath: str):
        """保存状态到文件"""
        self.last_save_time = datetime.now()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'GameState':
        """从文件加载状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class GameEngine:
    """
    游戏引擎
    
    核心时间管理器，负责：
    - 游戏时间推进
    - 事件调度和执行
    - 游戏状态管理
    - 暂停/恢复机制
    """
    
    def __init__(self, db_session_factory: Optional[Callable] = None):
        self.state = GameState()
        self.event_queue = EventQueue()
        self.handler_registry = EventHandlerRegistry.get_instance()
        self._db_session_factory = db_session_factory
        
        # 运行控制
        self._running = False
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 初始不暂停
        
        # 回调
        self._on_tick_callbacks: List[Callable[[GameTime], Awaitable[None]]] = []
        self._on_day_change_callbacks: List[Callable[[int], Awaitable[None]]] = []
        self._on_event_complete_callbacks: List[Callable[[GameEvent], Awaitable[None]]] = []
        
        # 当前正在执行的事件
        self._current_event: Optional[GameEvent] = None
    
    @property
    def game_time(self) -> GameTime:
        """当前游戏时间"""
        return self.state.game_time
    
    @property
    def is_running(self) -> bool:
        return self._running and not self._paused
    
    @property
    def is_paused(self) -> bool:
        return self._paused
    
    def schedule_event(self, event: GameEvent) -> Optional[int]:
        """
        调度事件
        
        Args:
            event: 要调度的事件
            
        Returns:
            事件ID，如果有冲突返回None
        """
        conflicts = self.event_queue.check_conflict(event)
        if conflicts:
            print(f"Event conflict detected: {event} conflicts with {conflicts}")
            return None
        
        return self.event_queue.add(event)
    
    def cancel_event(self, event_id: int) -> bool:
        """取消事件"""
        return self.event_queue.cancel(event_id)
    
    def get_character_schedule(self, character_id: int,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None) -> List[GameEvent]:
        """获取角色的事件计划"""
        if start_time is None:
            start_time = self.game_time.total_minutes
        return self.event_queue.get_character_events(character_id, start_time, end_time)
    
    async def start(self):
        """启动引擎"""
        if self._running:
            return
        
        self._running = True
        self._paused = False
        self.state.engine_state = EngineState.RUNNING
        
        print(f"Game engine started at {self.game_time}")
        await self._main_loop()
    
    async def stop(self):
        """停止引擎"""
        self._running = False
        self._paused = False
        self._pause_event.set()
        self.state.engine_state = EngineState.STOPPED
        print(f"Game engine stopped at {self.game_time}")
    
    def pause(self):
        """暂停引擎"""
        if self._running and not self._paused:
            self._paused = True
            self._pause_event.clear()
            self.state.engine_state = EngineState.PAUSED
            print(f"Game engine paused at {self.game_time}")
    
    def resume(self):
        """恢复引擎"""
        if self._running and self._paused:
            self._paused = False
            self._pause_event.set()
            self.state.engine_state = EngineState.RUNNING
            print(f"Game engine resumed at {self.game_time}")
    
    def on_tick(self, callback: Callable[[GameTime], Awaitable[None]]):
        """注册每tick回调"""
        self._on_tick_callbacks.append(callback)
    
    def on_day_change(self, callback: Callable[[int], Awaitable[None]]):
        """注册日期变更回调"""
        self._on_day_change_callbacks.append(callback)
    
    def on_event_complete(self, callback: Callable[[GameEvent], Awaitable[None]]):
        """注册事件完成回调"""
        self._on_event_complete_callbacks.append(callback)
    
    async def _main_loop(self):
        """主循环"""
        while self._running:
            # 等待暂停结束
            await self._pause_event.wait()
            
            if not self._running:
                break
            
            # 获取下一个事件
            next_event = self.event_queue.peek()
            
            if next_event is None:
                # 没有事件，推进1分钟
                await self._advance_time(1)
                continue
            
            # 计算到下一个事件的时间
            time_to_event = next_event.scheduled_time - self.game_time.total_minutes
            
            if time_to_event > 0:
                # 推进时间到事件开始
                await self._advance_time(time_to_event)
            
            # 执行事件
            event = self.event_queue.pop()
            if event:
                await self._execute_event(event)
            
            # 短暂让出控制权
            await asyncio.sleep(0.01)
    
    async def _advance_time(self, minutes: int):
        """推进游戏时间"""
        old_day = self.game_time.day
        
        for _ in range(minutes):
            self.game_time.advance(1)
            
            # 触发tick回调
            for callback in self._on_tick_callbacks:
                try:
                    await callback(self.game_time)
                except Exception as e:
                    print(f"Error in tick callback: {e}")
            
            # 检查日期变更
            if self.game_time.day != old_day:
                old_day = self.game_time.day
                for callback in self._on_day_change_callbacks:
                    try:
                        await callback(self.game_time.day)
                    except Exception as e:
                        print(f"Error in day change callback: {e}")
    
    async def _execute_event(self, event: GameEvent):
        """执行事件"""
        self._current_event = event
        
        context = {
            'engine': self,
            'game_time': self.game_time,
            'state': self.state,
        }
        
        # 添加数据库会话
        if self._db_session_factory:
            context['db'] = self._db_session_factory()
        
        try:
            success = await self.handler_registry.execute(event, context)
            
            if success:
                self.state.events_processed += 1
                
                # 推进事件持续时间
                if event.duration > 0:
                    await self._advance_time(event.duration)
                
                # 触发事件完成回调
                for callback in self._on_event_complete_callbacks:
                    try:
                        await callback(event)
                    except Exception as e:
                        print(f"Error in event complete callback: {e}")
            
        except Exception as e:
            print(f"Error executing event {event}: {e}")
            event.status = EventStatus.FAILED
        
        finally:
            self._current_event = None
            if 'db' in context and hasattr(context['db'], 'close'):
                context['db'].close()
    
    def save_state(self, filepath: str):
        """保存游戏状态"""
        self.state.save_to_file(filepath)
        
        # 也保存事件队列
        events_path = filepath.replace('.json', '_events.json')
        events_data = [e.to_dict() for e in self.event_queue.to_list()]
        with open(events_path, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
        
        print(f"Game state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """加载游戏状态"""
        self.state = GameState.load_from_file(filepath)
        
        # 加载事件队列
        events_path = filepath.replace('.json', '_events.json')
        try:
            with open(events_path, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            
            self.event_queue.clear()
            for data in events_data:
                event = GameEvent.from_dict(data)
                self.event_queue.add(event)
        except FileNotFoundError:
            print(f"No events file found at {events_path}")
        
        print(f"Game state loaded from {filepath}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态摘要"""
        return {
            'state': self.state.engine_state.value,
            'game_time': str(self.game_time),
            'game_time_detail': self.game_time.to_dict(),
            'weather': self.state.weather,
            'temperature': {
                'outdoor': self.state.outdoor_temperature,
                'indoor': self.state.indoor_temperature
            },
            'events_in_queue': len(self.event_queue),
            'events_processed': self.state.events_processed,
            'current_event': self._current_event.to_dict() if self._current_event else None
        }
