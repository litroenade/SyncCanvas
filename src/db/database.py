"""模块名称: database
主要功能: 数据库连接和表初始化功能
"""

from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session

from src.models.user import User  # noqa: F401  # pylint: disable=unused-import
from src.db.models import (  # noqa: F401  # pylint: disable=unused-import
    Room, RoomMember, Stroke, Update, Commit
)
from src.config import DATABASE_URL, DB_ECHO

# 确保数据库目录存在
_db_path = DATABASE_URL.replace("sqlite:///", "").lstrip("./")
_db_dir = Path(_db_path).parent
_db_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=DB_ECHO
)


def init_db():
    """初始化数据库表

    创建所有定义的数据模型对应的表。
    必须先导入所有模型才能让 SQLModel.metadata 知道要创建哪些表。
    """
    # 导入所有模型以注册到 SQLModel.metadata
    # pylint: disable=import-outside-toplevel,unused-import


    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话

    Yields:
        Session: SQLModel 数据库会话对象
    """
    with Session(engine) as session:
        yield session
