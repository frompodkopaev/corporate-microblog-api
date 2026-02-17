import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from fastapi import Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    init_db, close_db, get_db, get_api_key,
    get_user_service_cached, get_api_key_service_cached,
    get_tweet_service_cached, get_media_service_cached,
    get_service, get_user_service, get_api_key_service,
    get_tweet_service, get_media_service, get_current_user,
    get_user_by_id, follow_user, unfollow_user,
    like_tweet, unlike_tweet, get_user_feed,
    create_tweet, delete_tweet, upload_media
)
from app.models import User, Tweet
from app.schemas import TweetCreate
from app.core.exceptions import UnauthorizedException


import pytest
from unittest.mock import AsyncMock, patch, ANY


@pytest.mark.asyncio
async def test_init_db():
    """Тест инициализации БД"""
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_async_cm = AsyncMock()
    mock_async_cm.__aenter__.return_value = mock_conn
    mock_async_cm.__aexit__.return_value = None

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_async_cm

    with patch('app.dependencies.engine', mock_engine):
        from app.dependencies import init_db
        await init_db()

        mock_engine.begin.assert_called_once()
        mock_async_cm.__aenter__.assert_called_once()
        mock_async_cm.__aexit__.assert_called_once()
        mock_conn.run_sync.assert_called_once()

