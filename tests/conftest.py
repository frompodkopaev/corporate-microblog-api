import pytest
import asyncio
import asyncpg
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base
from fastapi.testclient import TestClient
from app.main import app

PROJECT_ROOT = Path(__file__).parent.parent
TEST_USERS_FILE = PROJECT_ROOT / "scripts" / "test_users.json"


def load_test_users():
    if TEST_USERS_FILE.exists():
        with open(TEST_USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


@pytest.fixture(scope="session")
def test_users_data():
    return load_test_users()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def event_loop():
    """Создает event loop для каждого теста"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


async def create_test_database():
    """Создает тестовую базу данных если она не существует"""
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password='password',
            host='localhost',
            port=5432,
            database='postgres'
        )

        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'test_db'"
        )

        if not exists:
            await conn.execute('CREATE DATABASE test_db')
            print("Created test_db database")
        else:
            print("test_db database already exists")

        await conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


@pytest.fixture(scope="function")
async def async_engine(event_loop):
    """Создает engine для тестовой БД (один на тест)"""
    await create_test_database()

    database_url = "postgresql+asyncpg://postgres:password@localhost:5432/test_db"

    engine = create_async_engine(
        database_url,
        echo=True,
        future=True
    )

    # Создаем таблицы для каждого теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Создает сессию БД для теста"""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def test_users(db_session, test_users_data):
    """Создает тестовых пользователей в БД"""
    from app.models import User, ApiKey

    if not test_users_data:
        return []

    created_users = []

    for user_info in test_users_data:
        user = User(id=user_info["user_id"], name=user_info["username"])
        db_session.add(user)

        api_key_value = user_info["api_key"]
        key_prefix = api_key_value[:8]
        key_hash = ApiKey.hash_key(api_key_value)

        api_key = ApiKey(
            user_id=user.id,
            key_prefix=key_prefix,
            key_hash=key_hash
        )
        db_session.add(api_key)

        created_users.append({
            "user": user,
            "api_key": api_key_value
        })

    await db_session.commit()
    return created_users


@pytest.fixture
def auth_headers(test_users):
    if not test_users:
        return {}
    api_key = test_users[0]["api_key"]
    return {"Api-Key": api_key}


@pytest.fixture
def specific_user_headers(test_users):
    def _get_headers(user_index=0):
        if not test_users or user_index >= len(test_users):
            return {}
        api_key = test_users[user_index]["api_key"]
        return {"Api-Key": api_key}

    return _get_headers