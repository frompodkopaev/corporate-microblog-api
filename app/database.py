import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/corporative_microblog_api"
)

class Base(AsyncAttrs, DeclarativeBase):
    pass

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFabric = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)