"""
Custom exception classes for the Corporate Microblog API.
All exceptions inherit from AppException base class.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base class for app exceptions."""

    def __init__(
        self,
        status_code: int,
        error_type: str,
        error_message: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize base app exception."""
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(
            status_code=status_code,
            detail={
                "result": False,
                "error_type": error_type,
                "error_message": error_message,
            },
            headers=headers,
        )


class BusinessLogicException(AppException):
    """400 Bad request exception for business logic violations."""

    def __init__(
        self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> None:
        """Initialize business logic exception."""
        super().__init__(
            status_code=status_code,
            error_type="BUSINESS_LOGIC_ERROR",
            error_message=message,
        )


class UnauthorizedException(AppException):
    """401 Unauthorized exception for authentication failures."""

    def __init__(self, message: str = "Unauthorized") -> None:
        """Initialize unauthorized exception."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="UNAUTHORIZED",
            error_message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientPermissionsException(AppException):
    """403 Insufficient permissions exception."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        """Initialize insufficient permissions exception."""
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_type="INSUFFICIENT_PERMISSIONS",
            error_message=message,
        )


class NotFoundException(AppException):
    """404 Not Found exception."""

    def __init__(self, entity: str, entity_id: Any = None) -> None:
        """Initialize not found exception."""
        message = f"{entity} not found"
        if entity_id:
            message += f" with id: {entity_id}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="NOT_FOUND",
            error_message=message,
        )


class ConflictException(AppException):
    """409 Conflict exception for duplicate operations."""

    def __init__(self, message: str = "Resource already exists") -> None:
        """Initialize conflict exception."""
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_type="CONFLICT",
            error_message=message,
        )


class ValidationException(AppException):
    """422 Unprocessable Entity exception for validation errors."""

    def __init__(self, message: str = "Validation error") -> None:
        """Initialize validation exception."""
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="VALIDATION_ERROR",
            error_message=message,
        )


class InternalServerErrorException(AppException):
    """500 Internal Server Error exception."""

    def __init__(self, message: str = "Internal server error") -> None:
        """Initialize internal server error exception."""
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="INTERNAL_SERVER_ERROR",
            error_message=message,
        )


class DatabaseException(AppException):
    """Database Error exception."""

    def __init__(self, message: str = "Database error") -> None:
        """Initialize database exception."""
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="DATABASE_ERROR",
            error_message=message,
        )
