from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Enum, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class MemoryType(str, enum.Enum):
    COMMON = "common"
    DAILY = "daily"
    IMPORTANT = "important"
    KNOWLEDGE = "knowledge"
    RELATION = "relation"


class GroupType(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class EventStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImageGenStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))
    nickname = Column(String(50), nullable=False)
    avatar_path = Column(String(500))
    bio = Column(Text)
    is_ai = Column(Boolean, default=False, index=True)
    # AI专用字段
    personality = Column(Text)
    fatigue = Column(Integer, default=100)
    current_x = Column(Float, default=0)
    current_y = Column(Float, default=0)
    current_location_id = Column(Integer, ForeignKey("locations.id"))
    inventory_weight_limit = Column(Float, default=20.0)
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", foreign_keys="Memory.user_id", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="user", cascade="all, delete-orphan")


class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type = Column(Enum(MemoryType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=5)
    game_day = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="memories", foreign_keys=[user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])


class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    image_path = Column(String(500))
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # 关系
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="unique_like"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


class ChatGroup(Base):
    __tablename__ = "chat_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    group_type = Column(Enum(GroupType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    members = relationship("ChatGroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")


class ChatGroupMember(Base):
    __tablename__ = "chat_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="unique_member"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    
    # 关系
    group = relationship("ChatGroup", back_populates="members")
    user = relationship("User")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(Integer, ForeignKey("chat_groups.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    group = relationship("ChatGroup", back_populates="messages")


class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location_type = Column(String(50))
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, default=10)
    height = Column(Float, default=10)
    description = Column(Text)


class GameEvent(Base):
    __tablename__ = "game_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)
    character_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    target_character_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"))
    scheduled_time = Column(Integer, nullable=False)
    duration = Column(Integer, default=0)
    status = Column(Enum(EventStatus, values_callable=lambda x: [e.value for e in x]), default=EventStatus.PENDING)
    data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    character = relationship("User", foreign_keys=[character_id])
    target_character = relationship("User", foreign_keys=[target_character_id])
    location = relationship("Location")


class ImageGenQueue(Base):
    __tablename__ = "image_gen_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    reference_images = Column(JSON)
    status = Column(Enum(ImageGenStatus, values_callable=lambda x: [e.value for e in x]), default=ImageGenStatus.PENDING)
    result_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    character = relationship("User")


class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(100), nullable=False)
    weight = Column(Float, default=0)
    quantity = Column(Integer, default=1)
    properties = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user = relationship("User")


class ActionLogType(str, enum.Enum):
    """行动日志类型"""
    MOVE = "move"               # 移动
    TALK = "talk"               # 对话
    USE_PHONE = "use_phone"     # 使用手机
    POST = "post"               # 发帖
    LIKE = "like"               # 点赞
    COMMENT = "comment"         # 评论
    MESSAGE = "message"         # 私聊
    REST = "rest"               # 休息
    SLEEP = "sleep"             # 睡觉
    WAKE_UP = "wake_up"         # 醒来
    EAT = "eat"                 # 吃东西
    WORK = "work"               # 工作
    THINK = "think"             # 思考/决策
    ENCOUNTER = "encounter"     # 相遇
    OTHER = "other"             # 其他


class ActionLog(Base):
    """
    AI行动日志表
    
    记录AI角色的每一步行动
    """
    __tablename__ = "action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(Enum(ActionLogType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    action_name = Column(String(100), nullable=False)  # 行动名称
    description = Column(Text)                          # 行动描述
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"))
    target_character_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # 行动相关数据
    game_day = Column(Integer)
    game_time = Column(String(10))                     # 游戏时间 HH:MM 格式
    duration = Column(Integer, default=0)              # 消耗时间（分钟）
    
    # AI决策相关
    reason = Column(Text)                              # AI选择这个行动的原因
    result = Column(Text)                              # 行动结果
    success = Column(Boolean, default=True)
    
    # LLM交互记录
    input_prompt = Column(Text)                        # 发送给LLM的完整prompt
    llm_response = Column(Text)                        # LLM返回的原始响应
    
    # 额外数据（JSON格式存储）
    extra_data = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # 关系
    character = relationship("User", foreign_keys=[character_id])
    target_character = relationship("User", foreign_keys=[target_character_id])
    location = relationship("Location")
