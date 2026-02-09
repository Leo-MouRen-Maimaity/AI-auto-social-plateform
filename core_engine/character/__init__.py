"""
角色模块

包含AI角色的核心功能：Agent、记忆系统、物品栏等
"""

from .memory import MemorySystem, MemoryType
from .inventory import Inventory, Item
from .perception import PerceptionSystem
from .agent import CharacterAgent

__all__ = [
    'MemorySystem', 'MemoryType',
    'Inventory', 'Item',
    'PerceptionSystem',
    'CharacterAgent'
]
