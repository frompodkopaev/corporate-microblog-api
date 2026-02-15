from fastapi import UploadFile, HTTPException
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_, update
from sqlalchemy.orm import selectinload

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
        stmt = select(Tweet).where(Tweet.id == tweet_id).with_for_update()
        result = await self.db.execute(stmt)
        tweet: Optional[Tweet|None] = result.scalar_one_or_none()
        if not tweet:
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

        new_like = Like(tweet_id = tweet_id, user_id = user.id)
        self.db.add(new_like)
        tweet.likes_counter += 1
        return True


    async def unlike_tweet(self, user: User, tweet_id: int) -> bool:
        stmt = select(Tweet).where(Tweet.id == tweet_id).with_for_update()
        result = await self.db.execute(stmt)
        tweet = result.scalar_one_or_none()

        if not tweet:
            raise ValueError("Tweet not found")

        new_stmt = select(Like).where(
            and_(Like.tweet_id == tweet_id,
                 Like.user_id == user.id)
        )
        result = await self.db.execute(new_stmt)
        like = result.scalar_one_or_none()

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

        content = await file.read()
        file_path.write_bytes(content)

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

        content = await file.read()
        if len(content) > self.MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large. Max: {self.MAX_FILE_SIZE}")

        await file.seek(0)

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
