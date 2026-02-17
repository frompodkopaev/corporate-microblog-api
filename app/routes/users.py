from fastapi import APIRouter, Depends
from app.schemas import UserResponse, BasicResponse
from app.dependencies import follow_user, unfollow_user, get_user_by_id, get_current_user
from app.models import User

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User= Depends(get_current_user)) -> UserResponse:
    return await UserResponse.create(user)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_info_by_id(
        user_id: int,
        user: User= Depends(get_user_by_id)
) -> UserResponse:
    return await UserResponse.create(user)

@router.post("/{user_id}/follow", response_model=BasicResponse)
async def follow_user_by_id(
        user_id: int,
        result: bool = Depends(follow_user)
) -> BasicResponse:
    return BasicResponse(result=result)


@router.delete("/{user_id}/follow", response_model=BasicResponse)
async def unfollow_user_by_id(
        user_id: int,
        result: bool = Depends(unfollow_user)
) -> BasicResponse:
    return BasicResponse(result=result)