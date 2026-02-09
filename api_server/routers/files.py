import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
import aiofiles
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.config import get_settings
from ..auth import get_current_user
from ..models import User

settings = get_settings()
router = APIRouter(prefix="/files", tags=["文件"])

# 允许的图片类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_upload_dir():
    """确保上传目录存在"""
    if not os.path.exists(settings.upload_dir):
        os.makedirs(settings.upload_dir)
    # 创建子目录
    for subdir in ['images', 'avatars']:
        path = os.path.join(settings.upload_dir, subdir)
        if not os.path.exists(path):
            os.makedirs(path)


def generate_filename(original_filename: str) -> str:
    """生成唯一文件名"""
    ext = os.path.splitext(original_filename)[1].lower()
    date_prefix = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    return f"{date_prefix}_{unique_id}{ext}"


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传图片文件"""
    ensure_upload_dir()
    
    # 检查文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型，允许: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 检查文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，最大允许 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    # 生成文件名并保存
    filename = generate_filename(file.filename)
    file_path = os.path.join(settings.upload_dir, "images", filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # 返回可访问的URL路径
    url_path = f"{settings.upload_url_prefix}/images/{filename}"
    
    return {
        "url": url_path,
        "filename": filename,
        "size": len(content)
    }


@router.post("/upload/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传头像"""
    ensure_upload_dir()
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型"
        )
    
    content = await file.read()
    
    if len(content) > 2 * 1024 * 1024:  # 头像限制2MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像文件过大，最大允许 2MB"
        )
    
    # 使用用户ID作为文件名前缀
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:6]}{ext}"
    file_path = os.path.join(settings.upload_dir, "avatars", filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    url_path = f"{settings.upload_url_prefix}/avatars/{filename}"
    
    return {
        "url": url_path,
        "filename": filename
    }


@router.get("/images/{filename}")
async def get_image(filename: str):
    """获取图片"""
    file_path = os.path.join(settings.upload_dir, "images", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """获取头像"""
    file_path = os.path.join(settings.upload_dir, "avatars", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)
