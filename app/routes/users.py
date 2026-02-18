"""
Users router module for the Corporate Microblog API.
Handles all user-related endpoints including profile retrieval and follow operations.
"""

from fastapi import APIRouter, Depends

from app.dependencies import (
    follow_user,
    get_current_user,
    get_user_by_id,
    unfollow_user,
)
from app.models import User
from app.schemas import BasicResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)) -> UserResponse:
    """Get information about the currently authenticated user."""
    return await UserResponse.create(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_info_by_id(
    user_id: int, user: User = Depends(get_user_by_id)
) -> UserResponse:
    """Get user information by ID."""
    return await UserResponse.create(user)


@router.post("/{user_id}/follow", response_model=BasicResponse)
async def follow_user_by_id(
    user_id: int, result: bool = Depends(follow_user)
) -> BasicResponse:
    """Follow a user by ID."""
    return BasicResponse(result=result)


@router.delete("/{user_id}/follow", response_model=BasicResponse)
async def unfollow_user_by_id(
    user_id: int, result: bool = Depends(unfollow_user)
) -> BasicResponse:
    """Unfollow a user by ID."""
    return BasicResponse(result=result)
