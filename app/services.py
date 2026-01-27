from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import ApiKey, User, Follow


class UserService:
    """Service for working with User model in routes"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def follow_user(self, follower_id: int, following_id: int) -> Follow:
        if following_id == follower_id:
            raise ValueError("User cannot follow himself")

        follower = await self.db.get(User, follower_id)
        following = await self.db.get(User, following_id)

        if not follower or not following:
            raise ValueError("User not found")

        existing = await self.db.execute(
            select(Follow).where(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id
            )
        )

        if existing.scalar_one_or_none():
            raise ValueError("Already following this user")

        follow = Follow(follower_id=follower_id, following_id=following_id)
        self.db.add(follow)
        await self.db.commit()
        await self.db.refresh(follow)

        return follow

    async def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        result = await self.db.execute(
            select(Follow).where(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id
            )
        )

        follow = result.scalar_one_or_none()
        if not follow:
            return False

        await self.db.delete(follow)
        await self.db.commit()
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
