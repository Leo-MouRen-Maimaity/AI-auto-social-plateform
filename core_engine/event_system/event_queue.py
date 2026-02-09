"""
事件队列模块

基于优先队列实现的事件调度系统
"""

import heapq
from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass, field
from .events import GameEvent, EventStatus, EventPriority


@dataclass(order=True)
class PrioritizedEvent:
    """带优先级的事件包装器，用于堆排序"""
    sort_key: tuple = field(compare=True)
    event: GameEvent = field(compare=False)
    
    @classmethod
    def from_event(cls, event: GameEvent) -> 'PrioritizedEvent':
        """从事件创建优先级包装器"""
        # 排序键：(scheduled_time, priority, id)
        return cls(
            sort_key=(event.scheduled_time, event.priority.value, id(event)),
            event=event
        )


class EventQueue:
    """
    事件优先队列
    
    按时间和优先级排序的事件队列，支持：
    - 添加/取消事件
    - 按时间获取事件
    - 按角色筛选事件
    - 冲突检测
    """
    
    def __init__(self):
        self._heap: List[PrioritizedEvent] = []
        self._event_map: Dict[int, GameEvent] = {}  # id -> event
        self._cancelled: Set[int] = set()  # 已取消的事件ID
        self._next_id: int = 1
    
    def add(self, event: GameEvent) -> int:
        """
        添加事件到队列
        
        Returns:
            事件ID
        """
        if event.id is None:
            event.id = self._next_id
            self._next_id += 1
        
        self._event_map[event.id] = event
        heapq.heappush(self._heap, PrioritizedEvent.from_event(event))
        return event.id
    
    def cancel(self, event_id: int) -> bool:
        """
        取消事件
        
        使用懒删除策略，标记为已取消但不立即从堆中移除
        """
        if event_id in self._event_map:
            self._event_map[event_id].status = EventStatus.CANCELLED
            self._cancelled.add(event_id)
            return True
        return False
    
    def peek(self) -> Optional[GameEvent]:
        """查看队首事件（不移除）"""
        self._cleanup()
        if self._heap:
            return self._heap[0].event
        return None
    
    def pop(self) -> Optional[GameEvent]:
        """取出队首事件"""
        self._cleanup()
        if self._heap:
            pe = heapq.heappop(self._heap)
            event = pe.event
            if event.id in self._event_map:
                del self._event_map[event.id]
            return event
        return None
    
    def get_next_events(self, game_time: int, count: int = 1) -> List[GameEvent]:
        """
        获取指定时间点或之后的下一批事件
        
        Args:
            game_time: 当前游戏时间
            count: 最多返回的事件数
            
        Returns:
            事件列表
        """
        self._cleanup()
        events = []
        temp = []
        
        while self._heap and len(events) < count:
            pe = heapq.heappop(self._heap)
            if pe.event.scheduled_time >= game_time and pe.event.status == EventStatus.PENDING:
                events.append(pe.event)
            temp.append(pe)
        
        # 放回堆中
        for pe in temp:
            heapq.heappush(self._heap, pe)
        
        return events
    
    def get_events_in_range(self, start_time: int, end_time: int) -> List[GameEvent]:
        """获取时间范围内的所有事件"""
        self._cleanup()
        return [
            pe.event for pe in self._heap
            if start_time <= pe.event.scheduled_time < end_time
            and pe.event.status == EventStatus.PENDING
        ]
    
    def get_character_events(self, character_id: int, 
                             start_time: Optional[int] = None,
                             end_time: Optional[int] = None) -> List[GameEvent]:
        """
        获取指定角色的事件
        
        Args:
            character_id: 角色ID
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
        """
        self._cleanup()
        events = []
        for pe in self._heap:
            event = pe.event
            if event.character_id != character_id:
                continue
            if event.status != EventStatus.PENDING:
                continue
            if start_time is not None and event.scheduled_time < start_time:
                continue
            if end_time is not None and event.scheduled_time >= end_time:
                continue
            events.append(event)
        
        return sorted(events, key=lambda e: (e.scheduled_time, e.priority.value))
    
    def check_conflict(self, new_event: GameEvent) -> List[GameEvent]:
        """
        检查新事件与现有事件的冲突
        
        返回冲突的事件列表
        """
        conflicts = []
        new_start = new_event.scheduled_time
        new_end = new_event.end_time
        
        for pe in self._heap:
            event = pe.event
            if event.character_id != new_event.character_id:
                continue
            if event.status != EventStatus.PENDING:
                continue
            
            # 检查时间重叠
            event_start = event.scheduled_time
            event_end = event.end_time
            
            if not (new_end <= event_start or new_start >= event_end):
                conflicts.append(event)
        
        return conflicts
    
    def can_schedule(self, event: GameEvent) -> bool:
        """检查事件是否可以被调度（无冲突）"""
        return len(self.check_conflict(event)) == 0
    
    def reschedule(self, event_id: int, new_time: int) -> bool:
        """
        重新调度事件
        
        Args:
            event_id: 事件ID
            new_time: 新的计划时间
        """
        if event_id not in self._event_map:
            return False
        
        event = self._event_map[event_id]
        old_time = event.scheduled_time
        event.scheduled_time = new_time
        
        # 检查新时间是否有冲突
        conflicts = self.check_conflict(event)
        if conflicts:
            # 恢复原时间
            event.scheduled_time = old_time
            return False
        
        # 重新加入堆（使用懒更新策略）
        self._cancelled.add(event_id)
        event.id = self._next_id
        self._next_id += 1
        self._event_map[event.id] = event
        heapq.heappush(self._heap, PrioritizedEvent.from_event(event))
        
        return True
    
    def _cleanup(self):
        """清理已取消的事件"""
        while self._heap:
            if self._heap[0].event.id in self._cancelled:
                pe = heapq.heappop(self._heap)
                self._cancelled.discard(pe.event.id)
                if pe.event.id in self._event_map:
                    del self._event_map[pe.event.id]
            else:
                break
    
    def __len__(self) -> int:
        """队列中的有效事件数"""
        return len(self._event_map) - len(self._cancelled)
    
    def __bool__(self) -> bool:
        return len(self) > 0
    
    def clear(self):
        """清空队列"""
        self._heap.clear()
        self._event_map.clear()
        self._cancelled.clear()
    
    def to_list(self) -> List[GameEvent]:
        """将队列转换为有序列表"""
        self._cleanup()
        events = [pe.event for pe in self._heap if pe.event.status == EventStatus.PENDING]
        return sorted(events, key=lambda e: (e.scheduled_time, e.priority.value))
