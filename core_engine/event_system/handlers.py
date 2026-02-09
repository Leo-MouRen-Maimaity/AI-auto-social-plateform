"""
事件处理器模块

定义事件处理器的基类和注册机制
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Callable, Any
from .events import GameEvent, EventType, EventStatus


class EventHandler(ABC):
    """
    事件处理器基类
    
    所有事件处理器需要继承此类并实现handle方法
    """
    
    @abstractmethod
    async def handle(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        """
        处理事件
        
        Args:
            event: 要处理的事件
            context: 事件上下文，包含引擎、数据库会话等
            
        Returns:
            处理是否成功
        """
        pass
    
    async def on_start(self, event: GameEvent, context: Dict[str, Any]):
        """事件开始时的回调"""
        event.status = EventStatus.IN_PROGRESS
    
    async def on_complete(self, event: GameEvent, context: Dict[str, Any]):
        """事件完成时的回调"""
        event.status = EventStatus.COMPLETED
    
    async def on_cancel(self, event: GameEvent, context: Dict[str, Any]):
        """事件取消时的回调"""
        event.status = EventStatus.CANCELLED
    
    async def on_fail(self, event: GameEvent, context: Dict[str, Any], error: Exception):
        """事件失败时的回调"""
        event.status = EventStatus.FAILED


class EventHandlerRegistry:
    """
    事件处理器注册表
    
    管理事件类型到处理器的映射
    """
    
    _instance: Optional['EventHandlerRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[EventType, EventHandler] = {}
            cls._instance._before_hooks: Dict[EventType, list] = {}
            cls._instance._after_hooks: Dict[EventType, list] = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'EventHandlerRegistry':
        """获取单例实例"""
        return cls()
    
    def register(self, event_type: EventType, handler: EventHandler):
        """注册事件处理器"""
        self._handlers[event_type] = handler
    
    def unregister(self, event_type: EventType):
        """取消注册"""
        if event_type in self._handlers:
            del self._handlers[event_type]
    
    def get_handler(self, event_type: EventType) -> Optional[EventHandler]:
        """获取事件处理器"""
        return self._handlers.get(event_type)
    
    def add_before_hook(self, event_type: EventType, 
                        hook: Callable[[GameEvent, Dict], None]):
        """添加事件处理前的钩子"""
        if event_type not in self._before_hooks:
            self._before_hooks[event_type] = []
        self._before_hooks[event_type].append(hook)
    
    def add_after_hook(self, event_type: EventType,
                       hook: Callable[[GameEvent, Dict, bool], None]):
        """添加事件处理后的钩子"""
        if event_type not in self._after_hooks:
            self._after_hooks[event_type] = []
        self._after_hooks[event_type].append(hook)
    
    async def execute(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        """
        执行事件处理
        
        Args:
            event: 事件
            context: 上下文
            
        Returns:
            处理是否成功
        """
        handler = self.get_handler(event.event_type)
        if not handler:
            print(f"Warning: No handler registered for event type {event.event_type}")
            return False
        
        # 执行前置钩子
        for hook in self._before_hooks.get(event.event_type, []):
            await hook(event, context) if callable(hook) else None
        
        # 执行处理器
        try:
            await handler.on_start(event, context)
            success = await handler.handle(event, context)
            
            if success:
                await handler.on_complete(event, context)
            else:
                await handler.on_fail(event, context, Exception("Handler returned False"))
            
        except Exception as e:
            await handler.on_fail(event, context, e)
            success = False
        
        # 执行后置钩子
        for hook in self._after_hooks.get(event.event_type, []):
            await hook(event, context, success) if callable(hook) else None
        
        return success


# 便捷装饰器
def event_handler(event_type: EventType):
    """
    事件处理器装饰器
    
    用法:
        @event_handler(EventType.WORK)
        class WorkHandler(EventHandler):
            async def handle(self, event, context):
                ...
    """
    def decorator(cls: Type[EventHandler]):
        registry = EventHandlerRegistry.get_instance()
        registry.register(event_type, cls())
        return cls
    return decorator
