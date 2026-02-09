"""
环境感知模块

为AI角色提供环境信息，包括周围物品、角色、地点等
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class EmotionState(str, Enum):
    """情绪状态"""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    TIRED = "tired"
    BORED = "bored"


@dataclass
class PhysicalState:
    """身体状态"""
    fatigue: float = 0.0          # 疲劳值 0-100，高表示累
    hunger: float = 0.0           # 饥饿值 0-100，高表示饿
    health: float = 100.0         # 健康值 0-100
    emotion: EmotionState = EmotionState.NEUTRAL
    
    # 状态阈值
    FATIGUE_TIRED = 60
    FATIGUE_EXHAUSTED = 85
    HUNGER_HUNGRY = 50
    HUNGER_STARVING = 80
    
    @property
    def is_tired(self) -> bool:
        return self.fatigue >= self.FATIGUE_TIRED
    
    @property
    def is_exhausted(self) -> bool:
        return self.fatigue >= self.FATIGUE_EXHAUSTED
    
    @property
    def is_hungry(self) -> bool:
        return self.hunger >= self.HUNGER_HUNGRY
    
    @property
    def is_starving(self) -> bool:
        return self.hunger >= self.HUNGER_STARVING
    
    @property
    def needs_rest(self) -> bool:
        return self.is_exhausted or self.health < 50
    
    def add_fatigue(self, amount: float):
        """增加疲劳"""
        self.fatigue = min(100, self.fatigue + amount)
        
        # 疲劳过高影响情绪
        if self.fatigue >= self.FATIGUE_EXHAUSTED:
            self.emotion = EmotionState.TIRED
    
    def recover_fatigue(self, amount: float):
        """恢复疲劳"""
        self.fatigue = max(0, self.fatigue - amount)
    
    def add_hunger(self, amount: float):
        """增加饥饿"""
        self.hunger = min(100, self.hunger + amount)
    
    def eat(self, amount: float):
        """进食减少饥饿"""
        self.hunger = max(0, self.hunger - amount)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fatigue': self.fatigue,
            'hunger': self.hunger,
            'health': self.health,
            'emotion': self.emotion.value,
            'is_tired': self.is_tired,
            'is_hungry': self.is_hungry,
            'needs_rest': self.needs_rest
        }
    
    def get_description(self) -> str:
        """获取状态的文字描述"""
        descriptions = []
        
        if self.is_exhausted:
            descriptions.append("非常疲惫")
        elif self.is_tired:
            descriptions.append("有些疲惫")
        
        if self.is_starving:
            descriptions.append("非常饥饿")
        elif self.is_hungry:
            descriptions.append("有些饿")
        
        if self.health < 30:
            descriptions.append("身体不适")
        elif self.health < 60:
            descriptions.append("身体状况一般")
        
        if self.emotion != EmotionState.NEUTRAL:
            emotion_text = {
                EmotionState.HAPPY: "心情愉快",
                EmotionState.SAD: "心情低落",
                EmotionState.ANGRY: "有些烦躁",
                EmotionState.ANXIOUS: "感到焦虑",
                EmotionState.EXCITED: "感到兴奋",
                EmotionState.TIRED: "疲惫不堪",
                EmotionState.BORED: "感到无聊"
            }
            descriptions.append(emotion_text.get(self.emotion, ""))
        
        if not descriptions:
            return "状态良好"
        
        return "，".join(descriptions)


@dataclass
class NearbyCharacter:
    """附近的角色信息"""
    id: int
    name: str
    distance: float
    is_ai: bool = True
    relationship_summary: str = ""  # 关系记忆摘要
    current_activity: str = ""      # 当前正在做的事


@dataclass
class NearbyObject:
    """附近的物品/对象"""
    id: int
    name: str
    object_type: str
    distance: float
    available_actions: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class EnvironmentPerception:
    """环境感知结果"""
    # 基本位置
    current_location_id: Optional[int] = None
    current_location_name: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    is_indoor: bool = True
    
    # 环境条件
    weather: str = "sunny"
    season: str = "spring"
    time_of_day: str = "morning"
    temperature: float = 22.0
    
    # 周围内容
    nearby_characters: List[NearbyCharacter] = field(default_factory=list)
    nearby_objects: List[NearbyObject] = field(default_factory=list)
    nearby_locations: List[Dict[str, Any]] = field(default_factory=list)
    
    # 身体状态
    physical_state: PhysicalState = field(default_factory=PhysicalState)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'location': {
                'id': self.current_location_id,
                'name': self.current_location_name,
                'position': {'x': self.position_x, 'y': self.position_y},
                'is_indoor': self.is_indoor
            },
            'environment': {
                'weather': self.weather,
                'season': self.season,
                'time_of_day': self.time_of_day,
                'temperature': self.temperature
            },
            'nearby_characters': [
                {
                    'id': c.id,
                    'name': c.name,
                    'distance': c.distance,
                    'relationship': c.relationship_summary,
                    'activity': c.current_activity
                }
                for c in self.nearby_characters
            ],
            'nearby_objects': [
                {
                    'id': o.id,
                    'name': o.name,
                    'type': o.object_type,
                    'distance': o.distance,
                    'actions': o.available_actions
                }
                for o in self.nearby_objects
            ],
            'nearby_locations': self.nearby_locations,
            'physical_state': self.physical_state.to_dict()
        }


class PerceptionSystem:
    """
    感知系统
    
    负责收集和整理角色周围的环境信息
    """
    
    def __init__(self, world=None, db_session=None):
        self._world = world
        self._db = db_session
    
    def set_world(self, world):
        """设置世界引用"""
        self._world = world
    
    def perceive(self, character_id: int, 
                 physical_state: PhysicalState = None) -> EnvironmentPerception:
        """
        感知环境
        
        Args:
            character_id: 角色ID
            physical_state: 角色的身体状态
            
        Returns:
            环境感知结果
        """
        perception = EnvironmentPerception()
        
        if physical_state:
            perception.physical_state = physical_state
        
        if not self._world:
            return perception
        
        # 获取角色位置
        pos = self._world.get_character_position(character_id)
        if pos:
            perception.position_x = pos.x
            perception.position_y = pos.y
            perception.current_location_id = pos.location_id
        
        # 获取当前地点信息
        if perception.current_location_id:
            location = self._world.location_manager.get(perception.current_location_id)
            if location:
                perception.current_location_name = location.name
                perception.is_indoor = location.is_indoor
        
        # 获取环境信息
        perception.weather = self._world.current_weather.value
        perception.season = self._world.current_season.value
        perception.temperature = (self._world.indoor_temperature 
                                  if perception.is_indoor 
                                  else self._world.outdoor_temperature)
        
        # 获取附近角色
        if pos:
            nearby_char_ids = self._world.get_nearby_characters(pos.x, pos.y, 30.0)
            for char_id in nearby_char_ids:
                if char_id == character_id:
                    continue
                
                char_pos = self._world.get_character_position(char_id)
                if char_pos:
                    distance = ((pos.x - char_pos.x) ** 2 + 
                               (pos.y - char_pos.y) ** 2) ** 0.5
                    
                    # 从数据库获取角色信息
                    char_info = self._get_character_info(char_id)
                    
                    perception.nearby_characters.append(NearbyCharacter(
                        id=char_id,
                        name=char_info.get('name', f'角色{char_id}'),
                        distance=distance,
                        is_ai=char_info.get('is_ai', True),
                        relationship_summary="",  # 后续由记忆系统填充
                        current_activity=""
                    ))
            
            # 获取附近地点
            nearby_locs = self._world.location_manager.find_nearby(pos.x, pos.y, 50.0)
            for loc in nearby_locs[:5]:
                if loc.id != perception.current_location_id:
                    perception.nearby_locations.append({
                        'id': loc.id,
                        'name': loc.name,
                        'type': loc.location_type.value,
                        'distance': loc.distance_to_point(pos.x, pos.y),
                        'is_open': loc.is_open(12)  # TODO: 使用实际时间
                    })
        
        return perception
    
    def _get_character_info(self, character_id: int) -> Dict[str, Any]:
        """从数据库获取角色信息"""
        if not self._db:
            return {}
        
        from api_server.models import User
        
        user = self._db.query(User).filter(User.id == character_id).first()
        if user:
            return {
                'name': user.nickname or user.username,
                'is_ai': user.is_ai
            }
        return {}
    
    def build_perception_prompt(self, perception: EnvironmentPerception,
                                 include_characters: bool = True,
                                 include_objects: bool = True) -> str:
        """
        构建环境感知的文字描述
        
        Args:
            perception: 环境感知结果
            include_characters: 是否包含附近角色
            include_objects: 是否包含附近物品
            
        Returns:
            格式化的环境描述文本
        """
        lines = []
        
        # 身体状态
        state_desc = perception.physical_state.get_description()
        lines.append(f"【身体状态】{state_desc}")
        lines.append(f"疲劳值：{perception.physical_state.fatigue:.0f}/100")
        
        # 当前位置
        if perception.current_location_name:
            lines.append(f"\n【当前位置】{perception.current_location_name}")
            lines.append(f"{'室内' if perception.is_indoor else '室外'}环境")
        else:
            lines.append(f"\n【当前位置】室外 ({perception.position_x:.0f}, {perception.position_y:.0f})")
        
        # 环境信息
        weather_text = {
            'sunny': '晴天',
            'cloudy': '多云',
            'rainy': '下雨',
            'stormy': '暴风雨',
            'snowy': '下雪',
            'foggy': '大雾'
        }.get(perception.weather, perception.weather)
        
        season_text = {
            'spring': '春季',
            'summer': '夏季',
            'autumn': '秋季',
            'winter': '冬季'
        }.get(perception.season, perception.season)
        
        lines.append(f"\n【环境】{season_text}，{weather_text}，气温{perception.temperature:.0f}°C")
        
        # 附近角色
        if include_characters and perception.nearby_characters:
            lines.append("\n【附近的人】")
            for char in perception.nearby_characters[:5]:
                distance_text = f"{char.distance:.0f}米" if char.distance >= 1 else "很近"
                line = f"- {char.name}（{distance_text}）"
                if char.relationship_summary:
                    line += f" - {char.relationship_summary}"
                if char.current_activity:
                    line += f" 正在{char.current_activity}"
                lines.append(line)
        
        # 附近地点
        if perception.nearby_locations:
            lines.append("\n【附近地点】")
            for loc in perception.nearby_locations[:5]:
                status = "开放" if loc.get('is_open', True) else "关闭"
                lines.append(f"- {loc['name']}（{loc['distance']:.0f}米，{status}）")
        
        # 附近物品
        if include_objects and perception.nearby_objects:
            lines.append("\n【附近物品】")
            for obj in perception.nearby_objects[:5]:
                actions = "、".join(obj.available_actions) if obj.available_actions else "无"
                lines.append(f"- {obj.name}（可执行：{actions}）")
        
        return "\n".join(lines)
    
    def get_available_actions(self, perception: EnvironmentPerception) -> List[Dict[str, Any]]:
        """
        根据环境感知获取可用的行动
        
        Returns:
            可用行动列表（每个行动包含预估时长 duration）
        """
        actions = []
        
        # 基础行动
        actions.append({
            'action': 'wait',
            'name': '等待',
            'description': '原地等待一段时间',
            'duration': 10,  # 默认10分钟
            'params': {}
        })
        
        actions.append({
            'action': 'look_around',
            'name': '观察周围',
            'description': '仔细观察周围环境',
            'duration': 5
        })
        
        # 移动行动
        for loc in perception.nearby_locations:
            if loc.get('is_open', True):
                # 根据距离估算时间（步行速度约5单位/分钟）
                distance = loc.get('distance', 50)
                walk_time = max(5, int(distance / 5))
                actions.append({
                    'action': 'move_to',
                    'name': f'前往{loc["name"]}',
                    'description': f'步行前往{loc["name"]}（约{distance:.0f}米）',
                    'duration': walk_time,
                    'params': {'location_id': loc['id']}
                })
        
        # 社交行动
        for char in perception.nearby_characters:
            actions.append({
                'action': 'talk_to',
                'name': f'和{char.name}交谈',
                'description': f'主动与{char.name}开始对话',
                'duration': 30,  # 对话通常30分钟
                'params': {'character_id': char.id}
            })
            
            actions.append({
                'action': 'greet',
                'name': f'向{char.name}打招呼',
                'description': f'简单地向{char.name}问好',
                'duration': 5,  # 打招呼很快
                'params': {'character_id': char.id}
            })
        
        # 物品行动
        for obj in perception.nearby_objects:
            for action in obj.available_actions:
                actions.append({
                    'action': f'interact_{action}',
                    'name': f'{action} {obj.name}',
                    'description': f'对{obj.name}执行{action}操作',
                    'duration': 15,  # 默认15分钟
                    'params': {'object_id': obj.id, 'interaction': action}
                })
        
        # 休息行动（根据疲劳度）
        if perception.physical_state.is_tired:
            actions.append({
                'action': 'rest',
                'name': '休息',
                'description': '找个地方休息一会儿，恢复精力',
                'duration': 30  # 休息30分钟
            })
        
        # 睡觉行动（疲劳度高时）
        if perception.physical_state.fatigue >= 70:
            actions.append({
                'action': 'sleep',
                'name': '睡觉',
                'description': '找个地方睡觉，好好休息（会睡到精力恢复）',
                'duration': 480  # 睡8小时
            })
        
        # 室内特定行动 - 拆解手机行为为具体社交操作
        if perception.is_indoor:
            # 浏览帖子
            actions.append({
                'action': 'browse_posts',
                'name': '浏览帖子',
                'description': '打开手机浏览社交网络上的帖子，看看大家都在聊什么',
                'duration': 15
            })
            
            # 发帖
            actions.append({
                'action': 'create_post',
                'name': '发帖',
                'description': '在社交网络上发一条帖子，分享你的想法或日常',
                'duration': 10
            })
            
            # 查看私信
            actions.append({
                'action': 'check_messages',
                'name': '查看私信',
                'description': '查看是否有人给你发私信，并回复消息',
                'duration': 10
            })
            
            # 主动发私信给某人（基于附近角色或认识的人）
            for char in perception.nearby_characters[:3]:  # 最多3个选项
                actions.append({
                    'action': 'send_message',
                    'name': f'给{char.name}发私信',
                    'description': f'主动给{char.name}发一条私信聊聊天',
                    'duration': 5,
                    'params': {'target_id': char.id, 'target_name': char.name}
                })
            
            # 查看某人的主页/帖子（基于附近角色）
            for char in perception.nearby_characters[:3]:  # 最多3个选项
                actions.append({
                    'action': 'view_user_profile',
                    'name': f'看{char.name}的帖子',
                    'description': f'打开{char.name}的主页，浏览TA发过的帖子',
                    'duration': 10,
                    'params': {'target_id': char.id, 'target_name': char.name}
                })
        
        return actions
