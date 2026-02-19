"""
Pydantic schemas for request/response validation and serialization.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import Tweet, User


class BasicResponse(BaseModel):
    """Base response schema."""

    result: bool = True


class TweetCreate(BaseModel):
    """Tweet creation schema."""

    tweet_data: str = Field(..., alias="content", min_length=1, max_length=1000)
    tweet_media_ids: Optional[List[int]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class TweetInfo(BaseModel):
    """Tweet information schema."""

    id: int
    content: str
    attachments: List[str] = []
    author: "UserBasic"
    likes: List["UserBasic"] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, tweet: Tweet) -> "TweetInfo":
        """Create TweetInfo from ORM model."""
        return cls(
            id=tweet.id,
            content=tweet.content,
            attachments=[media.link for media in tweet.media],
            author=UserBasic(id=tweet.author.id, name=tweet.author.name),
            likes=[
                UserBasic(id=like.user.id, name=like.user.name) for like in tweet.likes
            ],
        )


class TweetResponse(BasicResponse):
    """Tweet creation response schema."""

    model_config = ConfigDict(from_attributes=True)
    tweet_id: int


class TweetFeed(BasicResponse):
    """Tweet feed response schema."""

    tweets: List[TweetInfo] = []

    @classmethod
    def create(cls, tweets: List[Tweet]) -> "TweetFeed":
        """Create TweetFeed from list of tweets."""
        return cls(tweets=[TweetInfo.from_orm(tweet) for tweet in tweets])


class MediaResponse(BasicResponse):
    """Media upload response schema."""

    model_config = ConfigDict(from_attributes=True)
    media_id: int


class UserBasic(BaseModel):
    """Basic user information schema."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserFollowings(BaseModel):
    """User with followers and following schema."""

    id: int
    name: str
    followers: List[UserBasic] = []
    following: List[UserBasic] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    async def from_orm_async(cls, user: User) -> "UserFollowings":
        """Create UserFollowings from ORM model asynchronously."""
        followers = await user.awaitable_attrs.followers
        following = await user.awaitable_attrs.following
        return cls(
            id=user.id,
            name=user.name,
            followers=[UserBasic(id=f.id, name=f.name) for f in followers],
            following=[UserBasic(id=f.id, name=f.name) for f in following],
        )


class UserResponse(BasicResponse):
    """User information response schema."""

    user: UserFollowings

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    async def create(cls, user: User) -> "UserResponse":
        """Create UserResponse from ORM model."""
        user_info = await UserFollowings.from_orm_async(user)
        return cls(result=True, user=user_info)
