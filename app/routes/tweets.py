from typing import List
from fastapi import APIRouter, Depends
from app import BasicResponse, TweetResponse, create_tweet, delete_tweet, like_tweet, unlike_tweet, TweetFeed, Tweet, get_user_feed

router = APIRouter(prefix="/api/tweets",tags=["tweets"])

@router.get("/", response_model=TweetFeed)
async def show_tweets(
        tweets: List[Tweet] = Depends(get_user_feed)
) -> TweetFeed:
    return TweetFeed.create(tweets=tweets)

@router.post("/", response_model=TweetResponse)
async def create_new_tweet(
        tweet_id: int = Depends(create_tweet)
) -> TweetResponse:
    return TweetResponse(result=True, tweet_id=tweet_id)

@router.delete("/{id}", response_model=BasicResponse)
async def delete_tweet_by_id(
        result: bool = Depends(delete_tweet)
) -> BasicResponse:
    return BasicResponse(result=result)

@router.post("/{id}/likes", response_model=BasicResponse)
async def like_tweet_by_id(
        result: bool = Depends(like_tweet)
) -> BasicResponse:
    return BasicResponse(result=result)

@router.delete("/{id}/likes", response_model=BasicResponse)
async def unlike_tweet_by_id(
        result: bool = Depends(unlike_tweet)
) -> BasicResponse:
    return BasicResponse(result=result)