"""模块名称: auth
主要功能: 用户认证服务

提供用户注册、登录、Token 生成和密码验证等功能。
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from sqlmodel import Session
from sqlmodel import select

from src.config import config
from src.db.user import User
from src.logger import get_logger

logger = get_logger(__name__)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天


def hash_password(password: str) -> str:
    """哈希密码

    Args:
        password: 明文密码

    Returns:
        str: 密码哈希
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 密码哈希

    Returns:
        bool: 是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问 Token

    Args:
        data: Token 载荷数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT Token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码 Token

    Args:
        token: JWT Token

    Returns:
        dict: 载荷数据；失败返回 None
    """
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[ALGORITHM])
        return payload
    except Exception as e: # pylint: disable=broad-except
        logger.debug(f"Token 解码失败: {e}")
        return None


async def register_user(
    session: Session,
    username: str,
    password: str,
    nickname: str = "",
) -> User:
    """注册新用户

    Args:
        session: 数据库会话
        username: 用户名
        password: 密码
        nickname: 昵称

    Returns:
        User: 创建的用户

    Raises:
        ValueError: 用户名已存在
    """
    # 检查用户名是否已存在

    statement = select(User).where(User.username == username)
    existing = session.exec(statement).first()
    if existing:
        raise ValueError(f"用户名 {username} 已存在")

    # 创建用户
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname or username,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"新用户注册: {username}")
    return user


async def authenticate_user(
    session: Session,
    username: str,
    password: str,
) -> Optional[User]:
    """验证用户凭证

    Args:
        session: 数据库会话
        username: 用户名
        password: 密码

    Returns:
        User: 验证成功返回用户；失败返回 None
    """

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()

    if not user:
        logger.debug(f"用户不存在: {username}")
        return None

    if not verify_password(password, user.password_hash):
        logger.debug(f"密码错误: {username}")
        return None

    if not user.is_available:
        logger.debug(f"用户不可用: {username}")
        return None

    # 更新登录时间
    user.update_login_time()
    session.add(user)
    session.commit()

    logger.info(f"用户登录: {username}")
    return user


def login_for_token(user: User) -> dict:
    """生成登录 Token 响应

    Args:
        user: 用户对象

    Returns:
        dict: 包含 access_token 和 token_type 的字典
    """
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_public_dict(),
    }
