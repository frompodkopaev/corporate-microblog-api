import json
import pytest
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, DataError
from unittest.mock import Mock, AsyncMock, MagicMock

from app.core.exceptions import (
    AppException,
    BusinessLogicException,
    UnauthorizedException,
    NotFoundException,
    ConflictException
)
from app.core.error_handlers import (
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    python_exception_handler,
    http_exception_handler
)


@pytest.fixture
def mock_request():
    """Фикстура для мок-запроса"""
    request = AsyncMock(spec=Request)
    request.app.state.debug = False
    return request


class TestAppExceptionHandler:
    """Тесты для обработчика AppException"""

    @pytest.mark.asyncio
    async def test_handle_app_exception(self, mock_request):
        """Тест обработки AppException"""
        exc = BusinessLogicException("Test error")
        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.body is not None

        # Проверяем содержимое ответа (без пробелов)
        content = response.body.decode()
        assert '"result":false' in content
        assert '"error_type":"BUSINESS_LOGIC_ERROR"'in content
        assert '"error_message":"Test error"' in content

    @pytest.mark.asyncio
    async def test_handle_non_app_exception(self, mock_request):
        """Тест обработки не-AppException"""
        exc = ValueError("Some error")
        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = response.body.decode()
        assert '"error_type":"INTERNAL_SERVER_ERROR"' in content
        assert '"error_message":"Some error"' in content

    @pytest.mark.asyncio
    async def test_handle_unauthorized_with_headers(self, mock_request):
        """Тест обработки UnauthorizedException с заголовками"""
        exc = UnauthorizedException()
        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers.get("www-authenticate") == "Bearer"


class TestValidationExceptionHandler:
    """Тесты для обработчика validation ошибок"""

    @pytest.mark.asyncio
    async def test_handle_request_validation_error(self, mock_request):
        """Тест обработки RequestValidationError"""
        # Создаем мок ошибки валидации
        mock_error = Mock(spec=RequestValidationError)
        mock_error.errors.return_value = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]

        response = await validation_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = response.body.decode()
        assert '"error_type":"VALIDATION_ERROR"' in content
        assert "field required" in content

    @pytest.mark.asyncio
    async def test_handle_pydantic_validation_error(self, mock_request):
        """Тест обработки Pydantic ValidationError"""
        mock_error = Mock(spec=ValidationError)
        mock_error.errors.return_value = [
            {
                "loc": ("email",),
                "msg": "value is not a valid email",
                "type": "value_error.email"
            }
        ]

        response = await validation_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = response.body.decode()
        assert "value is not a valid email" in content

    @pytest.mark.asyncio
    async def test_handle_non_validation_error(self, mock_request):
        """Тест обработки не-validation ошибки"""
        exc = ValueError("Some error")
        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = response.body.decode()
        assert "Some error" in content


class TestSQLAlchemyExceptionHandler:
    """Тесты для обработчика SQLAlchemy ошибок"""

    @pytest.mark.asyncio
    async def test_handle_integrity_error_unique(self, mock_request):
        """Тест обработки IntegrityError (unique constraint)"""
        from app.core.error_handlers import sqlalchemy_exception_handler

        mock_error = MagicMock(spec=IntegrityError)

        # Создаем orig, который при преобразовании в строку даст нужное сообщение
        mock_orig = MagicMock()
        # Важно: str(mock_orig) должно возвращать нужную строку
        mock_orig.__str__.return_value = "duplicate key value violates unique constraint"
        mock_error.orig = mock_orig

        mock_error.statement = "INSERT INTO users ..."
        mock_error.params = {}

        response = await sqlalchemy_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_409_CONFLICT

        data = json.loads(response.body)
        assert data["result"] is False
        assert data["error_type"] == "INTEGRITY_ERROR"
        assert data["error_message"] == "Resource already exists"

    @pytest.mark.asyncio
    async def test_handle_integrity_error_foreign_key(self, mock_request):
        """Тест обработки IntegrityError (foreign key)"""
        from app.core.error_handlers import sqlalchemy_exception_handler
        from sqlalchemy.exc import IntegrityError
        from unittest.mock import MagicMock
        import json

        mock_error = MagicMock(spec=IntegrityError)
        # Используем реальный Exception с нужным сообщением
        mock_error.orig = Exception("foreign key constraint violation")
        mock_error.statement = "INSERT INTO users ..."
        mock_error.params = {}

        response = await sqlalchemy_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_409_CONFLICT

        data = json.loads(response.body)
        assert data["result"] is False
        assert data["error_type"] == "INTEGRITY_ERROR"
        assert data["error_message"] == "Referenced resource does not exist"

    @pytest.mark.asyncio
    async def test_handle_data_error(self, mock_request):
        """Тест обработки DataError"""
        mock_error = Mock(spec=DataError)

        response = await sqlalchemy_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.body.decode()
        assert '"error_type":"DATA_ERROR"' in content
        assert '"error_message":"Invalid data format"' in content

    @pytest.mark.asyncio
    async def test_handle_other_sqlalchemy_error(self, mock_request):
        """Тест обработки других SQLAlchemy ошибок"""
        mock_error = Exception("Some other error")

        response = await sqlalchemy_exception_handler(mock_request, mock_error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = response.body.decode()
        assert '"error_type":"DATABASE_ERROR"' in content


class TestPythonExceptionHandler:
    """Тесты для обработчика Python исключений"""

    @pytest.mark.asyncio
    async def test_handle_exception_production(self, mock_request):
        """Тест обработки в production режиме"""
        exc = ValueError("Something went wrong")
        response = await python_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = response.body.decode()
        assert '"error_message":"Internal server error"' in content

    @pytest.mark.asyncio
    async def test_handle_exception_debug(self, mock_request):
        """Тест обработки в debug режиме"""
        mock_request.app.state.debug = True
        exc = ValueError("Something went wrong")

        response = await python_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = response.body.decode()
        assert "ValueError: Something went wrong" in content


class TestHTTPExceptionHandler:
    """Тесты для обработчика HTTPException"""

    @pytest.mark.asyncio
    async def test_handle_http_exception(self, mock_request):
        """Тест обработки HTTPException"""
        from fastapi import HTTPException

        exc = HTTPException(
            status_code=404,
            detail="Not found"
        )

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        content = response.body.decode()
        assert '"error_type":"HTTP_ERROR"' in content
        assert '"error_message":"Not found"' in content

    @pytest.mark.asyncio
    async def test_handle_non_http_exception(self, mock_request):
        """Тест обработки не-HttpException"""
        exc = ValueError("Some error")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 500
        content = response.body.decode()
        assert "Some error" in content