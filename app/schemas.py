from pydantic import BaseModel, ConfigDict
from typing import List

from app import User


class UserFollower(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class UserInfo(BaseModel):
    id: int
    name: str
    followers: List[UserFollower] = []
    following: List[UserFollower] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, user: User) -> "UserInfo":
        return cls(
            id=user.id,
            name=user.name,
            followers=[
                UserFollower(id=f.id, name=f.name)
                for f in user.followers
            ],
            following=[
                UserFollower(id=f.id, name=f.name)
                for f in user.following
            ]
        )