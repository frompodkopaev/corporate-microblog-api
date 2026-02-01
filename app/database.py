from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = "postgresql+asyncpg://postgres:@localhost:5432/cma_db"

class Base(DeclarativeBase):
    pass

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFabric = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)