"""
Service layer module for the Corporate Microblog API.
Contains business logic and database operations.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from time import time
from typing import Dict, List, Optional
from uuid import uuid4

import aiofiles
from fastapi import UploadFile
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessLogicException,
    ConflictException,
    InsufficientPermissionsException,
    NotFoundException,
    ValidationException,
)
from app.models import ApiKey, Follow, Like, Media, Tweet, User


class UserService:
    """Service for working with User model in routes."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize UserService with database session."""
        self.db = db

    async def get_user(self, user: User, user_id: int) -> User:
        """Get user by ID with access control."""
        if user_id == user.id:
            return user

        requested_user: Optional[User] = await self.db.get(User, user_id)
        if not requested_user:
            raise NotFoundException("User", user_id)

        return requested_user

    async def follow_user(self, user: User, following_id: int) -> bool:
        """Follow another user."""
        if following_id == user.id:
            raise BusinessLogicException("User cannot follow himself")

        stmt = (
            select(User, Follow)
            .outerjoin(
                Follow,
                and_(
                    Follow.follower_id == user.id, Follow.following_id == following_id
                ),
            )
            .where(User.id == following_id)
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            raise NotFoundException("User", following_id)

        user_data, existing_follow = row
        if existing_follow:
            raise ConflictException("Already following this user")

        follow = Follow(follower_id=user.id, following_id=following_id)
        self.db.add(follow)
        return True

    async def unfollow_user(self, user, following_id: int) -> bool:
        """Unfollow a user."""
        if following_id == user.id:
            raise BusinessLogicException("User cannot unfollow himself")

        stmt = (
            select(User, Follow)
            .outerjoin(
                Follow,
                and_(
                    Follow.follower_id == user.id, Follow.following_id == following_id
                ),
            )
            .where(User.id == following_id)
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            raise NotFoundException("User", following_id)

        user_data, existing_follow = row
        if not existing_follow:
            raise ConflictException("Not following this user")
        await self.db.delete(existing_follow)
        return True

    async def like_tweet(self, user: User, tweet_id: int) -> bool:
        """Like a tweet."""
        stmt = (
            select(Tweet)
            .where(Tweet.id == tweet_id)
            .options(selectinload(Tweet.likes.and_(Like.user_id == user.id)))
            .with_for_update()
        )

        result = await self.db.execute(stmt)
        tweet = result.scalar_one_or_none()

        if not tweet:
            raise NotFoundException("Tweet", tweet_id)

        if any(like.user_id == user.id for like in tweet.likes):
            raise ConflictException("Tweet already liked")

        new_like = Like(tweet_id=tweet_id, user_id=user.id)
        self.db.add(new_like)
        tweet.likes_counter += 1

        return True

    async def unlike_tweet(self, user: User, tweet_id: int) -> bool:
        """Remove like from a tweet."""
        stmt = (
            select(Tweet)
            .where(Tweet.id == tweet_id)
            .options(selectinload(Tweet.likes))
            .with_for_update()
        )

        result = await self.db.execute(stmt)
        tweet = result.scalar_one_or_none()

        if not tweet:
            raise NotFoundException("Tweet", tweet_id)

        like_to_delete = None
        for like in tweet.likes:
            if like.user_id == user.id:
                like_to_delete = like
                break

        if not like_to_delete:
            raise ConflictException("Tweet not liked")

        await self.db.delete(like_to_delete)

        if tweet.likes_counter > 0:
            tweet.likes_counter -= 1

        return True

    async def get_tweets_feed_list(self, user: User) -> List[Tweet]:
        """Get feed of tweets from followed users."""
        stmt = (
            select(Tweet)
            .outerjoin(Follow, Follow.following_id == Tweet.user_id)  # LEFT OUTER JOIN
            .where(
                or_(
                    Follow.follower_id == user.id,  # твиты от подписок
                    Tweet.user_id == user.id  # собственные твиты
                )
            )
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.media),
                selectinload(Tweet.likes).selectinload(Like.user),
            )
            .order_by(Tweet.id.desc(), Tweet.likes_counter.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class ApiKeyService:
    """Service for authentication by api-key."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize ApiKeyService with database session."""
        self.db = db
        self._cache: Dict = {}
        self._cache_ttl = 300

    async def authenticate(self, api_key: str) -> Optional[User]:
        """Authenticate user by API key."""
        cache_key = hashlib.md5(api_key.encode()).hexdigest()
        cached_result = self._check_cache(cache_key)
        if cached_result is not None:
            return cached_result

        key_prefix = api_key[:8]

        stmt = (
            select(ApiKey)
            .where(and_(ApiKey.key_prefix == key_prefix, ApiKey.user.has()))
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
        """Check cache for existing authentication result."""
        if key in self._cache:
            user, timestamp = self._cache[key]
            if time() - timestamp < self._cache_ttl:
                return user
            else:
                del self._cache[key]
        return None

    def _add_to_cache(self, key: str, user: Optional[User]) -> None:
        """Add authentication result to cache."""
        self._cache[key] = (user, time())


class TweetService:
    """Service for working with Tweet model."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize TweetService with database session."""
        self.db = db

    async def create_tweet(
        self, user: User, tweet_data: str, tweet_media_ids: Optional[List[int]] = None
    ) -> int:
        """Create a new tweet."""
        if not tweet_data or not tweet_data.strip():
            raise ValidationException("Tweet content cannot be empty")

        content = tweet_data.strip()

        if len(content) > 1000:
            raise ValidationException("Tweet content too long (max 1000 characters)")

        new_tweet = Tweet(user_id=user.id, content=content)

        if tweet_media_ids:
            stmt = select(Media).where(Media.id.in_(tweet_media_ids))
            result = await self.db.execute(stmt)
            media_files = result.scalars().all()
            new_tweet.media.extend(media_files)

        self.db.add(new_tweet)
        await self.db.flush()

        return new_tweet.id

    async def delete_tweet(self, user: User, tweet_id: int) -> bool:
        """Delete a tweet."""
        stmt = select(Tweet).where(Tweet.id == tweet_id)
        result = await self.db.execute(stmt)
        tweet: Optional[Tweet] = result.scalar_one_or_none()
        if not tweet:
            raise NotFoundException("Tweet", tweet_id)

        if tweet.user_id != user.id:
            raise InsufficientPermissionsException("User not the author of this tweet")

        await self.db.delete(tweet)

        return True


class MediaService:
    """Service for media upload and management."""

    UPLOAD_ROOT = Path("uploads")
    ALLOWED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, db: AsyncSession) -> None:
        """Initialize MediaService with database session."""
        self.db = db
        self.UPLOAD_ROOT.mkdir(exist_ok=True)

    async def upload_file(self, user: User, file: UploadFile) -> int:
        """Upload file and save to database."""
        await self._validate_file(file)

        if not file.filename:
            ext = ".bin"
        else:
            ext = Path(file.filename).suffix

        unique_name = f"{uuid4()}{ext}"
        now = datetime.now()

        web_relative = f"user_{user.id}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_name}"

        full_path = self.UPLOAD_ROOT / web_relative
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        media = Media(link=f"/uploads/{web_relative}")

        self.db.add(media)
        await self.db.flush()

        return media.id

    async def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        if file.content_type not in self.ALLOWED_TYPES:
            raise BusinessLogicException(f"File type {file.content_type} not allowed")

        if file.size and file.size > self.MAX_FILE_SIZE:
            raise BusinessLogicException("File too large")

    def _generate_file_path(self, user_id: int, filename: Optional[str]) -> Path:
        """Generate unique file path."""
        if not filename:
            ext = ".bin"
        else:
            ext = Path(filename).suffix

        unique_name = f"{uuid4()}{ext}"

        now = datetime.now()
        user_dir = self.UPLOAD_ROOT / f"user_{user_id}"
        date_dir = user_dir / f"{now.year}" / f"{now.month:02d}" / f"{now.day:02d}"

        date_dir.mkdir(parents=True, exist_ok=True)

        return date_dir / unique_name
