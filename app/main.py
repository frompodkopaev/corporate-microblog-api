"""
Main application module for the Corporate Microblog API.
Configures FastAPI application, exception handlers, and lifecycle management.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from contextlib import asynccontextmanager

from app.dependencies import init_db, close_db
from app.routes import users, tweets, medias
from app.core.exceptions import AppException
from app.core.error_handlers import (
    app_exception_handler,
    python_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Corporative microblog API",
    lifespan=lifespan
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, python_exception_handler)

app.include_router(users.router)
app.include_router(tweets.router)
app.include_router(medias.router)