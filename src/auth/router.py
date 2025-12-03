"""模块名称: router
主要功能: 用户认证路由，提供登录、Token 管理等接口
支持通过服务端 secret_key 认证，用户名可任意填写
"""

import json
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session, select

from src.config import config
from src.db.database import get_session
from src.models.user import User
from .utils import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    get_current_user,
    get_current_user_optional,
    oauth2_scheme,
    oauth2_scheme_optional,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    """JWT Token 响应模型"""

    access_token: str
    token_type: str


class UserCreate(BaseModel):
    """用户创建/返回模型"""

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
    if not secrets.compare_digest(form_data.password, config.secret_key):
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
    key = config.secret_key
    if len(key) > 12:
        hint = f"{key[:4]}...{key[-4:]}"
    else:
        hint = "****"
    return {"hint": hint, "message": "完整 key 在 config.toml 中"}


@router.get("/me", response_model=UserCreate)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """获取当前登录用户信息"""
    return {"username": current_user.username, "password": ""}
