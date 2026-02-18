"""
Database models module for the Corporate Microblog API.
Defines SQLAlchemy ORM models with relationships and constraints.
"""

from sqlalchemy import String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import bcrypt

from app.database import Base


class User(Base):
    """Model for user."""
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
    """Model for follow relationships between users."""
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

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),
        Index("ix_follow_follower_following", "follower_id", "following_id"),
        Index("ix_follow_following_follower", "following_id", "follower_id"),
    )


class ApiKey(Base):
    """Model for API key."""
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
    def hash_key(key: str) -> str:
        """Hash an API key using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(key.encode(), salt).decode()

    def verify_key(self, key: str) -> bool:
        """Verify a raw API key against the stored hash."""
        return bcrypt.checkpw(key.encode(), self.key_hash.encode())

    __table_args__ = (
        Index("ix_apikey_user_prefix", "user_id", "key_prefix"),
    )


class Tweet(Base):
    """Model for tweets."""
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    likes_counter: Mapped[int] = mapped_column(default=0, index=True)

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
    """Model for media."""
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
    """Model for likes."""
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
        Index("ix_like_tweet_user", "tweet_id", "user_id"),
        Index("ix_like_user_tweet", "user_id", "tweet_id"),
    )