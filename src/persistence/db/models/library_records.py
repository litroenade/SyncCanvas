"""Canonical persistence models for imported Excalidraw libraries."""

from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from src.utils.time import timestamp_ms


class Library(SQLModel, table=True):
    """Imported Excalidraw library metadata."""

    id: str = Field(primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    source: str = Field(default="local", max_length=255)
    version: int = Field(default=1)
    created_at: int = Field(default_factory=timestamp_ms)


class LibraryItem(SQLModel, table=True):
    """Stored library item payload and optional embedding."""

    id: Optional[int] = Field(default=None, primary_key=True)
    library_id: str = Field(foreign_key="library.id", index=True, max_length=36)
    item_id: str = Field(max_length=64, index=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=1000)
    tags: list = Field(default_factory=list, sa_column=Column(JSON))
    elements: list = Field(default_factory=list, sa_column=Column(JSON))
    embedding: Optional[bytes] = Field(default=None)
    created_at: int = Field(default_factory=timestamp_ms)
