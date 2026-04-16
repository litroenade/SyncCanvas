import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from jose import JWTError, jwt
from src.application.libraries.service import library_service
from src.auth.utils import ALGORITHM
from src.infra.config import config
from src.infra.singleton_canvas import SINGLETON_USER_USERNAME
from src.infra.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
router = APIRouter(tags=["upload"])

# 鍥剧墖瀛樺偍鐩綍
UPLOAD_DIR = PROJECT_ROOT / "data" / "images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 鍏佽鐨勫浘鐗囩被鍨?
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}

# 鏈€澶ф枃浠跺ぇ灏?(10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def _get_username_from_token(authorization: Optional[str]) -> Optional[str]:
    """浠?Authorization header 涓彁鍙栫敤鎴峰悕锛堝彲閫夛級"""
    if not authorization:
        return None

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, config.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (ValueError, JWTError):
        return None


def _resolve_upload_path(filename: str) -> Path:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="invalid_filename")
    return UPLOAD_DIR / filename


@router.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...), authorization: Optional[str] = Header(None)
):
    """涓婁紶鍥剧墖

    Args:
        file: 涓婁紶鐨勬枃浠?
        authorization: Bearer Token锛堝彲閫夛紝鐢ㄤ簬璇嗗埆鐢ㄦ埛锛?

    Returns:
        鍖呭惈鍥剧墖 URL 鐨?JSON 鍝嶅簲
    """
    # 鍙€夎璇?- 鎻愬彇鐢ㄦ埛鍚嶇敤浜庢棩蹇?
    username = _get_username_from_token(authorization) or SINGLETON_USER_USERNAME

    # 妫€鏌ユ枃浠剁被鍨?
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"涓嶆敮鎸佺殑鏂囦欢绫诲瀷: {file.content_type}銆傛敮鎸佺殑绫诲瀷: {', '.join(ALLOWED_TYPES)}",
        )

    # 璇诲彇鏂囦欢鍐呭
    content = await file.read()

    # 妫€鏌ユ枃浠跺ぇ灏?
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"鏂囦欢澶ぇ銆傛渶澶у厑璁稿ぇ灏? {MAX_FILE_SIZE // 1024 // 1024}MB",
        )

    # 鐢熸垚鍞竴鏂囦欢鍚?
    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}{ext}"

    # 淇濆瓨鏂囦欢
    filepath = _resolve_upload_path(filename)
    try:
        with open(filepath, "wb") as f:
            f.write(content)
        await library_service.index_uploaded_asset(
            filename=filename,
            original_name=file.filename or filename,
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
        )
        logger.info(
            "鍥剧墖涓婁紶鎴愬姛: %s (%d bytes) by %s", filename, len(content), username
        )
    except OSError as e:
        logger.error("淇濆瓨鍥剧墖澶辫触: %s", e)
        raise HTTPException(status_code=500, detail="淇濆瓨鍥剧墖澶辫触") from e
    except Exception as e:
        if filepath.exists():
            try:
                filepath.unlink()
            except OSError:
                logger.warning("鍥剧墖绱㈠紩澶辫触鍚庢棤娉曞洖婊氬凡鍐欏叆鏂囦欢: %s", filepath)
        logger.error("鍥剧墖绱㈠紩澶辫触: %s", e)
        raise HTTPException(status_code=500, detail="鍥剧墖绱㈠紩澶辫触") from e

    # 杩斿洖鍙闂殑 URL
    return JSONResponse(
        {
            "success": True,
            "url": f"/api/images/{filename}",
            "filename": filename,
            "size": len(content),
        }
    )


@router.get("/api/images/{filename}")
async def get_image(filename: str):
    filepath = _resolve_upload_path(filename)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="file_not_found")
    return FileResponse(filepath)


@router.delete("/api/upload/{filename}")
async def delete_image(filename: str, authorization: Optional[str] = Header(None)):
    """鍒犻櫎鍥剧墖

    Args:
        filename: 瑕佸垹闄ょ殑鏂囦欢鍚?
        authorization: Bearer Token锛堝彲閫夛級
    """
    username = _get_username_from_token(authorization) or SINGLETON_USER_USERNAME

    filepath = _resolve_upload_path(filename)

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="file_not_found")

    try:
        library_service.remove_uploaded_asset(filename)
        os.remove(filepath)
        logger.info(f"鍥剧墖鍒犻櫎鎴愬姛: {filename} by {username}")
        return JSONResponse({"success": True})
    except OSError as e:
        logger.error(f"鍒犻櫎鍥剧墖澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鍒犻櫎鍥剧墖澶辫触") from e
    except Exception as e:
        logger.error(f"鍒犻櫎鍥剧墖绱㈠紩澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鍒犻櫎鍥剧墖绱㈠紩澶辫触") from e

