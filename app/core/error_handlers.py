from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, DataError
from pydantic import ValidationError

from app.core.exceptions import AppException

async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for inner app exceptions
    """
    if isinstance(exc, AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "result": False,
                "error_type": exc.error_type,
                "error_message": exc.error_message
            },
            headers=exc.headers
        )
    else:
        error_message = str(exc)
        error_type = "INTERNAL_SERVER_ERROR"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "result": False,
                "error_type": error_type,
                "error_message": error_message
            }
        )


async def validation_exception_handler(
        request: Request,
        exc: Exception
) -> JSONResponse:
    """
    Handler for Pydantic/FastAPI errors
    """
    if isinstance(exc, (RequestValidationError, ValidationError)):
        error_message = "|".join(
            [":".join(
                [" -> ".join(str(x) for x in error["loc"]),
                error["msg"]]
                )
                for error in exc.errors()
            ]
        )
    else:
        error_message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "result": False,
            "error_type": "VALIDATION_ERROR",
            "error_message": error_message
        }
    )


async def sqlalchemy_exception_handler(
        request: Request,
        exc: Exception
) -> JSONResponse:
    """
    Handler for SQLAlchemy errors
    """

    if isinstance(exc, IntegrityError):
        error_type = "INTEGRITY_ERROR"
        status_code = status.HTTP_409_CONFLICT
        message = "Data integrity violation"
        error_str = str(exc.orig)
        if "unique constraint" in error_str.lower():
            message = "Resource already exists"
        elif "foreign key constraint" in error_str.lower():
            message = "Referenced resource does not exist"

    elif isinstance(exc, DataError):
        error_type = "DATA_ERROR"
        status_code = status.HTTP_400_BAD_REQUEST
        message = "Invalid data format"
    else:
        error_type = "DATABASE_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Database error occurred"

    return JSONResponse(
        status_code=status_code,
        content={
            "result": False,
            "error_type": error_type,
            "error_message": message
        }
    )


async def python_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for Python exception
    """

    error_message = "Internal server error"
    if getattr(request.app.state, "debug", False):
        error_message = f"{type(exc).__name__}: {str(exc)}"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "result": False,
            "error_type": "INTERNAL_SERVER_ERROR",
            "error_message": error_message
        }
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for HTTPException
    """

    return JSONResponse(
        status_code=exc.status_code if hasattr(exc, 'status_code') else 500,
        content={
            "result": False,
            "error_type": "HTTP_ERROR",
            "error_message": exc.detail if hasattr(exc, 'detail') else str(exc)
        }
    )