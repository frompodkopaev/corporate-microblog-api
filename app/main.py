from typing import Dict, Optional

from aiofiles import open as aio_open
from fastapi import FastAPI, UploadFile

from contextlib import asynccontextmanager

from app import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="Corporative microblog API",
    lifespan=lifespan
)


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