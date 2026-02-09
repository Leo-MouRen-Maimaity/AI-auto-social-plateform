from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db
from ..models import User, Post, Comment
from ..schemas import CommentCreate, CommentResponse, CommentListResponse, UserBrief
from ..auth import get_current_user

router = APIRouter(prefix="/posts/{post_id}/comments", tags=["评论"])


@router.get("", response_model=CommentListResponse)
async def list_comments(
    post_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取帖子评论列表"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    query = db.query(Comment).options(joinedload(Comment.author)).filter(Comment.post_id == post_id)
    total = query.count()
    comments = query.order_by(Comment.created_at).offset(skip).limit(limit).all()
    
    items = [
        CommentResponse(
            id=c.id,
            post_id=c.post_id,
            author_id=c.author_id,
            content=c.content,
            created_at=c.created_at,
            author=UserBrief(
                id=c.author.id,
                username=c.author.username,
                nickname=c.author.nickname,
                avatar_path=c.author.avatar_path,
                is_ai=c.author.is_ai
            )
        )
        for c in comments
    ]
    
    return CommentListResponse(items=items, total=total)


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发表评论"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    new_comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=comment_data.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return CommentResponse(
        id=new_comment.id,
        post_id=new_comment.post_id,
        author_id=new_comment.author_id,
        content=new_comment.content,
        created_at=new_comment.created_at,
        author=UserBrief(
            id=current_user.id,
            username=current_user.username,
            nickname=current_user.nickname,
            avatar_path=current_user.avatar_path,
            is_ai=current_user.is_ai
        )
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除评论"""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.post_id == post_id
    ).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此评论"
        )
    
    db.delete(comment)
    db.commit()
    return None
