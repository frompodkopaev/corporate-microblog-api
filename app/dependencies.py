from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import AsyncSessionFabric, Base, engine, User
from app.services import UserService, ApiKeyService, TweetService, MediaService


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFabric() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_db():
    await engine.dispose()


async def get_api_key(api_key: Optional[str] = Header(None, alias="api-key")) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
    return api_key


async def get_user_service(db: AsyncSession = Depends(get_db)):
    return UserService(db)

async def get_api_key_service(db: AsyncSession = Depends(get_db)):
    return ApiKeyService(db)

async def get_tweet_service(db: AsyncSession = Depends(get_db)):
    return TweetService(db)

async def get_media_service(db: AsyncSession = Depends(get_db)):
    return MediaService(db)


async def authenticate_user(
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> User:
    apy_key_service = ApiKeyService(db)
    user = await apy_key_service.authenticate(api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return user


async def pagination_params(skip: int = 0, limit: int = 100) -> dict:
    return {"skip": skip, "limit": limit}
