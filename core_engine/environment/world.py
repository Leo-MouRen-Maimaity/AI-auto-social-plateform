"""
世界地图模块

管理游戏世界的整体状态，包括天气、环境、角色位置等
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set
from enum import Enum
import random

from .locations import Location, LocationType, LocationManager


class Weather(str, Enum):
    """天气类型"""
    SUNNY = "sunny"         # 晴天
    CLOUDY = "cloudy"       # 多云
    RAINY = "rainy"         # 下雨
    STORMY = "stormy"       # 暴风雨
    SNOWY = "snowy"         # 下雪
    FOGGY = "foggy"         # 大雾


class Season(str, Enum):
    """季节"""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


@dataclass
class WorldConfig:
    """世界配置"""
    name: str = "AI社区"
    
    # 地图尺寸
    map_width: float = 500.0
    map_height: float = 500.0
    
    # 时间配置
    minutes_per_real_second: float = 1.0  # 每现实秒经过的游戏分钟
    
    # 天气配置
    weather_change_probability: float = 0.1  # 每小时天气变化概率
    
    # 移动配置
    default_walk_speed: float = 5.0   # 默认步行速度（单位/分钟）
    default_run_speed: float = 10.0   # 默认跑步速度
    
    # 疲劳配置
    fatigue_per_minute_active: float = 0.1   # 活动时每分钟疲劳消耗
    fatigue_per_minute_walking: float = 0.2  # 行走时每分钟疲劳消耗
    fatigue_per_minute_running: float = 0.5  # 跑步时每分钟疲劳消耗
    fatigue_recovery_sleeping: float = 1.0   # 睡眠时每分钟恢复
    
    # 温度配置（摄氏度）
    base_temperature: Dict[Season, float] = field(default_factory=lambda: {
        Season.SPRING: 18.0,
        Season.SUMMER: 28.0,
        Season.AUTUMN: 15.0,
        Season.WINTER: 5.0
    })


@dataclass
class CharacterPosition:
    """角色位置信息"""
    character_id: int
    x: float
    y: float
    location_id: Optional[int] = None
    is_moving: bool = False
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    
    def update_position(self, new_x: float, new_y: float):
        """更新位置"""
        self.x = new_x
        self.y = new_y
        
        # 检查是否到达目标
        if self.is_moving and self.target_x is not None:
            distance = ((self.target_x - new_x) ** 2 + 
                       (self.target_y - new_y) ** 2) ** 0.5
            if distance < 1.0:
                self.is_moving = False
                self.target_x = None
                self.target_y = None


class World:
    """
    游戏世界
    
    管理整个游戏世界的状态
    """
    
    def __init__(self, config: Optional[WorldConfig] = None):
        self.config = config or WorldConfig()
        self.location_manager = LocationManager()
        
        # 世界状态
        self.current_day: int = 1
        self.current_weather: Weather = Weather.SUNNY
        self.current_season: Season = Season.SPRING
        self.outdoor_temperature: float = 20.0
        self.indoor_temperature: float = 22.0
        
        # 角色位置跟踪
        self._character_positions: Dict[int, CharacterPosition] = {}
    
    def initialize(self, db_session=None):
        """初始化世界"""
        if db_session:
            self.location_manager.load_from_db(db_session)
        
        self._update_temperature()
        print(f"World '{self.config.name}' initialized with {len(self.location_manager.get_all())} locations")
    
    def update(self, game_hour: int, game_day: int):
        """
        更新世界状态
        
        每小时调用一次
        """
        self.current_day = game_day
        
        # 更新季节（每30天换季）
        season_index = ((game_day - 1) // 30) % 4
        self.current_season = list(Season)[season_index]
        
        # 可能更新天气
        if random.random() < self.config.weather_change_probability:
            self._change_weather()
        
        # 更新温度
        self._update_temperature(game_hour)
    
    def _change_weather(self):
        """改变天气"""
        # 根据季节确定可能的天气
        weather_weights = self._get_weather_weights()
        
        weathers = list(weather_weights.keys())
        weights = list(weather_weights.values())
        
        self.current_weather = random.choices(weathers, weights=weights, k=1)[0]
    
    def _get_weather_weights(self) -> Dict[Weather, float]:
        """获取各种天气的概率权重（根据季节）"""
        base_weights = {
            Weather.SUNNY: 0.4,
            Weather.CLOUDY: 0.3,
            Weather.RAINY: 0.15,
            Weather.STORMY: 0.05,
            Weather.SNOWY: 0.0,
            Weather.FOGGY: 0.1
        }
        
        if self.current_season == Season.SUMMER:
            base_weights[Weather.SUNNY] = 0.5
            base_weights[Weather.STORMY] = 0.1
        elif self.current_season == Season.WINTER:
            base_weights[Weather.SNOWY] = 0.2
            base_weights[Weather.SUNNY] = 0.2
            base_weights[Weather.CLOUDY] = 0.4
        elif self.current_season == Season.SPRING:
            base_weights[Weather.RAINY] = 0.25
        elif self.current_season == Season.AUTUMN:
            base_weights[Weather.FOGGY] = 0.2
            base_weights[Weather.CLOUDY] = 0.35
        
        return base_weights
    
    def _update_temperature(self, hour: int = 12):
        """更新温度"""
        base_temp = self.config.base_temperature.get(self.current_season, 20.0)
        
        # 日间温度变化（6点最低，14点最高）
        hour_factor = -abs(hour - 14) / 14 * 8  # -8 到 0
        
        # 天气影响
        weather_factor = {
            Weather.SUNNY: 2,
            Weather.CLOUDY: 0,
            Weather.RAINY: -3,
            Weather.STORMY: -5,
            Weather.SNOWY: -8,
            Weather.FOGGY: -2
        }.get(self.current_weather, 0)
        
        self.outdoor_temperature = base_temp + hour_factor + weather_factor
        self.indoor_temperature = max(18.0, min(26.0, base_temp))
    
    def get_character_position(self, character_id: int) -> Optional[CharacterPosition]:
        """获取角色位置"""
        return self._character_positions.get(character_id)
    
    def set_character_position(self, character_id: int, x: float, y: float,
                               location_id: Optional[int] = None):
        """设置角色位置"""
        if character_id not in self._character_positions:
            self._character_positions[character_id] = CharacterPosition(
                character_id=character_id,
                x=x,
                y=y,
                location_id=location_id
            )
        else:
            pos = self._character_positions[character_id]
            pos.x = x
            pos.y = y
            pos.location_id = location_id
        
        # 同步到地点管理器
        if location_id:
            self.location_manager.move_character(character_id, location_id)
    
    def start_character_movement(self, character_id: int,
                                  target_x: float, target_y: float) -> bool:
        """开始角色移动"""
        pos = self.get_character_position(character_id)
        if not pos:
            return False
        
        pos.is_moving = True
        pos.target_x = target_x
        pos.target_y = target_y
        return True
    
    def calculate_movement_time(self, character_id: int,
                                target_x: float, target_y: float,
                                running: bool = False) -> int:
        """计算移动到目标位置需要的时间（分钟）"""
        pos = self.get_character_position(character_id)
        if not pos:
            return 0
        
        distance = ((target_x - pos.x) ** 2 + (target_y - pos.y) ** 2) ** 0.5
        speed = self.config.default_run_speed if running else self.config.default_walk_speed
        
        return max(1, int(distance / speed))
    
    def get_nearby_characters(self, x: float, y: float, 
                              radius: float = 20.0) -> List[int]:
        """获取附近的角色ID列表"""
        nearby = []
        for char_id, pos in self._character_positions.items():
            distance = ((pos.x - x) ** 2 + (pos.y - y) ** 2) ** 0.5
            if distance <= radius:
                nearby.append(char_id)
        return nearby
    
    def get_characters_at_location(self, location_id: int) -> List[int]:
        """获取指定地点的所有角色"""
        location = self.location_manager.get(location_id)
        if location:
            return list(location.current_occupants)
        return []
    
    def check_encounter(self, character_id: int, 
                        encounter_radius: float = 5.0) -> List[int]:
        """
        检查角色是否与其他角色相遇
        
        Returns:
            可能相遇的角色ID列表
        """
        pos = self.get_character_position(character_id)
        if not pos:
            return []
        
        encounters = []
        for other_id, other_pos in self._character_positions.items():
            if other_id == character_id:
                continue
            
            distance = ((pos.x - other_pos.x) ** 2 + 
                       (pos.y - other_pos.y) ** 2) ** 0.5
            
            if distance <= encounter_radius:
                encounters.append(other_id)
        
        return encounters
    
    def get_environment_description(self, character_id: int) -> Dict[str, Any]:
        """
        获取角色周围的环境描述
        
        用于提供给AI做决策
        """
        pos = self.get_character_position(character_id)
        if not pos:
            return {}
        
        # 当前地点
        current_location = None
        if pos.location_id:
            current_location = self.location_manager.get(pos.location_id)
        
        # 附近地点
        nearby_locations = self.location_manager.find_nearby(pos.x, pos.y, 50.0)
        
        # 附近角色
        nearby_characters = self.get_nearby_characters(pos.x, pos.y, 30.0)
        nearby_characters = [c for c in nearby_characters if c != character_id]
        
        return {
            'position': {'x': pos.x, 'y': pos.y},
            'current_location': current_location.to_dict() if current_location else None,
            'nearby_locations': [
                {'id': loc.id, 'name': loc.name, 'type': loc.location_type.value,
                 'distance': loc.distance_to_point(pos.x, pos.y)}
                for loc in nearby_locations[:5]
            ],
            'nearby_characters': nearby_characters,
            'weather': self.current_weather.value,
            'season': self.current_season.value,
            'temperature': {
                'outdoor': self.outdoor_temperature,
                'indoor': self.indoor_temperature
            },
            'is_indoor': current_location.is_indoor if current_location else False
        }
    
    def get_world_state(self) -> Dict[str, Any]:
        """获取世界状态摘要"""
        return {
            'name': self.config.name,
            'day': self.current_day,
            'season': self.current_season.value,
            'weather': self.current_weather.value,
            'temperature': {
                'outdoor': self.outdoor_temperature,
                'indoor': self.indoor_temperature
            },
            'locations_count': len(self.location_manager.get_all()),
            'active_characters': len(self._character_positions)
        }
