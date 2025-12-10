"""模块名称: deps
主要功能: FastAPI 依赖注入

提供用户认证相关的依赖注入函数，支持从 Header 和 Query 参数获取 Token。
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config import config
from src.db.models import User
from src.logger import get_logger

logger = get_logger(__name__)

# OAuth2 密码模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class AuthException:
    """认证异常定义"""

    CREDENTIALS = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    INACTIVE = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="用户未激活",
    )

    FORBIDDEN = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="权限不足",
    )


async def get_token_from_request(
    request: Request, token: Optional[str] = None
) -> Optional[str]:
    """从请求中提取 Token

    优先级：URL 参数 > Header

    Args:
        request: FastAPI 请求对象
        token: 从 OAuth2 scheme 获取的 token

    Returns:
        str: Token 字符串；不存在则返回 None
    """
    # 1. 尝试从 URL 参数获取
    url_token = request.query_params.get("token")
    if url_token:
        # 处理可能带有 Bearer 前缀的 token
        if url_token.startswith("Bearer "):
            url_token = url_token.split(" ", 1)[1]
        return url_token

    # 2. 尝试从 Header 获取
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    # 3. 使用 OAuth2 scheme 的结果
    return token


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """获取当前用户

    从请求中提取 Token 并验证；返回对应的用户对象。

    Args:
        request: FastAPI 请求对象
        token: OAuth2 Token

    Returns:
        User: 用户对象

    Raises:
        HTTPException: 认证失败
    """
    token = await get_token_from_request(request, token)

    if not token:
        logger.debug("请求中未找到 Token")
        raise AuthException.CREDENTIALS

    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=["HS256"],
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise AuthException.CREDENTIALS
    except JWTError as e:
        logger.debug(f"JWT 验证失败: {e}")
        raise AuthException.CREDENTIALS from e

    # 查询用户
    user = await User.get_or_none(username=username)
    if user is None:
        logger.debug(f"用户未找到: {username}")
        raise AuthException.CREDENTIALS

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户

    Args:
        current_user: 当前用户

    Returns:
        User: 活跃的用户对象

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise AuthException.INACTIVE
    return current_user


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """获取可选的当前用户

    不抛出异常；未认证时返回 None。

    Args:
        request: FastAPI 请求对象
        token: OAuth2 Token

    Returns:
        User | None: 用户对象或 None
    """
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None
