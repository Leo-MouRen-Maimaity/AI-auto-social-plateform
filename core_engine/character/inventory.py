"""
物品栏系统模块

管理AI角色的物品栏，包含物品定义、重量限制等
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
import json


class ItemType(str, Enum):
    """物品类型"""
    TOOL = "tool"           # 工具
    FOOD = "food"           # 食物
    MATERIAL = "material"   # 材料
    PHOTO = "photo"         # 照片
    DOCUMENT = "document"   # 文档
    GIFT = "gift"           # 礼物
    CURRENCY = "currency"   # 货币
    EQUIPMENT = "equipment" # 装备
    MISC = "misc"           # 杂项


@dataclass
class Item:
    """物品类"""
    id: int
    name: str
    item_type: ItemType
    weight: float = 1.0     # 重量（单位）
    quantity: int = 1       # 数量
    stackable: bool = True  # 是否可堆叠
    max_stack: int = 99     # 最大堆叠数
    description: str = ""
    
    # 可选属性
    value: float = 0.0      # 价值
    durability: Optional[int] = None  # 耐久度（None表示无耐久）
    max_durability: Optional[int] = None
    
    # 元数据（存储额外信息，如照片的描述等）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    obtained_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_weight(self) -> float:
        """总重量"""
        return self.weight * self.quantity
    
    @property
    def is_broken(self) -> bool:
        """是否损坏"""
        if self.durability is None:
            return False
        return self.durability <= 0
    
    def use(self) -> bool:
        """
        使用物品
        
        Returns:
            是否成功使用
        """
        if self.is_broken:
            return False
        
        if self.durability is not None:
            self.durability -= 1
        
        return True
    
    def repair(self, amount: int = None):
        """修复物品"""
        if self.durability is None or self.max_durability is None:
            return
        
        if amount is None:
            self.durability = self.max_durability
        else:
            self.durability = min(self.max_durability, self.durability + amount)
    
    def can_stack_with(self, other: 'Item') -> bool:
        """检查是否可以与另一个物品堆叠"""
        if not self.stackable or not other.stackable:
            return False
        return (self.name == other.name and 
                self.item_type == other.item_type and
                self.quantity < self.max_stack)
    
    def stack_with(self, other: 'Item') -> int:
        """
        与另一个物品堆叠
        
        Returns:
            剩余数量（无法堆叠的部分）
        """
        if not self.can_stack_with(other):
            return other.quantity
        
        available_space = self.max_stack - self.quantity
        to_add = min(available_space, other.quantity)
        
        self.quantity += to_add
        return other.quantity - to_add
    
    def split(self, amount: int) -> Optional['Item']:
        """
        分割物品
        
        Returns:
            分割出的新物品，失败返回None
        """
        if amount <= 0 or amount >= self.quantity:
            return None
        
        self.quantity -= amount
        
        new_item = Item(
            id=0,  # 需要外部分配新ID
            name=self.name,
            item_type=self.item_type,
            weight=self.weight,
            quantity=amount,
            stackable=self.stackable,
            max_stack=self.max_stack,
            description=self.description,
            value=self.value,
            metadata=self.metadata.copy()
        )
        
        return new_item
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'item_type': self.item_type.value,
            'weight': self.weight,
            'quantity': self.quantity,
            'stackable': self.stackable,
            'max_stack': self.max_stack,
            'description': self.description,
            'value': self.value,
            'durability': self.durability,
            'max_durability': self.max_durability,
            'metadata': self.metadata,
            'obtained_at': self.obtained_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        return cls(
            id=data['id'],
            name=data['name'],
            item_type=ItemType(data['item_type']),
            weight=data.get('weight', 1.0),
            quantity=data.get('quantity', 1),
            stackable=data.get('stackable', True),
            max_stack=data.get('max_stack', 99),
            description=data.get('description', ''),
            value=data.get('value', 0.0),
            durability=data.get('durability'),
            max_durability=data.get('max_durability'),
            metadata=data.get('metadata', {}),
            obtained_at=datetime.fromisoformat(data['obtained_at']) if 'obtained_at' in data else datetime.now()
        )
    
    @classmethod
    def from_db_row(cls, row) -> 'Item':
        """从数据库行创建"""
        metadata = {}
        if row.metadata:
            try:
                metadata = json.loads(row.metadata)
            except json.JSONDecodeError:
                pass
        
        return cls(
            id=row.id,
            name=row.name,
            item_type=ItemType(row.item_type) if row.item_type else ItemType.MISC,
            weight=row.weight or 1.0,
            quantity=row.quantity or 1,
            description=row.description or '',
            metadata=metadata
        )


class Inventory:
    """
    物品栏
    
    管理角色的物品，支持重量限制
    """
    
    def __init__(self, character_id: int, max_weight: float = 50.0, db_session=None):
        self.character_id = character_id
        self.max_weight = max_weight
        self._db = db_session
        
        self._items: Dict[int, Item] = {}  # item_id -> Item
        self._next_id = 1
    
    def load_from_db(self):
        """从数据库加载物品栏"""
        if not self._db:
            return
        
        from api_server.models import Inventory as InventoryModel
        
        rows = self._db.query(InventoryModel).filter(
            InventoryModel.user_id == self.character_id
        ).all()
        
        for row in rows:
            item = self._item_from_db_row(row)
            self._items[item.id] = item
        
        # 更新ID计数器
        if self._items:
            self._next_id = max(self._items.keys()) + 1
    
    def _item_from_db_row(self, row) -> 'Item':
        """从数据库行创建Item对象（适配数据库字段）"""
        # 数据库字段: id, user_id, item_name, weight, quantity, properties
        properties = row.properties or {}
        if isinstance(properties, str):
            import json
            properties = json.loads(properties)
        
        # 尝试从properties中获取item_type，默认为MISC
        item_type_str = properties.get('item_type', 'misc')
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            item_type = ItemType.MISC
        
        return Item(
            id=row.id,
            item_type=item_type,
            name=row.item_name,
            quantity=row.quantity or 1,
            weight=row.weight or 0.0,
            description=properties.get('description', ''),
            stackable=properties.get('stackable', True),
            max_stack=properties.get('max_stack', 99),
            metadata=properties.get('metadata', {})
        )
    
    def _generate_id(self) -> int:
        """生成新的物品ID"""
        id = self._next_id
        self._next_id += 1
        return id
    
    def _save_to_db(self, item: Item):
        """保存物品到数据库"""
        if not self._db:
            return
        
        from api_server.models import Inventory as InventoryModel
        import json
        
        existing = self._db.query(InventoryModel).filter(
            InventoryModel.id == item.id
        ).first()
        
        # 构建properties JSON
        properties = {
            'item_type': item.item_type.value,
            'description': item.description,
            'stackable': item.stackable,
            'max_stack': item.max_stack,
            'metadata': item.metadata
        }
        
        if existing:
            existing.quantity = item.quantity
            existing.properties = properties
        else:
            db_item = InventoryModel(
                user_id=self.character_id,
                item_name=item.name,
                quantity=item.quantity,
                weight=item.weight,
                properties=properties
            )
            self._db.add(db_item)
            self._db.flush()  # 获取自动生成的ID
            item.id = db_item.id
        
        self._db.commit()
    
    def _delete_from_db(self, item_id: int):
        """从数据库删除物品"""
        if not self._db:
            return
        
        from api_server.models import Inventory as InventoryModel
        
        self._db.query(InventoryModel).filter(InventoryModel.id == item_id).delete()
        self._db.commit()
    
    @property
    def current_weight(self) -> float:
        """当前总重量"""
        return sum(item.total_weight for item in self._items.values())
    
    @property
    def available_weight(self) -> float:
        """可用重量空间"""
        return self.max_weight - self.current_weight
    
    @property
    def is_overweight(self) -> bool:
        """是否超重"""
        return self.current_weight > self.max_weight
    
    def can_add(self, item: Item) -> bool:
        """检查是否可以添加物品"""
        return item.total_weight <= self.available_weight
    
    def add(self, item: Item) -> tuple:
        """
        添加物品到物品栏
        
        Returns:
            (success, message)
        """
        if not self.can_add(item):
            return False, f"超出负重限制（需要{item.total_weight}，可用{self.available_weight:.1f}）"
        
        # 尝试堆叠
        if item.stackable:
            for existing_item in self._items.values():
                if existing_item.can_stack_with(item):
                    remaining = existing_item.stack_with(item)
                    self._save_to_db(existing_item)
                    
                    if remaining <= 0:
                        return True, f"已将{item.name}堆叠到现有物品"
                    
                    item.quantity = remaining
        
        # 添加为新物品
        if item.id == 0:
            item.id = self._generate_id()
        
        self._items[item.id] = item
        self._save_to_db(item)
        
        return True, f"已添加{item.name} x{item.quantity}"
    
    def remove(self, item_id: int, quantity: int = None) -> tuple:
        """
        移除物品
        
        Args:
            item_id: 物品ID
            quantity: 移除数量，None表示全部
            
        Returns:
            (success, removed_item_or_message)
        """
        if item_id not in self._items:
            return False, "物品不存在"
        
        item = self._items[item_id]
        
        if quantity is None or quantity >= item.quantity:
            # 移除整个物品
            del self._items[item_id]
            self._delete_from_db(item_id)
            return True, item
        
        # 部分移除
        removed_item = item.split(quantity)
        if removed_item:
            removed_item.id = self._generate_id()
            self._save_to_db(item)
            return True, removed_item
        
        return False, "无法移除指定数量"
    
    def get(self, item_id: int) -> Optional[Item]:
        """获取物品"""
        return self._items.get(item_id)
    
    def get_by_name(self, name: str) -> Optional[Item]:
        """根据名称获取物品"""
        for item in self._items.values():
            if item.name == name:
                return item
        return None
    
    def get_by_type(self, item_type: ItemType) -> List[Item]:
        """获取指定类型的所有物品"""
        return [item for item in self._items.values() if item.item_type == item_type]
    
    def get_all(self) -> List[Item]:
        """获取所有物品"""
        return list(self._items.values())
    
    def has(self, name: str, quantity: int = 1) -> bool:
        """检查是否有指定数量的物品"""
        for item in self._items.values():
            if item.name == name and item.quantity >= quantity:
                return True
        return False
    
    def use_item(self, item_id: int) -> tuple:
        """
        使用物品
        
        Returns:
            (success, message)
        """
        item = self.get(item_id)
        if not item:
            return False, "物品不存在"
        
        if not item.use():
            return False, "物品已损坏"
        
        # 如果是消耗品，减少数量
        if item.item_type in [ItemType.FOOD]:
            item.quantity -= 1
            if item.quantity <= 0:
                del self._items[item_id]
                self._delete_from_db(item_id)
                return True, f"使用了{item.name}（已用完）"
        
        self._save_to_db(item)
        return True, f"使用了{item.name}"
    
    def get_inventory_text(self) -> str:
        """获取物品栏的文本描述"""
        if not self._items:
            return "物品栏为空"
        
        lines = [f"物品栏（{self.current_weight:.1f}/{self.max_weight}kg）："]
        
        for item in sorted(self._items.values(), key=lambda x: x.item_type.value):
            line = f"  - {item.name}"
            if item.quantity > 1:
                line += f" x{item.quantity}"
            if item.durability is not None:
                line += f" [{item.durability}/{item.max_durability}]"
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取物品栏统计"""
        type_counts = {}
        for item in self._items.values():
            type_name = item.item_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + item.quantity
        
        return {
            'character_id': self.character_id,
            'total_items': len(self._items),
            'total_quantity': sum(item.quantity for item in self._items.values()),
            'current_weight': self.current_weight,
            'max_weight': self.max_weight,
            'weight_percentage': (self.current_weight / self.max_weight * 100) if self.max_weight > 0 else 0,
            'by_type': type_counts
        }


