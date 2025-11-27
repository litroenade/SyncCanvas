"""模块名称: router
主要功能: 用户认证路由，提供登录、Token 管理等接口
支持通过服务端 secret_key 认证，用户名可任意填写
"""

import json
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session, select

from src.db.database import get_session
from src.models.user import User
from .utils import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# 设置文件路径
SETTINGS_FILE = Path(__file__).resolve().parents[2] / "data" / "settings.json"


def _load_or_create_secret_key() -> str:
    """加载或创建服务端 secret_key"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if "secret_key" in data:
                    return data["secret_key"]
        except (json.JSONDecodeError, OSError):
            pass

    # 生成新的 secret_key
    new_key = secrets.token_hex(32)
    settings = {}
    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    settings["secret_key"] = new_key
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    return new_key


# 加载服务端 secret_key
SERVER_SECRET_KEY = _load_or_create_secret_key()


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    password: str


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    """通过 secret_key 登录

    用户名可以随意填写，密码需要是服务端的 secret_key
    """
    # 验证 secret_key
    if not secrets.compare_digest(form_data.password, SERVER_SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 用户名可以随意，检查或创建用户
    username = form_data.username.strip() or "admin"
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()

    if not user:
        # 自动创建用户，密码哈希用占位符（实际不用于验证）
        user = User(username=username, password_hash="key_auth_user")
        session.add(user)
        session.commit()
        session.refresh(user)

    # 生成 Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/secret-key-hint")
async def get_secret_key_hint():
    """获取 secret_key 的提示（仅显示前后几位）"""
    key = SERVER_SECRET_KEY
    if len(key) > 12:
        hint = f"{key[:4]}...{key[-4:]}"
    else:
        hint = "****"
    return {"hint": hint, "message": "完整 key 在 data/settings.json 中"}


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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


@router.get("/me", response_model=UserCreate)  # 简单返回用户名
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {"username": current_user.username, "password": ""}  # 不返回密码 hash
