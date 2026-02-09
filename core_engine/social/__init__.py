"""
社交功能增强模块

包含AI角色的社交行为能力：
- 自动发帖
- 浏览/点赞/评论
- 私聊
- 线下相遇
"""

from .social_client import SocialClient, get_social_client
from .social_scheduler import SocialScheduler, get_social_scheduler
from .social_handlers import SocialEventHandlers

__all__ = [
    'SocialClient',
    'get_social_client',
    'SocialScheduler',
    'get_social_scheduler',
    'SocialEventHandlers'
]
