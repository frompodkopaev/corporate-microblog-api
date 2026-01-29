from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import bcrypt

from app import Base


class User(Base):
    """ Model for user"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    followers: Mapped[list["User"]] = relationship(
        secondary="followings",
        primaryjoin="Follow.following_id == User.id",
        secondaryjoin="Follow.follower_id == User.id",
        back_populates="following",
        lazy="selectin",
        viewonly=True
    )
    following: Mapped[list["User"]] = relationship(
        secondary="followings",
        primaryjoin="Follow.follower_id == User.id",
        secondaryjoin="Follow.following_id == User.id",
        back_populates="followers",
        lazy="selectin",
        viewonly=True
    )

    follower_relationships: Mapped[list["Follow"]] = relationship(
        foreign_keys="[Follow.following_id]",
        back_populates="following_user",
        cascade="all, delete-orphan"
    )
    following_relationships: Mapped[list["Follow"]] = relationship(
        foreign_keys="[Follow.follower_id]",
        back_populates="follower_user",
        cascade="all, delete-orphan"
    )

    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    tweets: Mapped[list["Tweet"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    likes: Mapped[list["Like"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class Follow(Base):
    """Model for follow relationships between users"""
    __tablename__ = "followings"

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    follower_user: Mapped["User"] = relationship(
        foreign_keys=[following_id],
        back_populates="following_relationships"
    )
    following_user: Mapped["User"] = relationship(
        foreign_keys=[following_id],
        back_populates="follower_relationships"
    )

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following")
    )


class ApiKey(Base):
    """Model for API key"""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        unique=True,
        index=True
    )
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )

    user: Mapped["User"] = relationship(
        back_populates="api_keys",
        lazy="joined"
    )

    @staticmethod
    def hash_key(key:str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(key.encode(), salt).decode()

    def verify_key(self, key: str) -> bool:
        return bcrypt.checkpw(key.encode(), self.key_hash.encode())


class Tweet(Base):
    """Model fot tweets"""
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(String(1000), nullable=False)

    author: Mapped["User"] = relationship(back_populates="tweets")

    media: Mapped[list["Media"]] = relationship(
        back_populates="tweet",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    likes: Mapped[list["Like"]] = relationship(
        back_populates="tweet",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class Media(Base):
    """Model for media"""
    __tablename__ = "medias"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column(String(500), nullable=True)
    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    tweet: Mapped["Tweet"] = relationship(back_populates="media")


class Like(Base):
    """Model for likes"""
    __tablename__ = "likes"

    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    tweet: Mapped["Tweet"] = relationship(back_populates="likes")
    user: Mapped["User"] = relationship(back_populates="likes")

    __table_args__ = (
        UniqueConstraint('tweet_id', 'user_id', name='uq_like_tweet_user'),
    )
