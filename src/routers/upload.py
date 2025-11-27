"""模块名称: upload
主要功能: 文件上传路由

支持已登录用户和游客上传图片。
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

from src.auth.utils import ALGORITHM
from src.config import SECRET_KEY
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 图片存储目录
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 允许的图片类型
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}

# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def _get_username_from_token(authorization: Optional[str]) -> Optional[str]:
    """从 Authorization header 中提取用户名（可选）"""
    if not authorization:
        return None

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (ValueError, JWTError):
        return None


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """上传图片
    
    Args:
        file: 上传的文件
        authorization: Bearer Token（可选，用于识别用户）
    
    Returns:
        包含图片 URL 的 JSON 响应
    """
    # 可选认证 - 提取用户名用于日志
    username = _get_username_from_token(authorization) or "guest"

    # 检查文件类型
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}。支持的类型: {', '.join(ALLOWED_TYPES)}"
        )

    # 读取文件内容
    content = await file.read()

    # 检查文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件太大。最大允许大小: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 生成唯一文件名
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}{ext}"

    # 保存文件
    filepath = UPLOAD_DIR / filename
    try:
        with open(filepath, "wb") as f:
            f.write(content)
        logger.info("图片上传成功: %s (%d bytes) by %s", filename, len(content), username)
    except OSError as e:
        logger.error("保存图片失败: %s", e)
        raise HTTPException(status_code=500, detail="保存图片失败") from e

    # 返回可访问的 URL
    return JSONResponse({
        "success": True,
        "url": f"/api/images/{filename}",
        "filename": filename,
        "size": len(content)
    })


@router.delete("/{filename}")
async def delete_image(
    filename: str,
    authorization: Optional[str] = Header(None)
):
    """删除图片
    
    Args:
        filename: 要删除的文件名
        authorization: Bearer Token（可选）
    """
    username = _get_username_from_token(authorization) or "guest"

    # 安全检查：防止路径遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    filepath = UPLOAD_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        os.remove(filepath)
        logger.info("图片删除成功: %s by %s", filename, username)
        return JSONResponse({"success": True})
    except OSError as e:
        logger.error("删除图片失败: %s", e)
        raise HTTPException(status_code=500, detail="删除图片失败") from e
