"""模块名称: database
主要功能: 数据库连接和表初始化功能
"""

from sqlmodel import SQLModel, create_engine, Session

from src.config import DATABASE_URL, DB_ECHO


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=DB_ECHO
)


def init_db():
    """初始化数据库表

    创建所有定义的数据模型对应的表。
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话

    Yields:
        Session: SQLModel 数据库会话对象
    """
    with Session(engine) as session:
        yield session
