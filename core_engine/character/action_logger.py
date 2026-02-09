"""
行动日志模块

记录AI角色的每一步行动，支持查询和可视化
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """行动类型"""
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


@dataclass
class ActionLogEntry:
    """行动日志条目"""
    id: int = 0
    character_id: int = 0
    action_type: ActionType = ActionType.OTHER
    action_name: str = ""
    description: str = ""
    location_id: Optional[int] = None
    target_character_id: Optional[int] = None
    game_day: int = 0
    game_time: str = ""
    duration: int = 0
    reason: str = ""
    result: str = ""
    success: bool = True
    input_prompt: str = ""           # 发送给LLM的完整prompt
    llm_response: str = ""           # LLM返回的原始响应
    extra_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = None
    
    # 额外信息（不存数据库，用于显示）
    character_name: str = ""
    target_character_name: str = ""
    location_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'character_id': self.character_id,
            'character_name': self.character_name,
            'action_type': self.action_type.value,
            'action_name': self.action_name,
            'description': self.description,
            'location_id': self.location_id,
            'location_name': self.location_name,
            'target_character_id': self.target_character_id,
            'target_character_name': self.target_character_name,
            'game_day': self.game_day,
            'game_time': self.game_time,
            'duration': self.duration,
            'reason': self.reason,
            'result': self.result,
            'success': self.success,
            'input_prompt': self.input_prompt,
            'llm_response': self.llm_response,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_display_text(self) -> str:
        """获取用于显示的文本"""
        time_str = f"[{self.game_time}]" if self.game_time else ""
        return f"{time_str} {self.action_name}: {self.description or self.result or ''}"


class ActionLogger:
    """
    行动日志记录器
    
    负责记录和查询AI角色的行动历史
    """
    
    def __init__(self, db_session=None):
        self._db = db_session
    
    def set_db_session(self, db_session):
        """设置数据库会话"""
        self._db = db_session
    
    def log_action(
        self,
        character_id: int,
        action_type: ActionType,
        action_name: str,
        description: str = "",
        location_id: Optional[int] = None,
        target_character_id: Optional[int] = None,
        game_day: int = 0,
        game_time: str = "",
        duration: int = 0,
        reason: str = "",
        result: str = "",
        success: bool = True,
        input_prompt: str = "",
        llm_response: str = "",
        extra_data: Dict[str, Any] = None
    ) -> Optional[int]:
        """
        记录一条行动日志
        
        Returns:
            日志ID，如果失败返回None
        """
        if not self._db:
            print(f"[ActionLog] (no db) {character_id}: {action_name} - {description}")
            return None
        
        try:
            from api_server import models
            
            log = models.ActionLog(
                character_id=character_id,
                action_type=action_type.value,  # 直接使用字符串值
                action_name=action_name,
                description=description,
                location_id=location_id,
                target_character_id=target_character_id,
                game_day=game_day,
                game_time=game_time,
                duration=duration,
                reason=reason,
                result=result,
                success=success,
                input_prompt=input_prompt,
                llm_response=llm_response,
                extra_data=extra_data or {}
            )
            
            self._db.add(log)
            self._db.commit()
            
            return log.id
            
        except Exception as e:
            print(f"ActionLogger error: {e}")
            self._db.rollback()
            return None
    
    def log_move(self, character_id: int, from_location: str, to_location: str,
                 location_id: int = None, game_day: int = 0, game_time: str = "",
                 duration: int = 0, reason: str = "") -> Optional[int]:
        """记录移动行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.MOVE,
            action_name="移动",
            description=f"从{from_location}前往{to_location}",
            location_id=location_id,
            game_day=game_day,
            game_time=game_time,
            duration=duration,
            reason=reason,
            result=f"到达了{to_location}"
        )
    
    def log_talk(self, character_id: int, target_id: int, target_name: str,
                 summary: str = "", game_day: int = 0, game_time: str = "",
                 duration: int = 0, location_id: int = None) -> Optional[int]:
        """记录对话行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.TALK,
            action_name="对话",
            description=f"与{target_name}交谈",
            target_character_id=target_id,
            location_id=location_id,
            game_day=game_day,
            game_time=game_time,
            duration=duration,
            result=summary
        )
    
    def log_use_phone(self, character_id: int, activity: str = "",
                      game_day: int = 0, game_time: str = "",
                      duration: int = 0, location_id: int = None) -> Optional[int]:
        """记录使用手机行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.USE_PHONE,
            action_name="使用手机",
            description=activity or "查看手机",
            location_id=location_id,
            game_day=game_day,
            game_time=game_time,
            duration=duration
        )
    
    def log_post(self, character_id: int, post_content: str,
                 post_id: int = None, game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录发帖行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.POST,
            action_name="发帖",
            description=post_content[:100] + ("..." if len(post_content) > 100 else ""),
            game_day=game_day,
            game_time=game_time,
            duration=5,
            extra_data={'post_id': post_id} if post_id else None
        )
    
    def log_like(self, character_id: int, post_author: str, post_id: int = None,
                 game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录点赞行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.LIKE,
            action_name="点赞",
            description=f"给{post_author}的帖子点赞",
            game_day=game_day,
            game_time=game_time,
            duration=1,
            extra_data={'post_id': post_id} if post_id else None
        )
    
    def log_comment(self, character_id: int, post_author: str, comment_content: str,
                    post_id: int = None, game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录评论行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.COMMENT,
            action_name="评论",
            description=f"评论了{post_author}的帖子: {comment_content[:50]}",
            game_day=game_day,
            game_time=game_time,
            duration=3,
            extra_data={'post_id': post_id} if post_id else None
        )
    
    def log_message(self, character_id: int, target_id: int, target_name: str,
                    message_preview: str = "", game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录私聊行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.MESSAGE,
            action_name="发送私信",
            description=f"给{target_name}发送私信",
            target_character_id=target_id,
            game_day=game_day,
            game_time=game_time,
            duration=2,
            result=message_preview[:50] if message_preview else ""
        )
    
    def log_rest(self, character_id: int, location_id: int = None,
                 game_day: int = 0, game_time: str = "", duration: int = 15) -> Optional[int]:
        """记录休息行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.REST,
            action_name="休息",
            description="休息了一会儿",
            location_id=location_id,
            game_day=game_day,
            game_time=game_time,
            duration=duration
        )
    
    def log_sleep(self, character_id: int, game_day: int, summary: str = "") -> Optional[int]:
        """记录睡觉行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.SLEEP,
            action_name="入睡",
            description="准备睡觉",
            game_day=game_day,
            game_time="22:00",
            result=summary
        )
    
    def log_wake_up(self, character_id: int, game_day: int, game_time: str = "08:00",
                    plan_summary: str = "") -> Optional[int]:
        """记录醒来行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.WAKE_UP,
            action_name="醒来",
            description=f"第{game_day}天开始",
            game_day=game_day,
            game_time=game_time,
            result=plan_summary[:200] if plan_summary else ""
        )
    
    def log_think(self, character_id: int, decision: str, reason: str = "",
                  game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录思考/决策行动"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.THINK,
            action_name="思考",
            description=decision,
            game_day=game_day,
            game_time=game_time,
            reason=reason,
            duration=1
        )
    
    def log_encounter(self, character_id: int, target_id: int, target_name: str,
                      location_id: int = None, location_name: str = "",
                      game_day: int = 0, game_time: str = "") -> Optional[int]:
        """记录相遇事件"""
        return self.log_action(
            character_id=character_id,
            action_type=ActionType.ENCOUNTER,
            action_name="相遇",
            description=f"在{location_name}遇到了{target_name}" if location_name else f"遇到了{target_name}",
            target_character_id=target_id,
            location_id=location_id,
            game_day=game_day,
            game_time=game_time
        )
    
    def get_recent_logs(self, character_id: int = None, limit: int = 20,
                        action_type: ActionType = None) -> List[ActionLogEntry]:
        """
        获取最近的行动日志
        
        Args:
            character_id: 角色ID，为None则获取所有角色
            limit: 返回数量限制
            action_type: 筛选特定类型的行动
            
        Returns:
            行动日志列表
        """
        if not self._db:
            return []
        
        try:
            from api_server import models
            
            query = self._db.query(models.ActionLog)
            
            if character_id is not None:
                query = query.filter(models.ActionLog.character_id == character_id)
            
            if action_type is not None:
                query = query.filter(models.ActionLog.action_type == models.ActionLogType(action_type.value))
            
            query = query.order_by(models.ActionLog.created_at.desc()).limit(limit)
            
            logs = query.all()
            
            # 转换为 ActionLogEntry
            entries = []
            for log in logs:
                entry = ActionLogEntry(
                    id=log.id,
                    character_id=log.character_id,
                    action_type=ActionType(log.action_type.value),
                    action_name=log.action_name,
                    description=log.description or "",
                    location_id=log.location_id,
                    target_character_id=log.target_character_id,
                    game_day=log.game_day or 0,
                    game_time=log.game_time or "",
                    duration=log.duration or 0,
                    reason=log.reason or "",
                    result=log.result or "",
                    success=log.success,
                    input_prompt=log.input_prompt or "",
                    llm_response=log.llm_response or "",
                    extra_data=log.extra_data or {},
                    created_at=log.created_at
                )
                
                # 获取角色名称
                if log.character:
                    entry.character_name = log.character.nickname or log.character.username
                if log.target_character:
                    entry.target_character_name = log.target_character.nickname or log.target_character.username
                if log.location:
                    entry.location_name = log.location.name
                
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            print(f"Get logs error: {e}")
            return []
    
    def get_character_logs(self, character_id: int, game_day: int = None,
                           limit: int = 50) -> List[ActionLogEntry]:
        """
        获取指定角色的行动日志
        
        Args:
            character_id: 角色ID
            game_day: 游戏日，为None则获取所有
            limit: 返回数量限制
        """
        if not self._db:
            return []
        
        try:
            from api_server import models
            
            query = self._db.query(models.ActionLog).filter(
                models.ActionLog.character_id == character_id
            )
            
            if game_day is not None:
                query = query.filter(models.ActionLog.game_day == game_day)
            
            query = query.order_by(models.ActionLog.created_at.desc()).limit(limit)
            
            logs = query.all()
            
            entries = []
            for log in logs:
                entry = ActionLogEntry(
                    id=log.id,
                    character_id=log.character_id,
                    action_type=ActionType(log.action_type.value),
                    action_name=log.action_name,
                    description=log.description or "",
                    location_id=log.location_id,
                    target_character_id=log.target_character_id,
                    game_day=log.game_day or 0,
                    game_time=log.game_time or "",
                    duration=log.duration or 0,
                    reason=log.reason or "",
                    result=log.result or "",
                    success=log.success,
                    input_prompt=log.input_prompt or "",
                    llm_response=log.llm_response or "",
                    extra_data=log.extra_data or {},
                    created_at=log.created_at
                )
                
                if log.target_character:
                    entry.target_character_name = log.target_character.nickname or log.target_character.username
                if log.location:
                    entry.location_name = log.location.name
                
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            print(f"Get character logs error: {e}")
            return []


# 全局实例
_action_logger: Optional[ActionLogger] = None


def get_action_logger(db_session=None) -> ActionLogger:
    """获取全局ActionLogger实例"""
    global _action_logger
    if _action_logger is None:
        _action_logger = ActionLogger(db_session)
    elif db_session:
        _action_logger.set_db_session(db_session)
    return _action_logger
