"""
社交行为调度器

协调AI角色的社交行为：
- 定时浏览社交网络
- 自动发帖
- 回复私聊
- 处理线下相遇
"""

import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum

from .social_client import SocialClient, PostData, MessageData, get_social_client

if TYPE_CHECKING:
    from ..character.agent import CharacterAgent


class SocialActionType(str, Enum):
    """社交行为类型"""
    BROWSE_FEED = "browse_feed"         # 浏览动态
    CREATE_POST = "create_post"          # 发帖
    LIKE_POST = "like_post"              # 点赞
    COMMENT_POST = "comment_post"        # 评论
    CHECK_MESSAGES = "check_messages"    # 查看私信
    REPLY_MESSAGE = "reply_message"      # 回复私信
    SEND_MESSAGE = "send_message"        # 主动发私信
    VIEW_USER_PROFILE = "view_user_profile"  # 查看用户主页
    ENCOUNTER = "encounter"              # 线下相遇


@dataclass
class SocialActionResult:
    """社交行为结果"""
    action_type: SocialActionType
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    duration: int = 2  # 消耗的游戏时间（分钟）


class SocialScheduler:
    """
    社交行为调度器
    
    管理AI角色的社交行为，包括：
    - 浏览帖子并决定是否点赞/评论
    - 查看并回复私聊消息
    - 自动发帖
    - 处理线下相遇对话
    """
    
    def __init__(self, db_session=None):
        self._social_client = get_social_client(db_session)
        self._db = db_session
    
    def set_db(self, db_session):
        """设置数据库会话"""
        self._db = db_session
        self._social_client.set_db(db_session)
    
    # ===== 看手机行为 =====
    
    async def use_phone(self, agent: 'CharacterAgent', 
                        duration_minutes: int = 10) -> List[SocialActionResult]:
        """
        使用手机（综合社交行为）
        
        模拟角色查看手机的行为，在指定时间内：
        - 浏览帖子（每条约2分钟）
        - 查看私聊消息并可能回复
        
        Args:
            agent: AI角色Agent
            duration_minutes: 使用手机的时间（分钟）
            
        Returns:
            执行的社交行为结果列表
        """
        results = []
        remaining_time = duration_minutes
        
        # 1. 先检查未读消息
        if remaining_time >= 2:
            msg_results = await self.check_and_reply_messages(agent)
            results.extend(msg_results)
            remaining_time -= sum(r.duration for r in msg_results)
        
        # 2. 浏览帖子
        if remaining_time >= 2:
            posts_to_view = remaining_time // 2  # 每条帖子约2分钟
            feed_results = await self.browse_feed(agent, max_posts=min(5, posts_to_view))
            results.extend(feed_results)
            remaining_time -= sum(r.duration for r in feed_results)
        
        # 3. 可能发帖（10%概率）
        if remaining_time >= 3 and random.random() < 0.1:
            post_result = await self.create_post(agent)
            if post_result:
                results.append(post_result)
        
        return results
    
    async def browse_feed(self, agent: 'CharacterAgent', 
                          max_posts: int = 5) -> List[SocialActionResult]:
        """
        浏览社交网络动态
        
        Args:
            agent: AI角色Agent
            max_posts: 最多浏览帖子数
            
        Returns:
            浏览结果列表（包含点赞/评论行为）
        """
        from shared.config import get_settings
        settings = get_settings()
        
        results = []
        
        # 获取最新帖子
        posts = self._social_client.get_latest_posts(
            limit=max_posts * 2,  # 获取更多，随机选择
            exclude_author_id=agent.character_id
        )
        
        if not posts:
            results.append(SocialActionResult(
                action_type=SocialActionType.BROWSE_FEED,
                success=True,
                message="社交网络没有新帖子",
                duration=1
            ))
            return results
        
        # 随机选择要看的帖子
        posts_to_view = random.sample(posts, min(max_posts, len(posts)))
        
        # 转换为agent可用的格式，包含评论
        posts_for_agent = []
        for p in posts_to_view:
            # 获取评论（前N条 + 自己的评论）
            comments = self._social_client.get_post_comments_for_user(
                p.id, 
                agent.character_id,
                limit=settings.ai_browse_comments_limit
            )
            
            # 检查自己是否已评论
            has_commented = any(c.author_id == agent.character_id for c in comments)
            
            posts_for_agent.append({
                'id': p.id,
                'content': p.content,
                'author_name': p.author_name,
                'likes_count': p.likes_count,
                'comments': [
                    {
                        'author_name': c.author_name,
                        'content': c.content,
                        'is_mine': c.author_id == agent.character_id
                    }
                    for c in comments
                ],
                'has_commented': has_commented
            })
        
        # 让Agent决定对每个帖子的反应
        reactions = await agent.browse_feed(posts_for_agent)
        
        for post, reaction in zip(posts_to_view, reactions):
            # 执行点赞
            if reaction.get('like', False):
                success = self._social_client.like_post(
                    agent.character_id, 
                    post.id
                )
                if success:
                    results.append(SocialActionResult(
                        action_type=SocialActionType.LIKE_POST,
                        success=True,
                        message=f"给{post.author_name}的帖子点赞",
                        data={'post_id': post.id},
                        duration=0
                    ))
            
            # 执行评论
            comment_text = reaction.get('comment', '')
            if comment_text:
                comment = self._social_client.create_comment(
                    agent.character_id,
                    post.id,
                    comment_text
                )
                if comment:
                    results.append(SocialActionResult(
                        action_type=SocialActionType.COMMENT_POST,
                        success=True,
                        message=f"评论了{post.author_name}的帖子：{comment_text[:20]}...",
                        data={'post_id': post.id, 'comment_id': comment.id},
                        duration=1
                    ))
            
            # 基础浏览时间
            results.append(SocialActionResult(
                action_type=SocialActionType.BROWSE_FEED,
                success=True,
                message=f"看了{post.author_name}的帖子",
                data={'post_id': post.id},
                duration=2
            ))
        
        return results
    
    async def create_post(self, agent: 'CharacterAgent', 
                          context: str = "") -> Optional[SocialActionResult]:
        """
        创建帖子
        
        Args:
            agent: AI角色Agent
            context: 发帖上下文
            
        Returns:
            发帖结果
        """
        # 让Agent生成帖子内容
        post_data = await agent.create_post(context)
        
        if not post_data or not post_data.get('content'):
            return SocialActionResult(
                action_type=SocialActionType.CREATE_POST,
                success=False,
                message="没有想到要发什么",
                duration=1
            )
        
        # 创建帖子
        new_post = self._social_client.create_post(
            author_id=agent.character_id,
            content=post_data['content'],
            image_path=post_data.get('image_path')
        )
        
        if new_post:
            return SocialActionResult(
                action_type=SocialActionType.CREATE_POST,
                success=True,
                message=f"发了一条帖子：{post_data['content'][:30]}...",
                data={'post_id': new_post.id, 'content': post_data['content']},
                duration=3
            )
        
        return SocialActionResult(
            action_type=SocialActionType.CREATE_POST,
            success=False,
            message="发帖失败",
            duration=1
        )
    
    async def view_user_profile(self, agent: 'CharacterAgent',
                                 target_id: int,
                                 max_posts: int = 5) -> List[SocialActionResult]:
        """
        查看指定用户的主页/帖子
        
        Args:
            agent: AI角色Agent
            target_id: 目标用户ID
            max_posts: 最多浏览帖子数
            
        Returns:
            浏览结果列表（包含点赞/评论行为）
        """
        results = []
        
        # 获取目标用户信息
        target = self._social_client.get_user(target_id)
        if not target:
            return [SocialActionResult(
                action_type=SocialActionType.VIEW_USER_PROFILE,
                success=False,
                message="找不到该用户",
                duration=1
            )]
        
        # 获取该用户的帖子
        posts = self._social_client.get_user_posts(
            user_id=target_id,
            limit=max_posts
        )
        
        if not posts:
            results.append(SocialActionResult(
                action_type=SocialActionType.VIEW_USER_PROFILE,
                success=True,
                message=f"查看了{target.nickname}的主页，但TA还没有发过帖子",
                data={'target_id': target_id, 'target_name': target.nickname},
                duration=2
            ))
            return results
        
        from shared.config import get_settings
        settings = get_settings()
        
        # 转换为agent可用的格式，包含评论
        posts_for_agent = []
        for p in posts:
            # 获取评论（前N条 + 自己的评论）
            comments = self._social_client.get_post_comments_for_user(
                p.id, 
                agent.character_id,
                limit=settings.ai_browse_comments_limit
            )
            
            # 检查自己是否已评论
            has_commented = any(c.author_id == agent.character_id for c in comments)
            
            posts_for_agent.append({
                'id': p.id,
                'content': p.content,
                'author_name': p.author_name,
                'likes_count': p.likes_count,
                'comments': [
                    {
                        'author_name': c.author_name,
                        'content': c.content,
                        'is_mine': c.author_id == agent.character_id
                    }
                    for c in comments
                ],
                'has_commented': has_commented
            })
        
        # 让Agent决定对每个帖子的反应
        reactions = await agent.browse_feed(posts_for_agent)
        
        for post, reaction in zip(posts, reactions):
            # 执行点赞
            if reaction.get('like', False):
                success = self._social_client.like_post(
                    agent.character_id, 
                    post.id
                )
                if success:
                    results.append(SocialActionResult(
                        action_type=SocialActionType.LIKE_POST,
                        success=True,
                        message=f"给{post.author_name}的帖子点赞",
                        data={'post_id': post.id},
                        duration=0
                    ))
            
            # 执行评论
            comment_text = reaction.get('comment', '')
            if comment_text:
                comment = self._social_client.create_comment(
                    agent.character_id,
                    post.id,
                    comment_text
                )
                if comment:
                    results.append(SocialActionResult(
                        action_type=SocialActionType.COMMENT_POST,
                        success=True,
                        message=f"评论了{post.author_name}的帖子：{comment_text[:20]}...",
                        data={'post_id': post.id, 'comment_id': comment.id},
                        duration=1
                    ))
        
        # 记录查看主页行为
        results.append(SocialActionResult(
            action_type=SocialActionType.VIEW_USER_PROFILE,
            success=True,
            message=f"查看了{target.nickname}的主页，浏览了{len(posts)}条帖子",
            data={
                'target_id': target_id, 
                'target_name': target.nickname,
                'posts_viewed': len(posts)
            },
            duration=max(2, len(posts))  # 每条帖子约1分钟
        ))
        
        return results
    
    # ===== 私聊行为 =====
    
    async def check_and_reply_messages(self, 
                                        agent: 'CharacterAgent') -> List[SocialActionResult]:
        """
        检查并回复私聊消息
        
        Args:
            agent: AI角色Agent
            
        Returns:
            处理结果列表
        """
        results = []
        
        # 获取未读消息
        unread = self._social_client.get_unread_messages(agent.character_id)
        
        if not unread:
            results.append(SocialActionResult(
                action_type=SocialActionType.CHECK_MESSAGES,
                success=True,
                message="没有未读消息",
                duration=1
            ))
            return results
        
        # 按发送者分组
        by_sender: Dict[int, List[MessageData]] = {}
        for msg in unread:
            if msg.sender_id not in by_sender:
                by_sender[msg.sender_id] = []
            by_sender[msg.sender_id].append(msg)
        
        # 处理每个发送者的消息
        for sender_id, messages in by_sender.items():
            sender_name = messages[0].sender_name
            
            # 获取最近的聊天历史
            history = self._social_client.get_chat_history(
                agent.character_id, 
                sender_id, 
                limit=10
            )
            
            # 构建对话上下文
            last_message = messages[-1]
            
            # 让Agent决定是否回复
            reply = await self._generate_reply(agent, sender_id, sender_name, history)
            
            if reply:
                # 发送回复
                sent = self._social_client.send_message(
                    agent.character_id,
                    sender_id,
                    reply
                )
                
                if sent:
                    results.append(SocialActionResult(
                        action_type=SocialActionType.REPLY_MESSAGE,
                        success=True,
                        message=f"回复了{sender_name}：{reply[:20]}...",
                        data={
                            'partner_id': sender_id,
                            'partner_name': sender_name,
                            'reply': reply
                        },
                        duration=2
                    ))
            else:
                results.append(SocialActionResult(
                    action_type=SocialActionType.CHECK_MESSAGES,
                    success=True,
                    message=f"看了{sender_name}的消息但没有回复",
                    data={'partner_id': sender_id},
                    duration=1
                ))
            
            # 标记为已读
            self._social_client.mark_messages_read(agent.character_id, sender_id)
        
        return results
    
    async def _generate_reply(self, agent: 'CharacterAgent',
                               partner_id: int, partner_name: str,
                               history: List[MessageData]) -> Optional[str]:
        """
        生成私聊回复
        
        Args:
            agent: AI角色Agent
            partner_id: 对方ID
            partner_name: 对方名称
            history: 聊天历史
            
        Returns:
            回复内容，如果不想回复则返回None
        """
        if not history:
            return None
        
        # 构建对话历史文本
        history_text = "\n".join([
            f"{'我' if m.sender_id == agent.character_id else partner_name}：{m.content}"
            for m in history[-5:]  # 最近5条
        ])
        
        # 获取关系记忆
        relationship = agent.memory.get_relationship_text(partner_id, partner_name)
        
        # 让LLM决定回复
        prompt = f"""
你正在查看与{partner_name}的私聊消息。
{f'你对{partner_name}的印象：{relationship}' if relationship else ''}

最近的聊天记录：
{history_text}

请决定是否要回复。如果要回复，请写出回复内容。如果不想回复（比如觉得对话已经结束，或者不知道说什么），可以选择不回复。

用JSON格式回复：
{{"reply": true/false, "content": "回复内容（如果reply为false则留空）"}}
"""
        
        response = await agent._llm.generate_json(
            agent._build_system_prompt(),
            prompt,
            temperature=0.7
        )
        
        if response and response.get('reply') and response.get('content'):
            return response['content']
        
        return None
    
    async def send_proactive_message(self, agent: 'CharacterAgent',
                                      target_id: int, 
                                      reason: str = "") -> Optional[SocialActionResult]:
        """
        主动发送私聊消息
        
        Args:
            agent: AI角色Agent
            target_id: 目标用户ID
            reason: 发消息的原因/上下文
            
        Returns:
            发送结果
        """
        target = self._social_client.get_user(target_id)
        if not target:
            return None
        
        # 获取聊天历史
        history = self._social_client.get_chat_history(
            agent.character_id,
            target_id,
            limit=10
        )
        
        # 让Agent生成消息
        prompt = f"""
你想给{target.nickname}发一条私信。
{reason if reason else ''}

{'之前的聊天记录：' + chr(10).join([f"{'我' if m.sender_id == agent.character_id else target.nickname}：{m.content}" for m in history[-3:]]) if history else '你们之前没有聊过天。'}

请写出要发送的消息内容。要符合你的性格特点，自然真实。

用JSON格式回复：
{{"content": "消息内容"}}
"""
        
        response = await agent._llm.generate_json(
            agent._build_system_prompt(),
            prompt,
            temperature=0.8
        )
        
        if not response or not response.get('content'):
            return None
        
        # 发送消息
        sent = self._social_client.send_message(
            agent.character_id,
            target_id,
            response['content']
        )
        
        if sent:
            return SocialActionResult(
                action_type=SocialActionType.SEND_MESSAGE,
                success=True,
                message=f"给{target.nickname}发了私信",
                data={
                    'partner_id': target_id,
                    'partner_name': target.nickname,
                    'content': response['content']
                },
                duration=2
            )
        
        return None
    
    # ===== 线下相遇 =====
    
    async def handle_encounter(self, agent1: 'CharacterAgent', 
                                agent2: 'CharacterAgent',
                                location: str = "") -> List[SocialActionResult]:
        """
        处理两个AI角色的线下相遇
        
        Args:
            agent1: 角色1
            agent2: 角色2
            location: 相遇地点
            
        Returns:
            相遇对话结果
        """
        results = []
        
        # 角色1发起对话
        context = f"你在{location}遇到了{agent2.profile.name}。" if location else f"你遇到了{agent2.profile.name}。"
        
        greeting = await agent1.start_conversation(
            agent2.character_id,
            agent2.profile.name,
            context
        )
        
        results.append(SocialActionResult(
            action_type=SocialActionType.ENCOUNTER,
            success=True,
            message=f"{agent1.profile.name}向{agent2.profile.name}打招呼",
            data={
                'speaker': agent1.character_id,
                'content': greeting
            },
            duration=1
        ))
        
        # 角色2回应
        response = await agent2.respond_in_conversation(
            greeting,
            agent1.profile.name
        )
        
        results.append(SocialActionResult(
            action_type=SocialActionType.ENCOUNTER,
            success=True,
            message=f"{agent2.profile.name}回应",
            data={
                'speaker': agent2.character_id,
                'content': response
            },
            duration=1
        ))
        
        # 继续几轮对话
        max_turns = random.randint(2, 5)
        current_speaker = agent1
        other_speaker = agent2
        last_message = response
        
        for _ in range(max_turns):
            reply = await current_speaker.respond_in_conversation(
                last_message,
                other_speaker.profile.name
            )
            
            results.append(SocialActionResult(
                action_type=SocialActionType.ENCOUNTER,
                success=True,
                message=f"{current_speaker.profile.name}说话",
                data={
                    'speaker': current_speaker.character_id,
                    'content': reply
                },
                duration=1
            ))
            
            last_message = reply
            current_speaker, other_speaker = other_speaker, current_speaker
        
        # 结束对话
        await agent1.end_conversation(agent2.character_id, agent2.profile.name)
        await agent2.end_conversation(agent1.character_id, agent1.profile.name)
        
        return results
    
    async def check_for_encounters(self, 
                                    agents: List['CharacterAgent'],
                                    location_id: int) -> List[tuple]:
        """
        检查同一地点的角色是否相遇
        
        Args:
            agents: 在同一地点的角色列表
            location_id: 地点ID
            
        Returns:
            可能发生相遇的角色对列表
        """
        if len(agents) < 2:
            return []
        
        encounters = []
        checked = set()
        
        for i, agent1 in enumerate(agents):
            for agent2 in agents[i+1:]:
                pair_key = tuple(sorted([agent1.character_id, agent2.character_id]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)
                
                # 30%的概率发生相遇对话
                if random.random() < 0.3:
                    encounters.append((agent1, agent2))
        
        return encounters


# 全局实例
_scheduler_instance = None


def get_social_scheduler(db_session=None) -> SocialScheduler:
    """获取社交调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SocialScheduler(db_session)
    elif db_session:
        _scheduler_instance.set_db(db_session)
    return _scheduler_instance