@pytest.mark.asyncio
async def test_close_db():
    """Тест закрытия БД"""
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()

    with patch('app.dependencies.engine', mock_engine):
        await close_db()
        mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_success():
    """Тест успешного получения сессии БД"""
    mock_session = AsyncMock(spec=AsyncSession)

    with patch('app.dependencies.AsyncSessionFabric') as mock_session_fabric:
        mock_session_fabric.return_value.__aenter__.return_value = mock_session

        # Получаем генератор
        gen = get_db()
        session = await gen.__anext__()

        assert session == mock_session
        mock_session.commit.assert_not_called()  # еще не вызывали commit

        # Завершаем генератор
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_with_exception():
    """Тест получения сессии с исключением"""
    mock_session = AsyncMock(spec=AsyncSession)

    with patch('app.dependencies.AsyncSessionFabric') as mock_session_fabric:
        mock_session_fabric.return_value.__aenter__.return_value = mock_session

        gen = get_db()
        session = await gen.__anext__()

        # Симулируем исключение в блоке try
        with pytest.raises(ValueError):
            await gen.athrow(ValueError("Test error"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_api_key_success():
    """Тест успешного получения API ключа"""
    api_key = "test-api-key-123"
    result = await get_api_key(api_key)
    assert result == api_key


@pytest.mark.asyncio
async def test_get_api_key_missing():
    """Тест отсутствия API ключа"""
    with pytest.raises(UnauthorizedException) as exc_info:
        await get_api_key(None)

    assert "API key is required" in str(exc_info.value)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_api_key_empty_string():
    """Тест пустого API ключа"""
    with pytest.raises(UnauthorizedException):
        await get_api_key("")


def test_get_user_service_cached():
    """Тест кэшированного создания UserService"""
    mock_db = AsyncMock(spec=AsyncSession)

    service1 = get_user_service_cached(mock_db)
    service2 = get_user_service_cached(mock_db)

    assert service1 is service2  # Должен вернуть тот же объект из кэша

    # Проверяем, что сервис создан с правильной БД сессией
    assert service1.db == mock_db


def test_get_api_key_service_cached():
    """Тест кэшированного создания ApiKeyService"""
    mock_db = AsyncMock(spec=AsyncSession)

    service1 = get_api_key_service_cached(mock_db)
    service2 = get_api_key_service_cached(mock_db)

    assert service1 is service2


def test_get_tweet_service_cached():
    """Тест кэшированного создания TweetService"""
    mock_db = AsyncMock(spec=AsyncSession)

    service1 = get_tweet_service_cached(mock_db)
    service2 = get_tweet_service_cached(mock_db)

    assert service1 is service2


def test_get_media_service_cached():
    """Тест кэшированного создания MediaService"""
    mock_db = AsyncMock(spec=AsyncSession)

    service1 = get_media_service_cached(mock_db)
    service2 = get_media_service_cached(mock_db)

    assert service1 is service2


@pytest.mark.asyncio
async def test_get_service_generic():
    """Тест обобщенной фабрики сервисов"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_service_class = MagicMock()
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance

    # Создаем зависимость
    dependency = get_service(mock_service_class)

    # Мокаем Depends(get_db)
    with patch('app.dependencies.get_db') as mock_get_db:
        mock_get_db.return_value = mock_db

        # Вызываем зависимость
        result = await dependency(db=mock_db)

        assert result == mock_service_instance
        mock_service_class.assert_called_once_with(mock_db)


@pytest.mark.asyncio
async def test_get_service_caching():
    """Тест кэширования в обобщенной фабрике"""
    mock_db1 = AsyncMock(spec=AsyncSession)
    mock_db2 = AsyncMock(spec=AsyncSession)

    # Создаем два разных мока для сервисов
    service_instance_1 = MagicMock(name='service1')
    service_instance_2 = MagicMock(name='service2')

    # При первом вызове возвращаем service1, при втором - service2
    mock_service_class = MagicMock()
    mock_service_class.side_effect = [service_instance_1, service_instance_2]

    dependency = get_service(mock_service_class)

    with patch('app.dependencies.get_db'):
        service1 = await dependency(db=mock_db1)
        service2 = await dependency(db=mock_db1)
        service3 = await dependency(db=mock_db2)

        # Проверяем кэширование
        assert service1 is service_instance_1
        assert service2 is service_instance_1  # должен быть кэш
        assert service1 is service2

        # Проверяем создание нового для другой сессии
        assert service3 is service_instance_2
        assert service1 is not service3

        # Проверяем количество созданных экземпляров
        assert mock_service_class.call_count == 2


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Тест успешной аутентификации пользователя"""
    mock_api_key = "test-key"
    mock_user = User(id=1, name="Test User")
    mock_api_key_service = AsyncMock()
    mock_api_key_service.authenticate = AsyncMock(return_value=mock_user)

    user = await get_current_user(
        api_key=mock_api_key,
        api_key_service=mock_api_key_service
    )

    assert user == mock_user
    mock_api_key_service.authenticate.assert_awaited_once_with(mock_api_key)


@pytest.mark.asyncio
async def test_get_current_user_invalid_key():
    """Тест невалидного API ключа"""
    mock_api_key = "invalid-key"
    mock_api_key_service = AsyncMock()
    mock_api_key_service.authenticate = AsyncMock(return_value=None)

    with pytest.raises(UnauthorizedException) as exc_info:
        await get_current_user(
            api_key=mock_api_key,
            api_key_service=mock_api_key_service
        )

    assert "Invalid API key" in str(exc_info.value)
    mock_api_key_service.authenticate.assert_awaited_once_with(mock_api_key)


@pytest.mark.asyncio
async def test_get_user_by_id():
    """Тест получения пользователя по ID"""
    mock_user_id = 1
    mock_current_user = User(id=2, name="Current User")
    mock_requested_user = User(id=1, name="Requested User")
    mock_user_service = AsyncMock()
    mock_user_service.get_user = AsyncMock(return_value=mock_requested_user)

    result = await get_user_by_id(
        user_id=mock_user_id,
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result == mock_requested_user
    mock_user_service.get_user.assert_awaited_once_with(mock_current_user, mock_user_id)


@pytest.mark.asyncio
async def test_follow_user():
    """Тест подписки на пользователя"""
    mock_user_id = 3
    mock_current_user = User(id=1, name="Current User")
    mock_user_service = AsyncMock()
    mock_user_service.follow_user = AsyncMock(return_value=True)

    result = await follow_user(
        user_id=mock_user_id,
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result is True
    mock_user_service.follow_user.assert_awaited_once_with(mock_current_user, mock_user_id)


@pytest.mark.asyncio
async def test_unfollow_user():
    """Тест отписки от пользователя"""
    mock_user_id = 3
    mock_current_user = User(id=1, name="Current User")
    mock_user_service = AsyncMock()
    mock_user_service.unfollow_user = AsyncMock(return_value=True)

    result = await unfollow_user(
        user_id=mock_user_id,
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result is True
    mock_user_service.unfollow_user.assert_awaited_once_with(mock_current_user, mock_user_id)


@pytest.mark.asyncio
async def test_like_tweet():
    """Тест лайка твита"""
    mock_tweet_id = 5
    mock_current_user = User(id=1, name="Current User")
    mock_user_service = AsyncMock()
    mock_user_service.like_tweet = AsyncMock(return_value=True)

    result = await like_tweet(
        tweet_id=mock_tweet_id,
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result is True
    mock_user_service.like_tweet.assert_awaited_once_with(mock_current_user, mock_tweet_id)


@pytest.mark.asyncio
async def test_unlike_tweet():
    """Тест снятия лайка с твита"""
    mock_tweet_id = 5
    mock_current_user = User(id=1, name="Current User")
    mock_user_service = AsyncMock()
    mock_user_service.unlike_tweet = AsyncMock(return_value=True)

    result = await unlike_tweet(
        tweet_id=mock_tweet_id,
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result is True
    mock_user_service.unlike_tweet.assert_awaited_once_with(mock_current_user, mock_tweet_id)


@pytest.mark.asyncio
async def test_get_user_feed():
    """Тест получения ленты пользователя"""
    mock_current_user = User(id=1, name="Current User")
    mock_tweets = [Tweet(id=1, content="Tweet 1"), Tweet(id=2, content="Tweet 2")]
    mock_user_service = AsyncMock()
    mock_user_service.get_tweets_feed_list = AsyncMock(return_value=mock_tweets)

    result = await get_user_feed(
        user_service=mock_user_service,
        current_user=mock_current_user
    )

    assert result == mock_tweets
    mock_user_service.get_tweets_feed_list.assert_awaited_once_with(mock_current_user)


@pytest.mark.asyncio
async def test_create_tweet():
    """Тест создания твита"""
    mock_content = "Test tweet content"  # меняем название переменной
    mock_media_ids = [1, 2, 3]
    # Используем правильное название поля - content
    mock_tweet_schema = TweetCreate(content=mock_content, media_ids=mock_media_ids)
    mock_current_user = User(id=1, name="Current User")
    mock_tweet_service = AsyncMock()
    mock_tweet_service.create_tweet = AsyncMock(return_value=123)

    result = await create_tweet(
        tweet_schema=mock_tweet_schema,
        tweet_service=mock_tweet_service,
        current_user=mock_current_user
    )

    assert result == 123
    mock_tweet_service.create_tweet.assert_awaited_once_with(
        mock_current_user, mock_content, mock_media_ids  # используем mock_content
    )


@pytest.mark.asyncio
async def test_create_tweet_without_media():
    """Тест создания твита без медиа"""
    mock_content = "Test tweet without media"
    mock_tweet_schema = TweetCreate(content=mock_content, media_ids=None)
    mock_current_user = User(id=1, name="Current User")
    mock_tweet_service = AsyncMock()
    mock_tweet_service.create_tweet = AsyncMock(return_value=124)

    result = await create_tweet(
        tweet_schema=mock_tweet_schema,
        tweet_service=mock_tweet_service,
        current_user=mock_current_user
    )

    assert result == 124
    mock_tweet_service.create_tweet.assert_awaited_once_with(
        mock_current_user, mock_content, None
    )


@pytest.mark.asyncio
async def test_delete_tweet():
    """Тест удаления твита"""
    mock_tweet_id = 5
    mock_current_user = User(id=1, name="Current User")
    mock_tweet_service = AsyncMock()
    mock_tweet_service.delete_tweet = AsyncMock(return_value=True)

    result = await delete_tweet(
        tweet_id=mock_tweet_id,
        tweet_service=mock_tweet_service,
        current_user=mock_current_user
    )

    assert result is True
    mock_tweet_service.delete_tweet.assert_awaited_once_with(mock_current_user, mock_tweet_id)


@pytest.mark.asyncio
async def test_upload_media():
    """Тест загрузки медиафайла"""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_current_user = User(id=1, name="Current User")
    mock_media_service = AsyncMock()
    mock_media_service.upload_file = AsyncMock(return_value=42)

    result = await upload_media(
        file=mock_file,
        media_service=mock_media_service,
        current_user=mock_current_user
    )

    assert result == 42
    mock_media_service.upload_file.assert_awaited_once_with(mock_current_user, mock_file)


def test_service_factories_exist():
    """Тест наличия всех фабрик сервисов"""
    assert callable(get_user_service)
    assert callable(get_api_key_service)
    assert callable(get_tweet_service)
    assert callable(get_media_service)


@pytest.mark.asyncio
async def test_dependencies_chain():
    """Тест цепочки зависимостей"""
    # Проверяем, что зависимости корректно связаны
    mock_db = AsyncMock()
    mock_user_service = AsyncMock()

    with patch('app.dependencies.get_db', return_value=mock_db):
        # Проверяем, что get_user_service возвращает сервис
        service = await get_user_service(db=mock_db)
        assert service is not None