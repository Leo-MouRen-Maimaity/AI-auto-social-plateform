"""
社交行为API客户端

为AI角色提供直接访问社交功能的能力
使用直接数据库访问而非HTTP请求，更高效
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# 延迟导入以避免循环依赖
_models = None
_database = None


def _get_models():
    global _models
    if _models is None:
        from api_server import models
        _models = models
    return _models


def _get_database():
    global _database
    if _database is None:
        from api_server import database
        _database = database
    return _database


@dataclass
class PostData:
    """帖子数据"""
    id: int
    content: str
    image_path: Optional[str]
    author_id: int
    author_name: str
    author_is_ai: bool
    likes_count: int
    comments_count: int
    created_at: datetime
    
    @classmethod
    def from_db(cls, post, db: Session) -> 'PostData':
        models = _get_models()
        comments_count = db.query(func.count(models.Comment.id)).filter(
            models.Comment.post_id == post.id
        ).scalar()
        
        return cls(
            id=post.id,
            content=post.content,
            image_path=post.image_path,
            author_id=post.author_id,
            author_name=post.author.nickname or post.author.username,
            author_is_ai=post.author.is_ai,
            likes_count=post.likes_count,
            comments_count=comments_count,
            created_at=post.created_at
        )


@dataclass
class CommentData:
    """评论数据"""
    id: int
    post_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime


@dataclass
class MessageData:
    """消息数据"""
    id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    content: str
    is_read: bool
    created_at: datetime


@dataclass
class UserData:
    """用户数据"""
    id: int
    username: str
    nickname: str
    is_ai: bool
    bio: Optional[str] = None


class SocialClient:
    """
    社交行为客户端
    
    为AI角色提供执行社交行为的能力，包括：
    - 发帖/查看帖子
    - 点赞/评论
    - 私聊消息
    """
    
    _instance = None
    
    def __init__(self, db_session: Session = None):
        self._db = db_session
    
    @classmethod
    def get_instance(cls, db_session: Session = None) -> 'SocialClient':
        if cls._instance is None:
            cls._instance = cls(db_session)
        elif db_session:
            cls._instance._db = db_session
        return cls._instance
    
    def set_db(self, db_session: Session):
        """设置数据库会话"""
        self._db = db_session
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self._db:
            return self._db
        database = _get_database()
        return next(database.get_db())
    
    # ===== 帖子相关 =====
    
    def get_latest_posts(self, limit: int = 10, offset: int = 0,
                         exclude_author_id: int = None) -> List[PostData]:
        """
        获取最新帖子
        
        Args:
            limit: 获取数量
            offset: 跳过前N条（分页用）
            exclude_author_id: 排除指定作者的帖子
            
        Returns:
            帖子列表
        """
        models = _get_models()
        db = self._get_db()
        
        query = db.query(models.Post).join(models.User)
        
        if exclude_author_id:
            query = query.filter(models.Post.author_id != exclude_author_id)
        
        posts = query.order_by(desc(models.Post.created_at)).offset(offset).limit(limit).all()
        
        return [PostData.from_db(p, db) for p in posts]
    
    def get_user_posts(self, user_id: int, limit: int = 10, 
                       offset: int = 0) -> List[PostData]:
        """
        获取指定用户的帖子
        
        Args:
            user_id: 用户ID
            limit: 获取数量
            offset: 跳过前N条（分页用）
            
        Returns:
            帖子列表
        """
        models = _get_models()
        db = self._get_db()
        
        posts = db.query(models.Post).join(models.User).filter(
            models.Post.author_id == user_id
        ).order_by(desc(models.Post.created_at)).offset(offset).limit(limit).all()
        
        return [PostData.from_db(p, db) for p in posts]
    
    def get_user_posts_count(self, user_id: int) -> int:
        """获取指定用户的帖子总数"""
        models = _get_models()
        db = self._get_db()
        
        return db.query(func.count(models.Post.id)).filter(
            models.Post.author_id == user_id
        ).scalar() or 0
    
    def get_post(self, post_id: int) -> Optional[PostData]:
        """获取单个帖子"""
        models = _get_models()
        db = self._get_db()
        
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not post:
            return None
        
        return PostData.from_db(post, db)
    
    def create_post(self, author_id: int, content: str, 
                    image_path: str = None) -> Optional[PostData]:
        """
        创建帖子
        
        Args:
            author_id: 作者ID
            content: 帖子内容
            image_path: 图片路径（可选）
            
        Returns:
            创建的帖子数据
        """
        models = _get_models()
        db = self._get_db()
        
        # 验证作者存在
        author = db.query(models.User).filter(models.User.id == author_id).first()
        if not author:
            return None
        
        new_post = models.Post(
            author_id=author_id,
            content=content,
            image_path=image_path
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return PostData.from_db(new_post, db)
    
    def like_post(self, user_id: int, post_id: int) -> bool:
        """
        点赞帖子
        
        Args:
            user_id: 用户ID
            post_id: 帖子ID
            
        Returns:
            是否成功
        """
        models = _get_models()
        db = self._get_db()
        
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not post:
            return False
        
        # 检查是否已点赞
        existing = db.query(models.PostLike).filter(
            models.PostLike.post_id == post_id,
            models.PostLike.user_id == user_id
        ).first()
        
        if existing:
            return True  # 已经点赞过
        
        # 创建点赞
        new_like = models.PostLike(post_id=post_id, user_id=user_id)
        db.add(new_like)
        post.likes_count += 1
        
        db.commit()
        return True
    
    def unlike_post(self, user_id: int, post_id: int) -> bool:
        """取消点赞"""
        models = _get_models()
        db = self._get_db()
        
        existing = db.query(models.PostLike).filter(
            models.PostLike.post_id == post_id,
            models.PostLike.user_id == user_id
        ).first()
        
        if not existing:
            return True
        
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if post:
            post.likes_count = max(0, post.likes_count - 1)
        
        db.delete(existing)
        db.commit()
        return True
    
    # ===== 评论相关 =====
    
    def get_post_comments(self, post_id: int, 
                          limit: int = 20) -> List[CommentData]:
        """获取帖子评论"""
        models = _get_models()
        db = self._get_db()
        
        comments = db.query(models.Comment).join(models.User).filter(
            models.Comment.post_id == post_id
        ).order_by(models.Comment.created_at).limit(limit).all()
        
        return [
            CommentData(
                id=c.id,
                post_id=c.post_id,
                author_id=c.author_id,
                author_name=c.author.nickname or c.author.username,
                content=c.content,
                created_at=c.created_at
            )
            for c in comments
        ]
    
    def get_post_comments_for_user(self, post_id: int, user_id: int,
                                    limit: int = 10) -> List[CommentData]:
        """
        获取帖子评论（为特定用户优化）
        
        返回前limit条评论 + 该用户自己的所有评论（去重）
        
        Args:
            post_id: 帖子ID
            user_id: 当前用户ID（用于获取自己的评论）
            limit: 获取的普通评论数量
            
        Returns:
            评论列表
        """
        models = _get_models()
        db = self._get_db()
        
        # 获取前N条评论
        top_comments = db.query(models.Comment).join(models.User).filter(
            models.Comment.post_id == post_id
        ).order_by(models.Comment.created_at).limit(limit).all()
        
        top_comment_ids = {c.id for c in top_comments}
        
        # 获取用户自己的评论（不在前N条中的）
        my_comments = db.query(models.Comment).join(models.User).filter(
            models.Comment.post_id == post_id,
            models.Comment.author_id == user_id,
            models.Comment.id.notin_(top_comment_ids) if top_comment_ids else True
        ).order_by(models.Comment.created_at).all()
        
        # 合并结果
        all_comments = list(top_comments) + list(my_comments)
        
        return [
            CommentData(
                id=c.id,
                post_id=c.post_id,
                author_id=c.author_id,
                author_name=c.author.nickname or c.author.username,
                content=c.content,
                created_at=c.created_at
            )
            for c in all_comments
        ]
    
    def has_user_commented(self, user_id: int, post_id: int) -> bool:
        """检查用户是否已评论过该帖子"""
        models = _get_models()
        db = self._get_db()
        
        return db.query(models.Comment).filter(
            models.Comment.post_id == post_id,
            models.Comment.author_id == user_id
        ).first() is not None
    
    def create_comment(self, author_id: int, post_id: int, 
                       content: str) -> Optional[CommentData]:
        """
        发表评论
        
        Args:
            author_id: 评论者ID
            post_id: 帖子ID
            content: 评论内容
            
        Returns:
            评论数据
        """
        models = _get_models()
        db = self._get_db()
        
        # 验证帖子存在
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not post:
            return None
        
        # 验证作者存在
        author = db.query(models.User).filter(models.User.id == author_id).first()
        if not author:
            return None
        
        new_comment = models.Comment(
            post_id=post_id,
            author_id=author_id,
            content=content
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return CommentData(
            id=new_comment.id,
            post_id=new_comment.post_id,
            author_id=new_comment.author_id,
            author_name=author.nickname or author.username,
            content=new_comment.content,
            created_at=new_comment.created_at
        )
    
    # ===== 私聊相关 =====
    
    def get_unread_messages(self, user_id: int) -> List[MessageData]:
        """获取未读消息"""
        models = _get_models()
        db = self._get_db()
        
        messages = db.query(models.Message).join(
            models.User, models.Message.sender_id == models.User.id
        ).filter(
            models.Message.receiver_id == user_id,
            models.Message.is_read == False,
            models.Message.group_id.is_(None)
        ).order_by(models.Message.created_at).all()
        
        return [
            MessageData(
                id=m.id,
                sender_id=m.sender_id,
                sender_name=m.sender.nickname or m.sender.username if m.sender else "未知",
                receiver_id=m.receiver_id,
                content=m.content,
                is_read=m.is_read,
                created_at=m.created_at
            )
            for m in messages
        ]
    
    def get_chat_history(self, user_id: int, partner_id: int, 
                         limit: int = 20) -> List[MessageData]:
        """获取与指定用户的聊天历史"""
        models = _get_models()
        db = self._get_db()
        
        from sqlalchemy import or_, and_
        
        messages = db.query(models.Message).filter(
            or_(
                and_(models.Message.sender_id == user_id, 
                     models.Message.receiver_id == partner_id),
                and_(models.Message.sender_id == partner_id, 
                     models.Message.receiver_id == user_id)
            ),
            models.Message.group_id.is_(None)
        ).order_by(desc(models.Message.created_at)).limit(limit).all()
        
        # 反转顺序（最旧的在前）
        messages.reverse()
        
        result = []
        for m in messages:
            sender = db.query(models.User).filter(models.User.id == m.sender_id).first()
            result.append(MessageData(
                id=m.id,
                sender_id=m.sender_id,
                sender_name=sender.nickname or sender.username if sender else "未知",
                receiver_id=m.receiver_id,
                content=m.content,
                is_read=m.is_read,
                created_at=m.created_at
            ))
        
        return result
    
    def send_message(self, sender_id: int, receiver_id: int, 
                     content: str) -> Optional[MessageData]:
        """
        发送私聊消息
        
        Args:
            sender_id: 发送者ID
            receiver_id: 接收者ID
            content: 消息内容
            
        Returns:
            消息数据
        """
        models = _get_models()
        db = self._get_db()
        
        # 验证用户存在
        sender = db.query(models.User).filter(models.User.id == sender_id).first()
        receiver = db.query(models.User).filter(models.User.id == receiver_id).first()
        
        if not sender or not receiver:
            return None
        
        if sender_id == receiver_id:
            return None
        
        new_message = models.Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        return MessageData(
            id=new_message.id,
            sender_id=new_message.sender_id,
            sender_name=sender.nickname or sender.username,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            is_read=new_message.is_read,
            created_at=new_message.created_at
        )
    
    def mark_messages_read(self, user_id: int, sender_id: int):
        """标记来自指定用户的消息为已读"""
        models = _get_models()
        db = self._get_db()
        
        db.query(models.Message).filter(
            models.Message.sender_id == sender_id,
            models.Message.receiver_id == user_id,
            models.Message.is_read == False
        ).update({"is_read": True})
        
        db.commit()
    
    # ===== 用户相关 =====
    
    def get_user(self, user_id: int) -> Optional[UserData]:
        """获取用户信息"""
        models = _get_models()
        db = self._get_db()
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
        
        return UserData(
            id=user.id,
            username=user.username,
            nickname=user.nickname or user.username,
            is_ai=user.is_ai,
            bio=user.bio
        )
    
    def get_all_users(self, exclude_id: int = None, 
                      ai_only: bool = False) -> List[UserData]:
        """获取所有用户"""
        models = _get_models()
        db = self._get_db()
        
        query = db.query(models.User)
        
        if exclude_id:
            query = query.filter(models.User.id != exclude_id)
        
        if ai_only:
            query = query.filter(models.User.is_ai == True)
        
        users = query.all()
        
        return [
            UserData(
                id=u.id,
                username=u.username,
                nickname=u.nickname or u.username,
                is_ai=u.is_ai,
                bio=u.bio
            )
            for u in users
        ]
    
    def get_ai_characters(self) -> List[UserData]:
        """获取所有AI角色"""
        return self.get_all_users(ai_only=True)


# 全局实例获取
def get_social_client(db_session: Session = None) -> SocialClient:
    """获取社交客户端实例"""
    return SocialClient.get_instance(db_session)
