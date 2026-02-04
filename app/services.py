from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_, update
from sqlalchemy.orm import selectinload

from app import ApiKey, User, Follow, Tweet, Media, Like


class UserService:
    """Service for working with User model in routes"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user(self, user: User, user_id: int) -> User:
        if user_id == user.id:
            return user

        requested_user: Optional[User] = await self.db.get(User, user_id)
        if not requested_user:
            raise ValueError("User not found")

        return requested_user

    async def follow_user(self, user: User, following_id: int) -> bool:
        if following_id == user.id:
            raise ValueError("User cannot follow himself")

        following_user = await self.db.get(User, following_id)

        if not following_user:
            raise ValueError("User not found")

        existing = await self.db.execute(
            select(Follow).where(
                Follow.follower_id == user.id,
                Follow.following_id == following_id
            )
        )

        if existing.scalar_one_or_none():
            raise ValueError("Already following this user")

        follow = Follow(follower_id=user.id, following_id=following_id)
        self.db.add(follow)
        await self.db.commit()
        await self.db.refresh(follow)
        return True

    async def unfollow_user(self, user, following_id: int) -> bool:
        result = await self.db.execute(
            select(Follow).where(
                Follow.follower_id == user.id,
                Follow.following_id == following_id
            )
        )

        follow = result.scalar_one_or_none()
        if not follow:
            return False

        await self.db.delete(follow)
        await self.db.commit()
        return True

    async def like_tweet(self, user: User, tweet_id: int) -> Optional[bool]:
        stmt = select(exists().where(Tweet.id == tweet_id))
        result = await self.db.execute(stmt)
        tweet_exists = result.scalar()
        if not tweet_exists:
            raise ValueError("Tweet not found")

        stmt = select(exists().where(
            and_(
                Like.tweet_id == tweet_id,
                Like.user_id == user.id
            )
        ))
        result = await self.db.execute(stmt)
        already_liked = result.scalar()
        if already_liked:
            raise ValueError("Tweet already liked")

        async with self.db.begin():
            new_like = Like(tweet_id = tweet_id, user_id = user.id)
            self.db.add(new_like)
        return True


    async def unlike_tweet(self, user: User, tweet_id: int) -> Optional[bool]:
        stmt = select(Like).where(
            and_(Like.tweet_id == tweet_id,
                 Like.user_id == user.id)
        )
        result = await self.db.execute(stmt)
        like = result.scalar_one_or_none()
        if not like:
            raise ValueError("Tweet not liked")
        async with self.db.begin():
            await self.db.delete(like)
        return True



class ApiKeyService:
    """Srvice for authentication by api-key"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, api_key: str) -> Optional[User]:
        key_prefix = api_key[:8]
        stmt = select(ApiKey).where(ApiKey.key_prefix == key_prefix).options(selectinload(ApiKey.user))
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        if not db_key:
            return None
        if not db_key.verify_key(api_key):
            return None
        return db_key.user


class TweetService:
    """Service for working with Tweet model"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tweet(
            self,
            user: User,
            tweet_data: str,
            tweet_media_ids: Optional[List[int]]=None
    ) -> int:
        if not tweet_data or not tweet_data.strip():
            raise ValueError("Tweet content cannot be empty")

        content = tweet_data.strip()

        if len(content) > 1000:
            raise ValueError("Tweet content too long (max 1000 characters)")

        async with self.db.begin():
            new_tweet = Tweet(
                user_id=user.id,
                content=tweet_data
            )
            self.db.add(new_tweet)
            await self.db.flush()
            if tweet_media_ids:
                stmt = update(Media).where(Media.id.in_(tweet_media_ids)).values(tweet_id=new_tweet.id)
                await self.db.execute(stmt)
        return new_tweet.id

    async def delete_tweet(
            self,
            user: User,
            tweet_id: int
    ) -> bool:
        stmt = select(Tweet).where(Tweet.id == tweet_id)
        result = await self.db.execute(stmt)
        tweet: Optional[Tweet|None] = result.scalar_one_or_none()
        if not tweet:
            raise ValueError("Tweet not found")

        if tweet.user_id != user.id:
            raise ValueError("User not the author of this tweet")

        async with self.db.begin():
            await self.db.delete(tweet)

        return True

class MediaService:
    """Service for media upload"""

    def __init__(self, db:AsyncSession):
        self.db = db

    async def create_media(self, link:str) -> int:
        async with self.db.begin():
            new_media = Media(link=link)
            self.db.add(new_media)
        return new_media.id
