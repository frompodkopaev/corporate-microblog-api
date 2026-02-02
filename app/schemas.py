from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app import User, Tweet, Like


class BasicResponse(BaseModel):
    """Base response"""
    result: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    result: bool = False
    error_type: str
    error_message: str


class TweetCreate(BaseModel):
    """Tweet creation scheme"""
    tweet_data: str = Field(...,alias="content", min_length=1, max_length=1000)
    media_ids: Optional[List[int]] = Field(default_factory=list)


class TweetInfo(BaseModel):
    id: int
    content: str
    attachments: List[str] = []
    author: UserBasic
    likes: List[UserBasic] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, tweet: Tweet) -> TweetInfo:
        return cls(
            id=tweet.id,
            content=tweet.content,
            attachments=[m.link for m in tweet.media],
            author=UserBasic(id=tweet.author.id, name=tweet.author.name),
            likes=[
                UserBasic(id=l.user.id, name=l.user.name)
                for l in tweet.likes
            ]
        )


class TweetResponse(BasicResponse):
    model_config = ConfigDict(from_attributes=True)
    tweet_id: int


class MediaResponse(BasicResponse):
    model_config = ConfigDict(from_attributes=True)
    media_id: int = True

class UserBasic(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class UserFollowings(BaseModel):
    id: int
    name: str
    followers: List[UserBasic] = []
    following: List[UserBasic] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, user: User) -> "UserFollowings":
        return cls(
            id=user.id,
            name=user.name,
            followers=[
                UserBasic(id=f.id, name=f.name)
                for f in user.followers
            ],
            following=[
                UserBasic(id=f.id, name=f.name)
                for f in user.following
            ]
        )