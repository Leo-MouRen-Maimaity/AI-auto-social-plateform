"""
社交事件处理器模块

处理各种社交相关的事件：
- USE_PHONE: 看手机（浏览帖子、查看私聊）
- POST_CONTENT: 发帖
- ONLINE_PRIVATE_CHAT: 私聊
- ENCOUNTER: 线下相遇
"""

from typing import Dict, Any, Optional

from ..event_system.events import GameEvent, EventType, EventStatus
from ..event_system.handlers import EventHandler, event_handler, EventHandlerRegistry
from .social_scheduler import SocialScheduler, get_social_scheduler


@event_handler(EventType.USE_PHONE)
class UsePhoneHandler(EventHandler):
    """
    使用手机事件处理器
    
    处理AI角色查看手机的行为：
    - 浏览社交网络帖子
    - 查看/回复私聊消息
    - 可能发帖
    """
    
    async def handle(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        agent = context.get('agent')
        if not agent:
            print(f"UsePhoneHandler: No agent in context for character {event.character_id}")
            return False
        
        scheduler = get_social_scheduler(context.get('db'))
        duration = event.duration or 10
        
        # 执行看手机行为
        results, browsing_summary = await scheduler.use_phone(agent, duration)
        
        # 更新事件数据
        event.data['results'] = [
            {
                'action': r.action_type.value,
                'success': r.success,
                'message': r.message
            }
            for r in results
        ]
        
        # 记录到角色今日事件
        # 非浏览类的消息（私信、发帖等）单独提取
        other_parts = []
        for r in results:
            if r.success and r.message and r.action_type.value not in ('browse_feed', 'like_post', 'comment_post'):
                other_parts.append(r.message)
        
        # 组合：浏览总结 + 其他行为
        all_parts = []
        if browsing_summary:
            all_parts.append(browsing_summary)
        all_parts.extend(other_parts[:2])
        
        if all_parts:
            agent.today_events.append(f"看了会儿手机：{'; '.join(all_parts)}")
        else:
            agent.today_events.append("看了会儿手机")
        
        return True


@event_handler(EventType.POST_CONTENT)
class PostContentHandler(EventHandler):
    """
    发帖事件处理器
    
    处理AI角色主动发帖的行为
    """
    
    async def handle(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        agent = context.get('agent')
        if not agent:
            return False
        
        scheduler = get_social_scheduler(context.get('db'))
        
        # 获取上下文（如果有）
        post_context = event.data.get('context', '')
        
        # 执行发帖
        result = await scheduler.create_post(agent, post_context)
        
        if result and result.success:
            event.data['post_id'] = result.data.get('post_id')
            event.data['content'] = result.data.get('content')
            agent.today_events.append(f"发了一条帖子")
            return True
        
        return False


@event_handler(EventType.ONLINE_PRIVATE_CHAT)
class OnlinePrivateChatHandler(EventHandler):
    """
    网络私聊事件处理器
    
    处理AI角色的私聊对话
    """
    
    async def handle(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        from ..character.agent import AgentManager
        
        agent = context.get('agent')
        if not agent:
            return False
        
        # 获取对话对象
        participant_ids = event.data.get('participant_ids', [])
        if not participant_ids:
            return False
        
        partner_id = participant_ids[0]
        
        scheduler = get_social_scheduler(context.get('db'))
        
        # 检查是回复还是主动发起
        if event.data.get('is_reply', False):
            # 回复模式：检查并回复消息
            results = await scheduler.check_and_reply_messages(agent)
        else:
            # 主动发起模式
            reason = event.data.get('reason', '')
            result = await scheduler.send_proactive_message(agent, partner_id, reason)
            results = [result] if result else []
        
        event.data['results'] = [
            {
                'action': r.action_type.value,
                'success': r.success,
                'message': r.message
            }
            for r in results if r
        ]
        
        return len(results) > 0


@event_handler(EventType.ENCOUNTER)
class EncounterHandler(EventHandler):
    """
    线下相遇事件处理器
    
    处理两个角色在同一地点相遇的情况
    """
    
    async def handle(self, event: GameEvent, context: Dict[str, Any]) -> bool:
        from ..character.agent import AgentManager
        
        agent = context.get('agent')
        if not agent:
            return False
        
        # 获取相遇的另一个角色
        other_id = event.data.get('other_character_id')
        if not other_id:
            return False
        
        # 获取另一个角色的Agent
        manager = AgentManager.get_instance()
        other_agent = manager.get_agent(other_id)
        
        if not other_agent:
            # 另一个角色不是AI，或者没有加载
            return self._handle_encounter_with_npc(agent, other_id, event, context)
        
        # 两个AI角色相遇
        scheduler = get_social_scheduler(context.get('db'))
        location = event.data.get('location_name', '某处')
        
        results = await scheduler.handle_encounter(agent, other_agent, location)
        
        event.data['dialogue'] = [
            {
                'speaker': r.data.get('speaker'),
                'content': r.data.get('content')
            }
            for r in results
        ]
        
        return True
    
    def _handle_encounter_with_npc(self, agent, other_id: int, 
                                    event: GameEvent, 
                                    context: Dict[str, Any]) -> bool:
        """处理与非AI角色（NPC或玩家）的相遇"""
        # 简单处理：不主动发起对话，只是注意到对方
        from .social_client import get_social_client
        
        client = get_social_client(context.get('db'))
        other_user = client.get_user(other_id)
        
        if other_user:
            agent.today_events.append(f"在路上看到了{other_user.nickname}")
        
        return True


class SocialEventHandlers:
    """
    社交事件处理器集合
    
    提供便捷的初始化方法
    """
    
    @staticmethod
    def register_all():
        """
        注册所有社交事件处理器
        
        使用 @event_handler 装饰器已自动注册
        此方法用于确保模块被导入
        """
        registry = EventHandlerRegistry.get_instance()
        
        # 验证处理器已注册
        handlers = [
            EventType.USE_PHONE,
            EventType.POST_CONTENT,
            EventType.ONLINE_PRIVATE_CHAT,
            EventType.ENCOUNTER
        ]
        
        for event_type in handlers:
            if not registry.get_handler(event_type):
                print(f"Warning: Handler for {event_type} not registered")
        
        return True
    
    @staticmethod
    def setup_hooks():
        """设置事件钩子"""
        registry = EventHandlerRegistry.get_instance()
        
        # 相遇事件后的钩子：更新关系记忆
        async def after_encounter(event: GameEvent, context: Dict[str, Any], success: bool):
            if success and event.data.get('dialogue'):
                agent = context.get('agent')
                if agent:
                    other_id = event.data.get('other_character_id')
                    # 可以在这里添加关系记忆更新逻辑
        
        registry.add_after_hook(EventType.ENCOUNTER, after_encounter)
