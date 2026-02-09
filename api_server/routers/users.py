from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User
from ..schemas import UserResponse, UserUpdate, UserBrief
from ..auth import get_current_user

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    if user_data.nickname is not None:
        current_user.nickname = user_data.nickname
    if user_data.avatar_path is not None:
        current_user.avatar_path = user_data.avatar_path
    if user_data.bio is not None:
        current_user.bio = user_data.bio
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/", response_model=List[UserBrief])
async def list_users(
    is_ai: bool = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    query = db.query(User)
    if is_ai is not None:
        query = query.filter(User.is_ai == is_ai)
    users = query.offset(skip).limit(limit).all()
    return users
