from fastapi import APIRouter, Depends, UploadFile
from app import MediaResponse, upload_media

router = APIRouter(prefix="/api/medias", tags=["medias"])


@router.post("/", response_model=MediaResponse)
async def upload_media_file(
        media_id:int = Depends(upload_media)
) -> MediaResponse:
    """
    Upload media file

    Returns media_id for attaching to tweets
    """
    return MediaResponse(
        result=True,
        media_id=media_id
    )