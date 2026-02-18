"""
Medias router module for the Corporate Microblog API.
Handles media file uploads and management.
"""

from fastapi import APIRouter, Depends

from app.dependencies import upload_media
from app.schemas import MediaResponse

router = APIRouter(prefix="/api/medias", tags=["medias"])


@router.post("/", response_model=MediaResponse)
async def upload_media_file(media_id: int = Depends(upload_media)) -> MediaResponse:
    """Upload media file and return media_id for attaching to tweets."""
    return MediaResponse(result=True, media_id=media_id)
