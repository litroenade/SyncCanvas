"""模块名称: database
主要功能: 数据库连接和表初始化功能
"""

from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session

from src.models.user import User  # noqa: F401  # pylint: disable=unused-import
from src.db.models import (  # noqa: F401  # pylint: disable=unused-import
    Room,
    RoomMember,
    Update,
    Commit,
    AgentRun,
    AgentAction,
)
from src.config import config

# 确保数据库目录存在
_db_url = config.database_url
_db_path = _db_url.replace("sqlite:///", "").lstrip("./")
_db_dir = Path(_db_path).parent
_db_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False}
    if _db_url.startswith("sqlite")
    else {},
    echo=config.db_echo,
)


def init_db():
    """初始化数据库表

    创建所有定义的数据模型对应的表。
    必须先导入所有模型才能让 SQLModel.metadata 知道要创建哪些表。
    """

    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话

    Yields:
        Session: SQLModel 数据库会话对象
    """
    with Session(engine) as session:
        yield session


from contextlib import contextmanager


@contextmanager
def get_sync_session():
    """获取同步数据库会话上下文管理器
    
    用于非 FastAPI Depends 场景的同步数据库操作。
    
    Yields:
        Session: SQLModel 数据库会话对象
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
