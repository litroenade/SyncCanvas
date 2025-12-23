"""
素材库数据模�?
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Library(SQLModel, table=True):
    """素材库模�?

    存储导入�?Excalidraw 素材库元信息�?
    """

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    source: str = Field(default="local", max_length=255)
    version: int = Field(default=1)
    created_at: int = Field(
        default_factory=lambda: int(datetime.now().timestamp() * 1000)
    )


class LibraryItem(SQLModel, table=True):
    """素材库项模型

    存储素材库中的单个素材项及其向量表示�?
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    library_id: str = Field(foreign_key="library.id", index=True, max_length=36)
    item_id: str = Field(max_length=64, index=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=1000)
    tags: list = Field(default_factory=list, sa_column=Column(JSON))
    elements: list = Field(default_factory=list, sa_column=Column(JSON))
    embedding: Optional[bytes] = Field(default=None)
    created_at: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp() * 1000)
    )
