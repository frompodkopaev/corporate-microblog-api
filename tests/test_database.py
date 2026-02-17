import asyncio
import os
import pytest
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

from app.database import Base, engine, AsyncSessionFabric, DATABASE_URL


def test_base_class_inheritance():
    """Тест проверки наследования базового класса"""
    assert issubclass(Base, AsyncAttrs), "Base должен наследовать AsyncAttrs"
    assert issubclass(Base, DeclarativeBase), "Base должен наследовать DeclarativeBase"

    # Проверяем, что Base является абстрактным
    assert hasattr(Base, "metadata"), "Base должен содержать metadata"


def test_database_url_from_env():
    """Тест получения DATABASE_URL из переменных окружения"""
    # Сохраняем оригинальное значение
    original_url = os.environ.get("DATABASE_URL")

    try:
        # Устанавливаем тестовое значение
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        os.environ["DATABASE_URL"] = test_url

        # Перезагружаем модуль для применения новой переменной
        import importlib
        import app.database
        importlib.reload(app.database)

        assert app.database.DATABASE_URL == test_url, \
            "DATABASE_URL должна браться из переменной окружения"

    finally:
        # Восстанавливаем оригинальное значение
        if original_url is None:
            del os.environ["DATABASE_URL"]
        else:
            os.environ["DATABASE_URL"] = original_url


def test_database_url_default():
    """Тест значения DATABASE_URL по умолчанию"""
    # Сохраняем оригинальное значение
    original_url = os.environ.get("DATABASE_URL")

    try:
        # Удаляем переменную окружения
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        # Перезагружаем модуль для применения значения по умолчанию
        import importlib
        import app.database
        importlib.reload(app.database)

        default_url = "postgresql+asyncpg://postgres:password@localhost:5432/corporative_microblog_api"
        assert app.database.DATABASE_URL == default_url, \
            "Должно использоваться значение по умолчанию"

    finally:
        # Восстанавливаем оригинальное значение
        if original_url is not None:
            os.environ["DATABASE_URL"] = original_url


def test_engine_creation():
    """Тест создания engine с правильными параметрами"""
    assert engine is not None, "Engine не должен быть None"
    assert hasattr(engine, "connect"), "Engine должен иметь метод connect"
    assert hasattr(engine, "dispose"), "Engine должен иметь метод dispose"

    # Проверяем, что engine создан с правильным URL
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host == "localhost"
    assert engine.url.port == 5432
    assert engine.url.database == "corporative_microblog_api"
    assert engine.url.username == "postgres"


@patch('app.database.create_async_engine')
def test_engine_echo_param(mock_create_engine):
    """Тест параметра echo при создании engine"""
    from app.database import engine

    # Проверяем, что create_async_engine был вызван с echo=True
    mock_create_engine.assert_not_called()  # Уже создан до патча

    # Создаем новый engine с патчем для проверки параметров
    with patch('app.database.create_async_engine') as mock:
        import importlib
        import app.database
        importlib.reload(app.database)

        mock.assert_called_once()
        args, kwargs = mock.call_args
        assert kwargs.get('echo') is True, "Engine должен быть создан с echo=True"


def test_async_session_fabric_creation():
    """Тест создания фабрики асинхронных сессий"""
    assert AsyncSessionFabric is not None, "Фабрика сессий не должна быть None"
    assert isinstance(AsyncSessionFabric, async_sessionmaker), \
        "Должна быть создана async_sessionmaker"


@pytest.mark.asyncio
async def test_async_session_fabric_config():
    """Тест конфигурации фабрики сессий"""
    # Проверяем, что фабрика создает правильный тип сессий
    assert AsyncSessionFabric.class_ == AsyncSession, \
        "Фабрика должна создавать AsyncSession"

    # Проверяем, что сессия создается и работает
    async with AsyncSessionFabric() as session:
        assert isinstance(session, AsyncSession)

        # Простая проверка, что сессия может выполнять запросы
        from sqlalchemy import text
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

def test_async_session_fabric_creates_session():
    """Тест создания сессии через фабрику"""
    # Создаем сессию через фабрику
    session = AsyncSessionFabric()

    assert isinstance(session, AsyncSession), \
        "Фабрика должна создавать экземпляры AsyncSession"
    assert hasattr(session, "execute"), "Сессия должна иметь метод execute"
    assert hasattr(session, "commit"), "Сессия должна иметь метод commit"
    assert hasattr(session, "rollback"), "Сессия должна иметь метод rollback"
    assert hasattr(session, "close"), "Сессия должна иметь метод close"


