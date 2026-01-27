from typing import Dict, Optional

from aiofiles import open as aio_open
from fastapi import Depends, Header, FastAPI, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import get_db, User, ApiKey

app = FastAPI()


async def get_api_key(api_key: Optional[str] = Header(None, alias="api-key")) -> Optional[str]:
    if api_key:
        return api_key
    return None

@app.get("/hello-world")
async def hello_world() -> Dict[str, str]:
    return {"message": "Hello world!"}


@app.post("/api/medias")
async def upload_file(file: UploadFile) -> Dict[str, str]:
    name_of_file = file.filename
    content = await file.read(-1)
    async with aio_open(f"{name_of_file}", mode='wb') as f:
        await f.write(content)
    return {"result": "True", "media_id": f"{file.filename}"}