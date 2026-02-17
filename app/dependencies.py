from typing import AsyncGenerator, Optional, List
from fastapi import Depends, Header, HTTPException, status, UploadFile, File
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionFabric, Base, engine
from app.models import User, Tweet
from app.schemas import TweetCreate
from app.services import UserService, ApiKeyService, TweetService, MediaService
from app.core.exceptions import UnauthorizedException


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
        raise UnauthorizedException("API key is required")
    return api_key


@lru_cache(maxsize=128)
def get_user_service_cached(db: AsyncSession) -> UserService:
    """Cached factory for UserService"""
    return UserService(db)


@lru_cache(maxsize=128)
def get_api_key_service_cached(db: AsyncSession) -> ApiKeyService:
    """Cached factory for ApiKeyService"""
    return ApiKeyService(db)


@lru_cache(maxsize=128)
def get_tweet_service_cached(db: AsyncSession) -> TweetService:
    """Cached factory for TweetService"""
    return TweetService(db)


@lru_cache(maxsize=128)
def get_media_service_cached(db: AsyncSession) -> MediaService:
    """Cached factory for MediaService"""
    return MediaService(db)


def get_service(service_class):
    """Generic factory for services with caching"""
    service_cache = {}

    async def dependency(db: AsyncSession = Depends(get_db)):
        cache_key = id(db)
        if cache_key not in service_cache:
            service_cache[cache_key] = service_class(db)
        return service_cache[cache_key]

    return dependency


get_user_service = get_service(UserService)
get_api_key_service = get_service(ApiKeyService)
get_tweet_service = get_service(TweetService)
get_media_service = get_service(MediaService)


async def get_current_user(
        api_key: str = Depends(get_api_key),
        api_key_service = Depends(get_api_key_service)
) -> User:
    user = await api_key_service.authenticate(api_key)

    if not user:
        raise UnauthorizedException("Invalid API key")

    return user

async def get_user_by_id(
        user_id: int,
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> User:
        requested_user = await user_service.get_user(current_user, user_id)
        return requested_user

async def follow_user(
        user_id: int,
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> bool:
    return await user_service.follow_user(current_user, user_id)

async def unfollow_user(
        user_id: int,
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> bool:
    return await user_service.unfollow_user(current_user, user_id)

async def like_tweet(
        tweet_id: int,
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> bool:
    return await user_service.like_tweet(current_user, tweet_id)

async def unlike_tweet(
        tweet_id: int,
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> bool:
    return await user_service.unlike_tweet(current_user, tweet_id)

async def get_user_feed(
        user_service: UserService = Depends(get_user_service),
        current_user: User = Depends(get_current_user)
) -> List[Tweet]:
    return await user_service.get_tweets_feed_list(current_user)


async def create_tweet(
        tweet_schema: TweetCreate,
        tweet_service: TweetService = Depends(get_tweet_service),
        current_user: User = Depends(get_current_user)
) -> int:
    return await tweet_service.create_tweet(current_user, tweet_schema.tweet_data, tweet_schema.media_ids)

async def delete_tweet(
        tweet_id:int,
        tweet_service: TweetService = Depends(get_tweet_service),
        current_user: User = Depends(get_current_user)
) -> bool:
    return await tweet_service.delete_tweet(current_user, tweet_id)


async def upload_media(
    file: UploadFile = File(...),
    media_service: MediaService = Depends(get_media_service),
    current_user: User = Depends(get_current_user)
) -> int:
    """Dependency for file upload"""
    return await media_service.upload_file(current_user, file)
