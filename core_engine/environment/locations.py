"""
地点管理模块

定义游戏世界中的地点和地点管理器
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set
import math


class LocationType(str, Enum):
    """地点类型"""
    PUBLIC = "public"           # 公共场所
    COMMERCIAL = "commercial"   # 商业场所
    RESIDENTIAL = "residential" # 住宅
    WORKPLACE = "workplace"     # 工作场所
    MEDICAL = "medical"         # 医疗设施
    GOVERNMENT = "government"   # 政府机构
    EDUCATION = "education"     # 教育机构
    RECREATION = "recreation"   # 休闲场所


@dataclass
class Location:
    """
    地点类
    
    表示游戏世界中的一个位置
    """
    id: int
    name: str
    location_type: LocationType
    x: float
    y: float
    width: float = 10.0
    height: float = 10.0
    description: str = ""
    
    # 可选属性
    owner_id: Optional[int] = None  # 所有者（住宅的主人等）
    capacity: int = 100             # 最大容纳人数
    is_indoor: bool = True          # 是否室内
    opening_hour: int = 0           # 开放时间（0表示全天开放）
    closing_hour: int = 24          # 关闭时间
    
    # 交互方法
    available_actions: List[str] = field(default_factory=list)
    
    # 当前状态
    current_occupants: Set[int] = field(default_factory=set)
    
    @property
    def center(self) -> tuple:
        """地点中心坐标"""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def bounds(self) -> tuple:
        """地点边界 (x1, y1, x2, y2)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def contains_point(self, px: float, py: float) -> bool:
        """检查点是否在地点范围内"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)
    
    def distance_to(self, other: 'Location') -> float:
        """计算到另一个地点的距离（中心点之间）"""
        cx1, cy1 = self.center
        cx2, cy2 = other.center
        return math.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)
    
    def distance_to_point(self, px: float, py: float) -> float:
        """计算到某点的距离（从中心点）"""
        cx, cy = self.center
        return math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
    
    def is_open(self, hour: int) -> bool:
        """检查在指定时间是否开放"""
        if self.opening_hour == 0 and self.closing_hour == 24:
            return True
        if self.opening_hour < self.closing_hour:
            return self.opening_hour <= hour < self.closing_hour
        else:
            # 跨越午夜的情况
            return hour >= self.opening_hour or hour < self.closing_hour
    
    def can_enter(self, character_id: int, hour: int) -> tuple:
        """
        检查角色是否可以进入
        
        Returns:
            (can_enter, reason)
        """
        if not self.is_open(hour):
            return False, "地点已关闭"
        
        if len(self.current_occupants) >= self.capacity:
            return False, "人数已满"
        
        return True, ""
    
    def enter(self, character_id: int) -> bool:
        """角色进入地点"""
        if character_id not in self.current_occupants:
            self.current_occupants.add(character_id)
            return True
        return False
    
    def leave(self, character_id: int) -> bool:
        """角色离开地点"""
        if character_id in self.current_occupants:
            self.current_occupants.discard(character_id)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'location_type': self.location_type.value,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'description': self.description,
            'owner_id': self.owner_id,
            'capacity': self.capacity,
            'is_indoor': self.is_indoor,
            'opening_hour': self.opening_hour,
            'closing_hour': self.closing_hour,
            'available_actions': self.available_actions,
            'current_occupants': list(self.current_occupants)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """从字典创建"""
        loc = cls(
            id=data['id'],
            name=data['name'],
            location_type=LocationType(data['location_type']),
            x=data['x'],
            y=data['y'],
            width=data.get('width', 10.0),
            height=data.get('height', 10.0),
            description=data.get('description', ''),
            owner_id=data.get('owner_id'),
            capacity=data.get('capacity', 100),
            is_indoor=data.get('is_indoor', True),
            opening_hour=data.get('opening_hour', 0),
            closing_hour=data.get('closing_hour', 24),
            available_actions=data.get('available_actions', [])
        )
        loc.current_occupants = set(data.get('current_occupants', []))
        return loc
    
    @classmethod
    def from_db_row(cls, row) -> 'Location':
        """从数据库行创建"""
        return cls(
            id=row.id,
            name=row.name,
            location_type=LocationType(row.location_type) if row.location_type else LocationType.PUBLIC,
            x=row.x,
            y=row.y,
            width=row.width or 10.0,
            height=row.height or 10.0,
            description=row.description or ''
        )


class LocationManager:
    """
    地点管理器
    
    管理游戏世界中的所有地点
    """
    
    def __init__(self):
        self._locations: Dict[int, Location] = {}
        self._locations_by_type: Dict[LocationType, List[Location]] = {}
        self._character_locations: Dict[int, int] = {}  # character_id -> location_id
    
    def add(self, location: Location):
        """添加地点"""
        self._locations[location.id] = location
        
        if location.location_type not in self._locations_by_type:
            self._locations_by_type[location.location_type] = []
        self._locations_by_type[location.location_type].append(location)
    
    def remove(self, location_id: int):
        """移除地点"""
        if location_id in self._locations:
            location = self._locations[location_id]
            del self._locations[location_id]
            
            if location.location_type in self._locations_by_type:
                self._locations_by_type[location.location_type] = [
                    loc for loc in self._locations_by_type[location.location_type]
                    if loc.id != location_id
                ]
    
    def get(self, location_id: int) -> Optional[Location]:
        """获取地点"""
        return self._locations.get(location_id)
    
    def get_by_name(self, name: str) -> Optional[Location]:
        """根据名称获取地点"""
        for location in self._locations.values():
            if location.name == name:
                return location
        return None
    
    def get_by_type(self, location_type: LocationType) -> List[Location]:
        """获取指定类型的所有地点"""
        return self._locations_by_type.get(location_type, [])
    
    def get_all(self) -> List[Location]:
        """获取所有地点"""
        return list(self._locations.values())
    
    def find_at_point(self, x: float, y: float) -> Optional[Location]:
        """查找包含指定点的地点"""
        for location in self._locations.values():
            if location.contains_point(x, y):
                return location
        return None
    
    def find_nearby(self, x: float, y: float, radius: float) -> List[Location]:
        """查找指定范围内的地点"""
        nearby = []
        for location in self._locations.values():
            if location.distance_to_point(x, y) <= radius:
                nearby.append(location)
        return sorted(nearby, key=lambda loc: loc.distance_to_point(x, y))
    
    def find_nearest(self, x: float, y: float, 
                     location_type: Optional[LocationType] = None) -> Optional[Location]:
        """查找最近的地点"""
        candidates = self._locations.values()
        if location_type:
            candidates = self._locations_by_type.get(location_type, [])
        
        if not candidates:
            return None
        
        return min(candidates, key=lambda loc: loc.distance_to_point(x, y))
    
    def get_character_location(self, character_id: int) -> Optional[Location]:
        """获取角色当前所在地点"""
        location_id = self._character_locations.get(character_id)
        if location_id:
            return self.get(location_id)
        return None
    
    def move_character(self, character_id: int, 
                       to_location_id: int, hour: int = 12) -> tuple:
        """
        移动角色到指定地点
        
        Returns:
            (success, message)
        """
        new_location = self.get(to_location_id)
        if not new_location:
            return False, "目标地点不存在"
        
        can_enter, reason = new_location.can_enter(character_id, hour)
        if not can_enter:
            return False, reason
        
        # 离开当前地点
        current_location = self.get_character_location(character_id)
        if current_location:
            current_location.leave(character_id)
        
        # 进入新地点
        new_location.enter(character_id)
        self._character_locations[character_id] = to_location_id
        
        return True, f"已移动到{new_location.name}"
    
    def calculate_travel_time(self, from_location: Location, 
                              to_location: Location,
                              speed: float = 5.0) -> int:
        """
        计算两地之间的旅行时间（分钟）
        
        Args:
            from_location: 起点
            to_location: 终点
            speed: 移动速度（单位距离/分钟）
        """
        distance = from_location.distance_to(to_location)
        return max(1, int(distance / speed))
    
    def load_from_db(self, db_session):
        """从数据库加载地点"""
        from api_server.models import Location as LocationModel
        
        rows = db_session.query(LocationModel).all()
        for row in rows:
            location = Location.from_db_row(row)
            self.add(location)
        
        print(f"Loaded {len(self._locations)} locations from database")
    
    def get_map_data(self) -> Dict[str, Any]:
        """获取地图数据（用于渲染）"""
        return {
            'locations': [loc.to_dict() for loc in self._locations.values()],
            'bounds': self._calculate_bounds()
        }
    
    def _calculate_bounds(self) -> Dict[str, float]:
        """计算地图边界"""
        if not self._locations:
            return {'min_x': 0, 'min_y': 0, 'max_x': 100, 'max_y': 100}
        
        min_x = min(loc.x for loc in self._locations.values())
        min_y = min(loc.y for loc in self._locations.values())
        max_x = max(loc.x + loc.width for loc in self._locations.values())
        max_y = max(loc.y + loc.height for loc in self._locations.values())
        
        return {
            'min_x': min_x - 50,
            'min_y': min_y - 50,
            'max_x': max_x + 50,
            'max_y': max_y + 50
        }
