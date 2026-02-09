"""事件系统模块"""

from .events import (
    GameEvent, EventType, EventPriority, EventStatus,
    PersonalEvent, CollectiveEvent, EmergencyEvent
)
from .event_queue import EventQueue
from .handlers import EventHandler, EventHandlerRegistry

__all__ = [
    'GameEvent',
    'EventType',
    'EventPriority',
    'EventStatus',
    'PersonalEvent',
    'CollectiveEvent',
    'EmergencyEvent',
    'EventQueue',
    'EventHandler',
    'EventHandlerRegistry',
]
