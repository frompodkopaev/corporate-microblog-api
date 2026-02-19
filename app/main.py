from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.dependencies import close_db, init_db
from app.routes import medias, tweets, users

BASE_DIR = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    (BASE_DIR / "uploads").mkdir(exist_ok=True)
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(users.router)
app.include_router(tweets.router)
app.include_router(medias.router)

app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"))
app.mount("/css", StaticFiles(directory=BASE_DIR / "frontend" / "css"))
app.mount("/js", StaticFiles(directory=BASE_DIR / "frontend" / "js"))


@app.get("/{full_path:path}")
@app.get("/")
async def spa():
    return FileResponse(BASE_DIR / "frontend" / "index.html")