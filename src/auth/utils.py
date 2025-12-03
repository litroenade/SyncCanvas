"""模块名称: utils
主要功能: 认证工具函数，提供密码哈希、验证、JWT Token 生成等功能
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlmodel import Session, select

from src.config import config
from src.db.database import get_session
from src.models.user import User

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌

    Args:
        data: 要编码到 Token 中的数据
        expires_delta: Token 过期时间增量

    Returns:
        str: 编码后的 JWT Token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session),
) -> User:
    """获取当前登录用户

    Args:
        token: JWT Token
        session: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)],
    session: Session = Depends(get_session),
) -> Optional[User]:
    """获取当前登录用户（可选，未登录返回 None）

    Args:
        token: JWT Token，可选
        session: 数据库会话

    Returns:
        Optional[User]: 当前用户对象，未登录返回 None
    """
    if token is None:
        return None

    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    return user
