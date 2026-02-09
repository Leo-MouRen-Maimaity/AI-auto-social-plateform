"""
事件定义模块

定义游戏中的各类事件：个人事件、集体事件、突发事件
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventType(str, Enum):
    """事件类型枚举"""
    # 个人事件
    WORK = "work"                    # 工作
    WAIT = "wait"                    # 等待
    SLEEP = "sleep"                  # 睡眠
    TAKE_PHOTO = "take_photo"        # 拍照
    POST_CONTENT = "post_content"    # 发帖
    USE_PHONE = "use_phone"          # 看手机
    MOVE = "move"                    # 移动
    
    # 集体事件
    OFFLINE_CHAT = "offline_chat"    # 线下群聊
    ONLINE_GROUP_CHAT = "online_group_chat"  # 网络群聊
    ONLINE_PRIVATE_CHAT = "online_private_chat"  # 网络私聊
    
    # 突发事件
    ENCOUNTER = "encounter"          # 相遇
    FATIGUE_WARNING = "fatigue_warning"  # 疲劳警告
    VISUAL_EVENT = "visual_event"    # 视觉事件
    AUDIO_EVENT = "audio_event"      # 声音事件


class EventPriority(int, Enum):
    """事件优先级（数字越小优先级越高）"""
    CRITICAL = 0      # 最高优先级（系统事件）
    EMERGENCY = 10    # 紧急事件（突发事件）
    HIGH = 20         # 高优先级
    NORMAL = 50       # 普通优先级
    LOW = 80          # 低优先级
    BACKGROUND = 100  # 后台任务


class EventStatus(str, Enum):
    """事件状态"""
    PENDING = "pending"          # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消
    FAILED = "failed"            # 执行失败


@dataclass
class GameEvent:
    """
    游戏事件基类
    
    Attributes:
        id: 事件唯一标识（数据库ID或生成的UUID）
        event_type: 事件类型
        character_id: 执行事件的角色ID
        scheduled_time: 计划执行时间（游戏分钟）
        duration: 事件持续时间（分钟）
        priority: 事件优先级
        status: 事件状态
        data: 事件附加数据
        created_at: 创建时间
    """
    event_type: EventType
    character_id: int
    scheduled_time: int  # 游戏时间（分钟），从游戏开始计算
    duration: int = 0    # 持续时间（分钟）
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    data: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def end_time(self) -> int:
        """事件结束时间"""
        return self.scheduled_time + self.duration
    
    def __lt__(self, other: 'GameEvent') -> bool:
        """比较运算符，用于优先队列排序"""
        # 先按时间排序，时间相同按优先级排序
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority.value < other.priority.value
    
    def __eq__(self, other: 'GameEvent') -> bool:
        if not isinstance(other, GameEvent):
            return False
        return self.id == other.id if self.id else False
    
    def __hash__(self) -> int:
        return hash(self.id) if self.id else hash(id(self))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'character_id': self.character_id,
            'scheduled_time': self.scheduled_time,
            'duration': self.duration,
            'priority': self.priority.value,
            'status': self.status.value,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameEvent':
        """从字典创建事件"""
        return cls(
            id=data.get('id'),
            event_type=EventType(data['event_type']),
            character_id=data['character_id'],
            scheduled_time=data['scheduled_time'],
            duration=data.get('duration', 0),
            priority=EventPriority(data.get('priority', EventPriority.NORMAL.value)),
            status=EventStatus(data.get('status', EventStatus.PENDING.value)),
            data=data.get('data', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class PersonalEvent(GameEvent):
    """
    个人事件
    
    包括：工作、等待、睡眠、拍照、发帖、看手机等
    """
    
    @classmethod
    def create_work(cls, character_id: int, scheduled_time: int, 
                    duration: int, work_type: str = "general") -> 'PersonalEvent':
        """创建工作事件"""
        return cls(
            event_type=EventType.WORK,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.NORMAL,
            data={'work_type': work_type}
        )
    
    @classmethod
    def create_sleep(cls, character_id: int, scheduled_time: int,
                     duration: int = 480) -> 'PersonalEvent':
        """创建睡眠事件（默认8小时=480分钟）"""
        return cls(
            event_type=EventType.SLEEP,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.HIGH,
            data={'need_summary': True}  # 需要总结当天内容
        )
    
    @classmethod
    def create_take_photo(cls, character_id: int, scheduled_time: int,
                          is_selfie: bool = False, 
                          direction: str = "forward",
                          pose: str = "standing") -> 'PersonalEvent':
        """创建拍照事件"""
        return cls(
            event_type=EventType.TAKE_PHOTO,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=5,  # 拍照5分钟
            priority=EventPriority.NORMAL,
            data={
                'is_selfie': is_selfie,
                'direction': direction,
                'pose': pose
            }
        )
    
    @classmethod
    def create_post_content(cls, character_id: int, scheduled_time: int,
                            content: str = "", 
                            image_id: Optional[int] = None) -> 'PersonalEvent':
        """创建发帖事件"""
        return cls(
            event_type=EventType.POST_CONTENT,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=3,  # 发帖3分钟
            priority=EventPriority.NORMAL,
            data={
                'content': content,
                'image_id': image_id
            }
        )
    
    @classmethod
    def create_use_phone(cls, character_id: int, scheduled_time: int,
                         duration: int = 30,
                         activities: Optional[List[str]] = None) -> 'PersonalEvent':
        """
        创建看手机事件
        
        activities: 可选活动列表 ['browse_posts', 'check_messages', 'view_comments']
        """
        return cls(
            event_type=EventType.USE_PHONE,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.LOW,
            data={
                'activities': activities or ['browse_posts'],
                'posts_viewed': 0,
                'messages_checked': False
            }
        )
    
    @classmethod
    def create_move(cls, character_id: int, scheduled_time: int,
                    target_x: float, target_y: float,
                    target_location_id: Optional[int] = None) -> 'PersonalEvent':
        """创建移动事件"""
        return cls(
            event_type=EventType.MOVE,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=0,  # 持续时间由距离计算
            priority=EventPriority.NORMAL,
            data={
                'target_x': target_x,
                'target_y': target_y,
                'target_location_id': target_location_id
            }
        )


@dataclass
class CollectiveEvent(GameEvent):
    """
    集体事件
    
    包括：线下群聊、网络群聊、网络私聊等
    需要多个角色参与
    """
    participant_ids: List[int] = field(default_factory=list)
    max_chat_turns: int = 10  # 最大聊天轮次
    
    @classmethod
    def create_offline_chat(cls, initiator_id: int, participant_ids: List[int],
                            scheduled_time: int, duration: int = 30,
                            location_id: Optional[int] = None) -> 'CollectiveEvent':
        """创建线下群聊事件"""
        return cls(
            event_type=EventType.OFFLINE_CHAT,
            character_id=initiator_id,
            participant_ids=participant_ids,
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.NORMAL,
            data={
                'location_id': location_id,
                'chat_history': [],
                'current_turn': 0
            }
        )
    
    @classmethod
    def create_online_private_chat(cls, sender_id: int, receiver_id: int,
                                   scheduled_time: int, 
                                   duration: int = 15) -> 'CollectiveEvent':
        """创建网络私聊事件"""
        return cls(
            event_type=EventType.ONLINE_PRIVATE_CHAT,
            character_id=sender_id,
            participant_ids=[receiver_id],
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.NORMAL,
            data={
                'chat_history': [],
                'current_turn': 0
            }
        )
    
    @classmethod
    def create_online_group_chat(cls, initiator_id: int, group_id: int,
                                 participant_ids: List[int],
                                 scheduled_time: int,
                                 duration: int = 30) -> 'CollectiveEvent':
        """创建网络群聊事件"""
        return cls(
            event_type=EventType.ONLINE_GROUP_CHAT,
            character_id=initiator_id,
            participant_ids=participant_ids,
            scheduled_time=scheduled_time,
            duration=duration,
            priority=EventPriority.NORMAL,
            data={
                'group_id': group_id,
                'chat_history': [],
                'current_turn': 0
            }
        )


@dataclass
class EmergencyEvent(GameEvent):
    """
    突发事件
    
    包括：相遇、疲劳警告、视觉/声音事件等
    优先级较高，可能打断其他事件
    """
    can_interrupt: bool = True  # 是否可以打断当前事件
    
    @classmethod
    def create_encounter(cls, character_id: int, other_character_id: int,
                         scheduled_time: int, location_id: int) -> 'EmergencyEvent':
        """创建相遇事件"""
        return cls(
            event_type=EventType.ENCOUNTER,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=1,  # 相遇判定1分钟
            priority=EventPriority.EMERGENCY,
            can_interrupt=True,
            data={
                'other_character_id': other_character_id,
                'location_id': location_id,
                'interaction_chosen': False
            }
        )
    
    @classmethod
    def create_fatigue_warning(cls, character_id: int, 
                               scheduled_time: int,
                               fatigue_level: int) -> 'EmergencyEvent':
        """创建疲劳警告事件"""
        return cls(
            event_type=EventType.FATIGUE_WARNING,
            character_id=character_id,
            scheduled_time=scheduled_time,
            duration=0,
            priority=EventPriority.HIGH,
            can_interrupt=False,  # 不打断，只是提醒
            data={
                'fatigue_level': fatigue_level,
                'suggested_action': 'rest' if fatigue_level < 20 else 'slow_down'
            }
        )
