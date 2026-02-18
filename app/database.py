"""
Database configuration module for the Corporate Microblog API.
Sets up SQLAlchemy async engine, session factory, and base model class.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/corporative_microblog_api",
)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFabric = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)
