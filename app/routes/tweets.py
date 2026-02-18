"""
Tweets router module for the Corporate Microblog API.
Handles all tweet-related endpoints including creation, deletion, and interactions.
"""

from typing import List
from fastapi import APIRouter, Depends
from app.schemas import BasicResponse, TweetResponse, TweetFeed
from app.dependencies import create_tweet, delete_tweet, like_tweet, unlike_tweet, get_user_feed
from app.models import Tweet

router = APIRouter(prefix="/api/tweets", tags=["tweets"])


@router.get("/", response_model=TweetFeed)
async def show_tweets(
        tweets: List[Tweet] = Depends(get_user_feed)
) -> TweetFeed:
    """Get tweet feed for current user."""
    return TweetFeed.create(tweets=tweets)


@router.post("/", response_model=TweetResponse)
async def create_new_tweet(
        tweet_id: int = Depends(create_tweet)
) -> TweetResponse:
    """Create a new tweet."""
    return TweetResponse(result=True, tweet_id=tweet_id)


@router.delete("/{tweet_id}", response_model=BasicResponse)
async def delete_tweet_by_id(
        result: bool = Depends(delete_tweet)
) -> BasicResponse:
    """Delete a tweet by ID."""
    return BasicResponse(result=result)


@router.post("/{tweet_id}/likes", response_model=BasicResponse)
async def like_tweet_by_id(
        result: bool = Depends(like_tweet)
) -> BasicResponse:
    """Like a tweet by ID."""
    return BasicResponse(result=result)


@router.delete("/{tweet_id}/likes", response_model=BasicResponse)
async def unlike_tweet_by_id(
        result: bool = Depends(unlike_tweet)
) -> BasicResponse:
    """Unlike a tweet by ID."""
    return BasicResponse(result=result)