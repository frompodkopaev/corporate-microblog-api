from fastapi import FastAPI

from contextlib import asynccontextmanager

from app.dependencies import init_db, close_db
from app.routes import users, tweets, medias


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="Corporative microblog API",
    lifespan=lifespan
)

app.include_router(users.router)
app.include_router(tweets.router)
app.include_router(medias.router)