from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# ============ Auth Schemas ============

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str = Field(..., min_length=1, max_length=50)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ============ User Schemas ============

class UserBase(BaseModel):
    username: str
    nickname: str
    avatar_path: Optional[str] = None
    bio: Optional[str] = None
    is_ai: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_path: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """简要用户信息，用于嵌套显示"""
    id: int
    username: str
    nickname: str
    avatar_path: Optional[str] = None
    is_ai: bool = False
    
    class Config:
        from_attributes = True


# ============ Post Schemas ============

class PostBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    image_path: Optional[str] = None


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    id: int
    author_id: int
    likes_count: int
    created_at: datetime
    author: UserBrief
    is_liked: bool = False  # 当前用户是否点赞
    comments_count: int = 0
    
    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    items: List[PostResponse]
    total: int
    page: int
    page_size: int


# ============ Comment Schemas ============

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentCreate(CommentBase):
    pass


class CommentResponse(CommentBase):
    id: int
    post_id: int
    author_id: int
    created_at: datetime
    author: UserBrief
    
    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int


# ============ Like Schemas ============

class LikeResponse(BaseModel):
    liked: bool
    likes_count: int


# ============ Message Schemas ============

class MessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageCreate(MessageBase):
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None


class MessageResponse(MessageBase):
    id: int
    sender_id: int
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    sender: UserBrief
    
    class Config:
        from_attributes = True


# ============ Common Schemas ============

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
