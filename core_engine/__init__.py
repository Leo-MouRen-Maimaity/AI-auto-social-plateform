"""
AI社区核心引擎

包含时间管理器、事件系统、环境系统、AI角色系统、社交功能等核心组件
"""

from .engine import GameEngine, GameState, GameTime
from .simulation import GameSimulation, SimulationConfig, SimulationState, create_simulation, get_simulation
from .event_system.events import (
    GameEvent, EventType, EventPriority,
    PersonalEvent, CollectiveEvent, EmergencyEvent
)
from .event_system.event_queue import EventQueue
from .environment.world import World, Weather, Season
from .environment.locations import Location, LocationType, LocationManager
from .character.agent import CharacterAgent, CharacterProfile, AgentManager
from .character.memory import MemorySystem, MemoryType
from .character.inventory import Inventory, Item, ItemType
from .character.perception import PerceptionSystem, PhysicalState
from .ai_integration.llm_client import LLMClient, LLMConfig, get_llm_client
from .social.social_client import SocialClient, get_social_client
from .social.social_scheduler import SocialScheduler, get_social_scheduler
from .social.social_handlers import SocialEventHandlers

__all__ = [
    # 引擎
    'GameEngine',
    'GameState',
    'GameTime',
    # 模拟整合层
    'GameSimulation',
    'SimulationConfig',
    'SimulationState',
    'create_simulation',
    'get_simulation',
    # 事件系统
    'GameEvent',
    'EventType',
    'EventPriority',
    'PersonalEvent',
    'CollectiveEvent',
    'EmergencyEvent',
    'EventQueue',
    # 环境系统
    'World',
    'Weather',
    'Season',
    'Location',
    'LocationType',
    'LocationManager',
    # AI角色系统
    'CharacterAgent',
    'CharacterProfile',
    'AgentManager',
    'MemorySystem',
    'MemoryType',
    'Inventory',
    'Item',
    'ItemType',
    'PerceptionSystem',
    'PhysicalState',
    # AI集成
    'LLMClient',
    'LLMConfig',
    'get_llm_client',
    # 社交功能
    'SocialClient',
    'get_social_client',
    'SocialScheduler',
    'get_social_scheduler',
    'SocialEventHandlers',
]