# ===== 预定义物品模板 =====

class ItemTemplates:
    """常用物品模板"""
    
    @staticmethod
    def create_photo(description: str, location: str = "", 
                     image_path: str = "") -> Item:
        """创建照片物品"""
        return Item(
            id=0,
            name="照片",
            item_type=ItemType.PHOTO,
            weight=0.01,
            stackable=False,
            description=description,
            metadata={
                'location': location,
                'image_path': image_path,
                'description': description
            }
        )
    
    @staticmethod
    def create_phone() -> Item:
        """创建手机"""
        return Item(
            id=0,
            name="手机",
            item_type=ItemType.TOOL,
            weight=0.2,
            stackable=False,
            description="可以查看社交网络、发消息、拍照",
            durability=100,
            max_durability=100,
            metadata={
                'actions': ['browse_feed', 'send_message', 'take_photo', 'check_notifications']
            }
        )
    
    @staticmethod
    def create_food(name: str, weight: float = 0.5, 
                    energy_restore: int = 20) -> Item:
        """创建食物"""
        return Item(
            id=0,
            name=name,
            item_type=ItemType.FOOD,
            weight=weight,
            stackable=True,
            max_stack=10,
            description=f"食物，恢复{energy_restore}点体力",
            metadata={
                'energy_restore': energy_restore
            }
        )
    
    @staticmethod
    def create_money(amount: int) -> Item:
        """创建货币"""
        return Item(
            id=0,
            name="金币",
            item_type=ItemType.CURRENCY,
            weight=0.0,
            quantity=amount,
            stackable=True,
            max_stack=999999,
            description="通用货币",
            value=1.0
        )
