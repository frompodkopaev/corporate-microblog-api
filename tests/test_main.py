import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app, lifespan
from app.core.exceptions import AppException


def test_app_creation():
    """Тест создания приложения FastAPI"""
    assert isinstance(app, FastAPI)
    assert app.title == "Corporative microblog API"


def test_routers_included():
    """Тест подключения всех роутеров"""
    routes_paths = [route.path for route in app.routes]

    # Проверяем, что все ожидаемые пути присутствуют
    expected_paths = [
        "/api/users",
        "/api/tweets",
        "/api/medias"
    ]

    for expected_path in expected_paths:
        assert any(route.startswith(expected_path) for route in routes_paths), \
            f"Роутер для пути {expected_path} не найден"


def test_exception_handlers_registered():
    """Тест регистрации всех обработчиков исключений"""
    exception_handlers = app.exception_handlers

    # Проверяем, что для каждого типа исключений зарегистрирован обработчик
    expected_exceptions = [
        RequestValidationError,
        SQLAlchemyError,
        AppException,
        HTTPException,
        Exception
    ]

    for exception_type in expected_exceptions:
        assert exception_type in exception_handlers, \
            f"Обработчик для {exception_type.__name__} не зарегистрирован"


@pytest.mark.asyncio
async def test_lifespan_success():
    """Тест успешной работы lifespan"""
    mock_app = MagicMock(spec=FastAPI)

    with patch('app.main.init_db', new_callable=AsyncMock) as mock_init_db, \
            patch('app.main.close_db', new_callable=AsyncMock) as mock_close_db:
        # Проверяем вход в контекст
        async with lifespan(mock_app) as result:
            mock_init_db.assert_awaited_once()
            assert result is None  # lifespan не должен ничего возвращать

        # Проверяем выход из контекста
        mock_close_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_init_db_failure():
    """Тест ошибки при инициализации БД"""
    mock_app = MagicMock(spec=FastAPI)

    with patch('app.main.init_db', new_callable=AsyncMock) as mock_init_db:
        mock_init_db.side_effect = Exception("DB init error")

        # Проверяем, что исключение пробрасывается наружу
        with pytest.raises(Exception, match="DB init error"):
            async with lifespan(mock_app):
                pass


@pytest.mark.asyncio
async def test_lifespan_close_db_failure():
    """Тест ошибки при закрытии БД"""
    mock_app = MagicMock(spec=FastAPI)

    with patch('app.main.init_db', new_callable=AsyncMock) as mock_init_db, \
            patch('app.main.close_db', new_callable=AsyncMock) as mock_close_db:
        mock_close_db.side_effect = Exception("DB close error")

        # Исключение при закрытии должно пробрасываться после yield
        with pytest.raises(Exception, match="DB close error"):
            async with lifespan(mock_app):
                pass

        mock_init_db.assert_awaited_once()


def test_imports_exist():
    """Тест проверки наличия всех импортируемых модулей"""
    try:
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
        assert True
    except ImportError as e:
        pytest.fail(f"Ошибка импорта: {e}")


@pytest.mark.parametrize("exception_handler", [
    "app_exception_handler",
    "python_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "sqlalchemy_exception_handler"
])
def test_error_handlers_are_functions(exception_handler):
    """Тест проверки, что обработчики ошибок являются функциями"""
    from app.core import error_handlers

    handler = getattr(error_handlers, exception_handler, None)
    assert handler is not None, f"Обработчик {exception_handler} не найден"
    assert callable(handler), f"{exception_handler} должен быть вызываемым"


def test_router_prefixes():
    """Тест проверки префиксов роутеров"""
    # Получаем все зарегистрированные пути
    route_paths = [route.path for route in app.routes if hasattr(route, 'path')]

    # Проверяем, что роутеры зарегистрированы с правильными базовыми путями
    assert any(path.startswith("/api/users") for path in route_paths), "Роутер users не зарегистрирован"
    assert any(path.startswith("/api/tweets") for path in route_paths), "Роутер tweets не зарегистрирован"
    assert any(path.startswith("/api/medias") for path in route_paths), "Роутер medias не зарегистрирован"


def test_app_configuration():
    """Тест дополнительных конфигураций приложения"""
    assert app.debug is False, "Приложение должно быть в production режиме"
    assert app.docs_url == "/docs", "Документация должна быть доступна"
    assert app.redoc_url == "/redoc", "ReDoc должна быть доступна"
    assert app.openapi_url == "/openapi.json", "OpenAPI схема должна быть доступна"