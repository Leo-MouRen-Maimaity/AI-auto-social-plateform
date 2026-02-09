from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import Optional

from ..database import get_db
from ..models import User, Post, PostLike, Comment
from ..schemas import PostCreate, PostResponse, PostListResponse, LikeResponse, UserBrief
from ..auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/posts", tags=["帖子"])


def post_to_response(post: Post, current_user: Optional[User], db: Session) -> PostResponse:
    """将Post模型转换为响应格式"""
    is_liked = False
    if current_user:
        like = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id
        ).first()
        is_liked = like is not None
    
    comments_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar()
    
    return PostResponse(
        id=post.id,
        content=post.content,
        image_path=post.image_path,
        author_id=post.author_id,
        likes_count=post.likes_count,
        created_at=post.created_at,
        author=UserBrief(
            id=post.author.id,
            username=post.author.username,
            nickname=post.author.nickname,
            avatar_path=post.author.avatar_path,
            is_ai=post.author.is_ai
        ),
        is_liked=is_liked,
        comments_count=comments_count
    )


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    author_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取帖子列表"""
    query = db.query(Post).options(joinedload(Post.author))
    
    if author_id:
        query = query.filter(Post.author_id == author_id)
    
    total = query.count()
    posts = query.order_by(desc(Post.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    items = [post_to_response(post, current_user, db) for post in posts]
    
    return PostListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布帖子"""
    new_post = Post(
        author_id=current_user.id,
        content=post_data.content,
        image_path=post_data.image_path
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return post_to_response(new_post, current_user, db)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取帖子详情"""
    post = db.query(Post).options(joinedload(Post.author)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    return post_to_response(post, current_user, db)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除帖子"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此帖子"
        )
    
    db.delete(post)
    db.commit()
    return None


@router.post("/{post_id}/like", response_model=LikeResponse)
async def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """点赞/取消点赞"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        # 取消点赞
        db.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        liked = False
    else:
        # 点赞
        new_like = PostLike(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        post.likes_count += 1
        liked = True
    
    db.commit()
    db.refresh(post)
    
    return LikeResponse(liked=liked, likes_count=post.likes_count)