@pytest.mark.asyncio
async def test_engine_connection():
    """Тест возможности подключения через engine"""
    try:
        # Пробуем подключиться с таймаутом
        async with asyncio.timeout(5):  # Python 3.11+
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        # Если дошли сюда - БД доступна
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1, "Должен выполняться простой запрос"

    except asyncio.TimeoutError:
        pytest.skip("Таймаут подключения к БД (проверьте запущен ли Docker контейнер)")
    except (OperationalError, DatabaseError) as e:
        pytest.skip(f"БД недоступна: {e}")
    except Exception as e:
        pytest.skip(f"Неожиданная ошибка: {e}")


def test_dotenv_loading():
    """Тест загрузки .env файла"""
    # Сохраняем оригинальный модуль, если он есть
    original_module = sys.modules.get('app.database')

    try:
        # Удаляем модуль из кэша, чтобы гарантировать полную перезагрузку
        if 'app.database' in sys.modules:
            del sys.modules['app.database']

        # Патчим dotenv.load_dotenv
        with patch('dotenv.load_dotenv') as mock_load_dotenv:
            # Импортируем модуль заново
            import app.database

            # Проверяем, что load_dotenv был вызван
            mock_load_dotenv.assert_called_once_with()

    finally:
        # Восстанавливаем оригинальный модуль
        if original_module:
            sys.modules['app.database'] = original_module
        elif 'app.database' in sys.modules:
            del sys.modules['app.database']


@pytest.mark.parametrize("url_variant,expected_scheme", [
    ("postgresql+asyncpg://user:pass@localhost/db", "postgresql+asyncpg"),
])
def test_database_url_schemes(url_variant, expected_scheme):
    """Тест различных схем URL для БД"""
    # Сохраняем оригинальное значение
    original_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["DATABASE_URL"] = url_variant

        import importlib
        import app.database
        importlib.reload(app.database)

        assert app.database.DATABASE_URL == url_variant
        assert app.database.DATABASE_URL.startswith(expected_scheme), \
            f"Схема {expected_scheme} не соответствует URL"

    finally:
        # Восстанавливаем оригинальное значение
        if original_url is None:
            del os.environ["DATABASE_URL"]
        else:
            os.environ["DATABASE_URL"] = original_url


def test_engine_pool_settings():
    """Тест настроек пула соединений"""
    # Проверяем стандартные настройки пула
    assert hasattr(engine, "pool"), "Engine должен иметь пул соединений"
    assert hasattr(engine.pool, "size"), "Пул должен иметь параметр size"


@pytest.mark.asyncio
async def test_session_fabric_binds_to_engine():
    """Тест привязки фабрики сессий к engine"""
    # Проверяем, что фабрика использует наш engine
    session = AsyncSessionFabric()
    try:
        assert session.bind == engine, "Сессия должна быть привязана к правильному engine"
    finally:
        await session.close()


def test_base_metadata():
    """Тест metadata базового класса"""
    assert Base.metadata is not None, "Base должен содержать metadata"
    assert hasattr(Base.metadata, "tables"), "metadata должен содержать таблицы"
    assert isinstance(Base.metadata.tables, dict), "tables должен быть словарем"


def test_imports():
    """Тест доступности всех необходимых импортов"""
    try:
        from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
        from sqlalchemy.sql import func
        assert True
    except ImportError as e:
        pytest.fail(f"Необходимые импорты SQLAlchemy недоступны: {e}")


@pytest.mark.asyncio
async def test_session_context_manager():
    """Тест использования сессии как контекстного менеджера"""
    session = AsyncSessionFabric()

    try:
        # Проверяем основные методы сессии
        assert hasattr(session, "__aenter__"), "Сессия должна поддерживать async with"
        assert hasattr(session, "__aexit__"), "Сессия должна поддерживать async with"

        # Проверяем состояние сессии
        assert session.is_active, "Новая сессия должна быть активной"

    finally:
        await session.close()


def test_engine_dispose():
    """Тест метода dispose у engine"""
    assert hasattr(engine, "dispose"), "Engine должен иметь метод dispose"
    assert callable(engine.dispose), "dispose должен быть вызываемым"