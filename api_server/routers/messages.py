"""私聊消息路由"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from typing import List, Dict, Optional
import json
from datetime import datetime

from ..database import get_db
from ..models import Message, User
from ..schemas import MessageCreate, MessageResponse, UserBrief, SuccessResponse
from ..auth import get_current_user, decode_token

router = APIRouter(prefix="/messages", tags=["messages"])


# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        # user_id -> list of websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """发送消息给指定用户的所有连接"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)


manager = ConnectionManager()


# 会话信息响应模型
class ConversationResponse:
    pass


def user_to_brief(user: User) -> dict:
    """将User转换为简要信息字典"""
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_path": user.avatar_path,
        "is_ai": user.is_ai
    }


def message_to_response(msg: Message, sender: User) -> dict:
    """将Message转换为响应字典"""
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "group_id": msg.group_id,
        "content": msg.content,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat(),
        "sender": user_to_brief(sender)
    }


@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的所有私聊会话列表"""
    try:
        user_id = current_user.id
        
        # 获取所有与当前用户相关的私聊消息
        all_messages = db.query(Message).filter(
            or_(Message.sender_id == user_id, Message.receiver_id == user_id),
            Message.group_id.is_(None)
        ).order_by(desc(Message.created_at)).all()
        
        # 按对话方分组，找出每个对话的最后一条消息
        conversation_map = {}
        for msg in all_messages:
            other_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
            if other_id not in conversation_map:
                conversation_map[other_id] = msg
        
        # 构建响应
        conversations = []
        for other_user_id, last_message in conversation_map.items():
            # 获取对方用户信息
            other_user = db.query(User).filter(User.id == other_user_id).first()
            if not other_user:
                continue
            
            # 统计未读消息数
            unread_count = db.query(func.count(Message.id)).filter(
                Message.sender_id == other_user_id,
                Message.receiver_id == user_id,
                Message.is_read == False
            ).scalar()
            
            conversations.append({
                "user": user_to_brief(other_user),
                "last_message": {
                    "id": last_message.id,
                    "content": last_message.content,
                    "created_at": last_message.created_at.isoformat(),
                    "is_mine": last_message.sender_id == user_id
                },
                "unread_count": unread_count
            })
        
        # 按最后消息时间排序
        conversations.sort(
            key=lambda x: x["last_message"]["created_at"],
            reverse=True
        )
        
        return {"conversations": conversations}
    except Exception as e:
        import traceback
        print(f"Error in get_conversations: {e}")
        traceback.print_exc()
        raise


@router.get("/history/{user_id}")
async def get_message_history(
    user_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取与指定用户的私聊历史"""
    my_id = current_user.id
    
    # 验证对方用户存在
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 查询双方的私聊消息
    query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == my_id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == my_id)
        ),
        Message.group_id.is_(None)
    ).order_by(desc(Message.created_at))
    
    total = query.count()
    messages = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 按时间正序返回（最新的在最后）
    messages.reverse()
    
    # 构建响应
    items = []
    for msg in messages:
        sender = current_user if msg.sender_id == my_id else other_user
        items.append(message_to_response(msg, sender))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "other_user": user_to_brief(other_user)
    }


@router.post("/send/{user_id}")
async def send_message(
    user_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送私聊消息"""
    # 验证接收者存在
    receiver = db.query(User).filter(User.id == user_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能给自己发消息
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发消息")
    
    # 创建消息
    db_message = Message(
        sender_id=current_user.id,
        receiver_id=user_id,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # 构建响应
    response_data = message_to_response(db_message, current_user)
    
    # 通过WebSocket推送给接收者
    await manager.send_personal_message({
        "type": "new_message",
        "data": response_data
    }, user_id)
    
    return response_data


@router.post("/read/{user_id}")
async def mark_messages_read(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记与指定用户的所有消息为已读"""
    db.query(Message).filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    return SuccessResponse(message="消息已标记为已读")


@router.get("/unread_count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的未读消息总数"""
    count = db.query(func.count(Message.id)).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False,
        Message.group_id.is_(None)
    ).scalar()
    
    return {"unread_count": count}


# WebSocket端点
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket连接端点，用于实时接收消息"""
    # 从query参数获取token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    # 验证token
    token_data = decode_token(token)
    if not token_data or not token_data.user_id:
        await websocket.close(code=4002, reason="Invalid token")
        return
    
    user_id = token_data.user_id
    
    # 验证用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=4003, reason="User not found")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
