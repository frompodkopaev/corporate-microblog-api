from typing import AsyncGenerator, Optional, List
from fastapi import Depends, Header, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app import AsyncSessionFabric, Base, engine, User, Tweet
from app.schemas import TweetCreate
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

async def get_user_by_id(
        user_id: int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> User:
        user_service = UserService(db)
        requested_user = await user_service.get_user(user, user_id)
        return requested_user

async def follow_user(
        user_id: int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> bool:
    user_service = UserService(db)
    result = await user_service.follow_user(user, user_id)
    return result

async def unfollow_user(
        user_id: int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> bool:
    user_service = UserService(db)
    result = await user_service.unfollow_user(user, user_id)
    return result

async def like_tweet(
        tweet_id:int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> bool:
    user_service = UserService(db)
    result = await user_service.like_tweet(user, tweet_id)
    return result

async def unlike_tweet(
        tweet_id: int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> bool:
    user_service = UserService(db)
    result = await user_service.unlike_tweet(user, tweet_id)
    return result


async def create_tweet(
        tweet_schema: TweetCreate,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> int:
    tweet_service = TweetService(db)
    tweet_id = await tweet_service.create_tweet(user, tweet_schema.tweet_data, tweet_schema.media_ids)
    return tweet_id

async def delete_tweet(
        tweet_id:int,
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> bool:
    tweet_service = TweetService(db)
    result = await tweet_service.delete_tweet(user, tweet_id)
    return result


async def get_user_feed(
        user: User = Depends(authenticate_user),
        db: AsyncSession = Depends(get_db)
) -> List[Tweet]:
    user_service = UserService(db)
    tweet_list = await user_service.get_tweets_feed_list(user)
    return tweet_list

async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db)
) -> int:
    """Dependency for file upload"""
    media_service = MediaService(db)
    return await media_service.upload_file(user, file)

async def pagination_params(skip: int = 0, limit: int = 100) -> dict:
    return {"skip": skip, "limit": limit}
