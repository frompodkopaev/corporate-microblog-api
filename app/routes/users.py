from fastapi import APIRouter, Depends
from app import authenticate_user, UserResponse, User

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User= Depends(authenticate_user)):
    return await UserResponse.create(user)