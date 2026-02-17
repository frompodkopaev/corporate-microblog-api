import pytest
from fastapi import status
from app.core.exceptions import (
    AppException,
    BusinessLogicException,
    UnauthorizedException,
    InsufficientPermissionsException,
    NotFoundException,
    ConflictException,
    ValidationException,
    InternalServerErrorException,
    DatabaseException
)


class TestAppException:
    """Тесты для базового класса исключений"""

    def test_app_exception_creation(self):
        """Тест создания базового исключения"""
        exc = AppException(
            status_code=400,
            error_type="TEST_ERROR",
            error_message="Test message"
        )

        assert exc.status_code == 400
        assert exc.error_type == "TEST_ERROR"
        assert exc.error_message == "Test message"
        assert exc.detail == {
            "result": False,
            "error_type": "TEST_ERROR",
            "error_message": "Test message"
        }
        assert exc.headers is None

    def test_app_exception_with_headers(self):
        """Тест создания исключения с заголовками"""
        exc = AppException(
            status_code=401,
            error_type="UNAUTHORIZED",
            error_message="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"}
        )

        assert exc.headers == {"WWW-Authenticate": "Bearer"}


class TestBusinessLogicException:
    """Тесты для BusinessLogicException"""

    def test_default_creation(self):
        """Тест создания с сообщением по умолчанию"""
        exc = BusinessLogicException("Invalid operation")

        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.error_type == "BUSINESS_LOGIC_ERROR"
        assert exc.error_message == "Invalid operation"

    def test_custom_status_code(self):
        """Тест создания с кастомным статус-кодом"""
        exc = BusinessLogicException(
            "Custom error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.error_message == "Custom error"


class TestUnauthorizedException:
    """Тесты для UnauthorizedException"""

    def test_default_message(self):
        """Тест создания с сообщением по умолчанию"""
        exc = UnauthorizedException()

        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.error_type == "UNAUTHORIZED"
        assert exc.error_message == "Unauthorized"
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_custom_message(self):
        """Тест создания с кастомным сообщением"""
        exc = UnauthorizedException("Invalid token")

        assert exc.error_message == "Invalid token"


class TestInsufficientPermissionsException:
    """Тесты для InsufficientPermissionsException"""

    def test_default_message(self):
        exc = InsufficientPermissionsException()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.error_type == "INSUFFICIENT_PERMISSIONS"
        assert exc.error_message == "Insufficient permissions"

    def test_custom_message(self):
        exc = InsufficientPermissionsException("Admin access required")
        assert exc.error_message == "Admin access required"


class TestNotFoundException:
    """Тесты для NotFoundException"""

    def test_without_id(self):
        exc = NotFoundException("User")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.error_type == "NOT_FOUND"
        assert exc.error_message == "User not found"

    def test_with_id(self):
        exc = NotFoundException("User", 123)
        assert exc.error_message == "User not found with id: 123"

    def test_with_string_id(self):
        exc = NotFoundException("Tweet", "abc-123")
        assert exc.error_message == "Tweet not found with id: abc-123"


class TestConflictException:
    """Тесты для ConflictException"""

    def test_default_message(self):
        exc = ConflictException()
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.error_type == "CONFLICT"
        assert exc.error_message == "Resource already exists"

    def test_custom_message(self):
        exc = ConflictException("User already followed")
        assert exc.error_message == "User already followed"


class TestValidationException:
    """Тесты для ValidationException"""

    def test_default_message(self):
        exc = ValidationException()
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.error_type == "VALIDATION_ERROR"
        assert exc.error_message == "Validation error"

    def test_custom_message(self):
        exc = ValidationException("Invalid email format")
        assert exc.error_message == "Invalid email format"


class TestInternalServerErrorException:
    """Тесты для InternalServerErrorException"""

    def test_default_message(self):
        exc = InternalServerErrorException()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.error_type == "INTERNAL_SERVER_ERROR"
        assert exc.error_message == "Internal server error"


class TestDatabaseException:
    """Тесты для DatabaseException"""

    def test_default_message(self):
        exc = DatabaseException()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.error_type == "DATABASE_ERROR"
        assert exc.error_message == "Database error"