import aiofiles
from fastapi import UploadFile, HTTPException
from time import time
from typing import Optional, List, Dict
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_, update
from sqlalchemy.orm import selectinload
import hashlib

from app.models import ApiKey, User, Follow, Tweet, Media, Like


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

        stmt = (
            select(User, Follow)
            .outerjoin(
                Follow,
                and_(
                    Follow.follower_id == user.id,
                    Follow.following_id == following_id
                )
            )
            .where(User.id == following_id)
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError("User not found")

        user_data, existing_follow = row
        if existing_follow:
            raise ValueError("Already following this user")

        follow = Follow(follower_id=user.id, following_id=following_id)
        self.db.add(follow)
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

        return True

    async def like_tweet(self, user: User, tweet_id: int) -> bool:
        stmt = (
            select(Tweet)
            .where(Tweet.id == tweet_id)
            .options(
                selectinload(Tweet.likes.and_(Like.user_id == user.id))
            )
            .with_for_update()
        )

        result = await self.db.execute(stmt)
        tweet = result.scalar_one_or_none()

        if not tweet:
            raise ValueError("Tweet not found")

        if any(like.user_id == user.id for like in tweet.likes):
            raise ValueError("Tweet already liked")

        new_like = Like(tweet_id=tweet_id, user_id=user.id)
        self.db.add(new_like)
        tweet.likes_counter += 1

        return True

    async def unlike_tweet(self, user: User, tweet_id: int) -> bool:
        stmt = (
            select(Tweet, Like)
            .outerjoin(
                Like,
                and_(
                    Like.tweet_id == Tweet.id,
                    Like.user_id == user.id
                )
            )
            .where(Tweet.id == tweet_id)
            .with_for_update()
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError("Tweet not found")

        tweet, like = row

        if not like:
            raise ValueError("Tweet not liked")

        await self.db.delete(like)

        if tweet.likes_counter > 0:
            tweet.likes_counter -= 1

        return True

    async def get_tweets_feed_list(self, user:User) -> List[Tweet]:
        stmt = (
            select(Tweet)
            .join(Follow, Follow.following_id == Tweet.user_id)
            .where(
                and_(
                    Follow.follower_id == user.id,
                    Tweet.user_id != user.id
                )
            )
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.media),
                selectinload(Tweet.likes).selectinload(Like.user)
            )
            .order_by(Tweet.likes_counter.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class ApiKeyService:
    """Srvice for authentication by api-key"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict = {}
        self._cache_ttl = 300

    async def authenticate(self, api_key: str) -> Optional[User]:
        cache_key = hashlib.md5(api_key.encode()).hexdigest()
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            return cached_result

        key_prefix = api_key[:8]

        stmt = (
            select(ApiKey)
            .where(
                and_(
                    ApiKey.key_prefix == key_prefix,
                    ApiKey.user.has()  # Быстрая проверка через индекс
                )
            )
            .options(selectinload(ApiKey.user).load_only(User.id, User.name))
        )

        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()

        if not db_key:
            return None
        if not db_key.verify_key(api_key):
            return None
        user = db_key.user
        self._add_to_cache(cache_key, user)
        return db_key.user

    def _check_cache(self, key: str) -> Optional[User]:
        if key in self._cache:
            user, timestamp = self._cache[key]
            if time() - timestamp < self._cache_ttl:
                return user
            else:
                del self._cache[key]
        return None

    def _add_to_cache(self, key: str, user: Optional[User]):
        self._cache[key] = (user, time())


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

        new_tweet = Tweet(user_id=user.id, content=content)

        if tweet_media_ids:
            stmt = select(Media).where(Media.id.in_(tweet_media_ids))
            result = await self.db.execute(stmt)
            media_files = result.scalars().all()
            new_tweet.media.extend(media_files)

        self.db.add(new_tweet)
        await self.db.flush()

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

        return True

class MediaService:
    """Service for media upload and management"""

    UPLOAD_ROOT = Path("uploads")
    ALLOWED_TYPES = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, db: AsyncSession):
        self.db = db
        self.UPLOAD_ROOT.mkdir(exist_ok=True)

    async def upload_file(
            self,
            user: User,
            file: UploadFile
    ) -> int:
        """Upload file and save to database"""
        await self._validate_file(file)

        file_path = self._generate_file_path(user.id, file.filename)

        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        media = Media(
            link=str(file_path)
        )

        self.db.add(media)
        await self.db.flush()

        return media.id

    async def _validate_file(self, file: UploadFile):
        """Validate uploaded file"""
        if file.content_type not in self.ALLOWED_TYPES:
            raise HTTPException(400, f"File type {file.content_type} not allowed")

        if file.size and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large")

    def _generate_file_path(self, user_id: int, filename: Optional[str|None]) -> Path:
        """Generate unique file path"""
        if not filename:
            base_name = "uploaded_file"
            ext = ".bin"
        else:
            ext = Path(filename).suffix

        unique_name = f"{uuid4()}{ext}"

        now = datetime.now()
        user_dir = self.UPLOAD_ROOT / f"user_{user_id}"
        date_dir = user_dir / f"{now.year}" / f"{now.month:02d}" / f"{now.day:02d}"

        date_dir.mkdir(parents=True, exist_ok=True)

        return date_dir / unique_name
