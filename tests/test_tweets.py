import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.routes import tweets
from app.schemas import BasicResponse, TweetResponse, TweetFeed
from app.dependencies import create_tweet, delete_tweet, like_tweet, unlike_tweet, get_user_feed
from app.core.exceptions import NotFoundException, ConflictException
from app.models import Tweet


# ========== Фикстуры ==========

@pytest.fixture
def app():
    """Фикстура создания приложения для тестов"""
    app = FastAPI()
    app.include_router(tweets.router)
    return app


@pytest.fixture
def client(app):
    """Фикстура тестового клиента"""
    return TestClient(app)


@pytest.fixture
def mock_tweet():
    """Фикстура мок-твита"""
    tweet = MagicMock(spec=Tweet)
    tweet.id = 1
    tweet.content = "Test tweet"
    tweet.user_id = 1
    return tweet


# ========== Тесты роутера ==========

def test_router_prefix():
    """Тест префикса роутера"""
    assert tweets.router.prefix == "/api/tweets"
    assert tweets.router.tags == ["tweets"]


def test_router_routes_count():
    """Тест количества роутов"""
    # Должно быть 5 роутов: GET /, POST /, DELETE /{id}, POST /{id}/likes, DELETE /{id}/likes
    assert len(tweets.router.routes) == 5


def test_router_paths():
    """Тест правильности путей в роутере"""
    paths = [route.path for route in tweets.router.routes]

    print(f"All paths: {paths}")

    # Проверяем наличие корневого пути (со слешем)
    assert "/api/tweets/" in paths, "Path /api/tweets/ should exist"

    # Проверяем наличие пути для удаления
    assert "/api/tweets/{id}" in paths, "Path /api/tweets/{{id}} should exist"

    # Проверяем наличие пути для лайков
    assert "/api/tweets/{id}/likes" in paths, "Path /api/tweets/{{id}}/likes should exist"

    # Проверяем, что всего 5 роутов (2 для /, 1 для /{id}, 2 для /{id}/likes)
    assert len(paths) == 5, f"Expected 5 routes, got {len(paths)}"


def test_router_methods():
    """Тест HTTP методов для каждого пути"""
    path_methods = {}
    for route in tweets.router.routes:
        path_methods.setdefault(route.path, set()).update(route.methods)

    print(f"\nPath methods: {path_methods}")

    # Проверяем корневой путь (GET и POST на одном пути)
    assert '/api/tweets/' in path_methods, "Path /api/tweets/ not found"
    assert path_methods['/api/tweets/'] == {'GET', 'POST'}, \
        f"Expected GET and POST for /api/tweets/, got {path_methods['/api/tweets/']}"

    # Проверяем путь для удаления
    assert '/api/tweets/{id}' in path_methods, "Path /api/tweets/{{id}} not found"
    assert path_methods['/api/tweets/{id}'] == {'DELETE'}, \
        f"Expected DELETE for /api/tweets/{{id}}, got {path_methods['/api/tweets/{id}']}"

    # Проверяем путь для лайков
    assert '/api/tweets/{id}/likes' in path_methods, "Path /api/tweets/{{id}}/likes not found"
    assert path_methods['/api/tweets/{id}/likes'] == {'POST', 'DELETE'}, \
        f"Expected POST and DELETE for /api/tweets/{{id}}/likes, got {path_methods['/api/tweets/{id}/likes']}"

    # Проверяем общее количество уникальных путей
    assert len(path_methods) == 3, f"Expected 3 unique paths, got {len(path_methods)}"


# ========== Unit-тесты эндпоинтов ==========

@pytest.mark.asyncio
async def test_show_tweets_endpoint():
    """Тест эндпоинта show_tweets"""
    mock_tweets = [MagicMock(spec=Tweet), MagicMock(spec=Tweet)]
    mock_response = MagicMock(spec=TweetFeed)

    with patch('app.routes.tweets.TweetFeed.create', return_value=mock_response) as mock_create:
        result = await tweets.show_tweets(tweets=mock_tweets)

        assert result == mock_response
        mock_create.assert_called_once_with(tweets=mock_tweets)


@pytest.mark.asyncio
async def test_create_new_tweet_endpoint():
    """Тест эндпоинта create_new_tweet"""
    tweet_id = 123
    mock_response = MagicMock(spec=TweetResponse)

    with patch('app.routes.tweets.TweetResponse', return_value=mock_response) as mock_response_class:
        result = await tweets.create_new_tweet(tweet_id=tweet_id)

        assert result == mock_response
        mock_response_class.assert_called_once_with(result=True, tweet_id=tweet_id)


@pytest.mark.asyncio
async def test_delete_tweet_by_id_endpoint():
    """Тест эндпоинта delete_tweet_by_id"""
    result_value = True

    result = await tweets.delete_tweet_by_id(result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is True


@pytest.mark.asyncio
async def test_like_tweet_by_id_endpoint():
    """Тест эндпоинта like_tweet_by_id"""
    result_value = True

    result = await tweets.like_tweet_by_id(result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is True


@pytest.mark.asyncio
async def test_unlike_tweet_by_id_endpoint():
    """Тест эндпоинта unlike_tweet_by_id"""
    result_value = True

    result = await tweets.unlike_tweet_by_id(result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is True


@pytest.mark.asyncio
async def test_like_tweet_by_id_false():
    """Тест эндпоинта like_tweet_by_id с результатом False"""
    result_value = False

    result = await tweets.like_tweet_by_id(result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is False


# ========== Интеграционные тесты с TestClient ==========

def test_show_tweets_integration(client, auth_headers):
    """Интеграционный тест GET /api/tweets/"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    # Создаем мок-твиты
    mock_tweets = [MagicMock(spec=Tweet), MagicMock(spec=Tweet)]

    # Создаем реальные объекты TweetInfo для ответа
    from app.schemas import TweetInfo, UserBasic, TweetFeed

    # Создаем автора
    author = UserBasic(id=1, name="Alice Developer")

    # Создаем твиты
    tweet_info_1 = TweetInfo(
        id=1,
        content="Tweet 1",
        attachments=[],
        author=author,
        likes=[]
    )
    tweet_info_2 = TweetInfo(
        id=2,
        content="Tweet 2",
        attachments=[],
        author=author,
        likes=[]
    )

    # Создаем реальный объект TweetFeed
    real_feed = TweetFeed(
        result=True,
        tweets=[tweet_info_1, tweet_info_2]
    )

    # Переопределяем зависимость get_user_feed
    async def override_get_user_feed():
        return mock_tweets

    from app.dependencies import get_user_feed
    app.dependency_overrides[get_user_feed] = override_get_user_feed

    # Мокаем TweetFeed.create, но возвращаем реальный объект
    with patch('app.routes.tweets.TweetFeed.create', return_value=real_feed) as mock_create:
        response = client.get("/api/tweets/", headers=headers)

        print(f"Status code: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert data["result"] is True
        assert "tweets" in data
        assert len(data["tweets"]) == 2

        # Проверяем первый твит
        assert data["tweets"][0]["id"] == 1
        assert data["tweets"][0]["content"] == "Tweet 1"
        assert data["tweets"][0]["author"]["id"] == 1
        assert data["tweets"][0]["author"]["name"] == "Alice Developer"

        # Проверяем второй твит
        assert data["tweets"][1]["id"] == 2
        assert data["tweets"][1]["content"] == "Tweet 2"

        mock_create.assert_called_once_with(tweets=mock_tweets)

    app.dependency_overrides = {}


def test_create_new_tweet_integration(client, auth_headers):
    """Интеграционный тест POST /api/tweets/"""
    headers = auth_headers
    tweet_id = 123

    app = client.app
    app.dependency_overrides = {}

    async def override_create_tweet():
        return tweet_id

    from app.dependencies import create_tweet
    app.dependency_overrides[create_tweet] = override_create_tweet

    response = client.post("/api/tweets/", headers=headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["tweet_id"] == tweet_id

    app.dependency_overrides = {}


def test_delete_tweet_integration(client, auth_headers):
    """Интеграционный тест DELETE /api/users/{id}"""
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_delete_tweet():
        return True

    from app.dependencies import delete_tweet
    app.dependency_overrides[delete_tweet] = override_delete_tweet

    response = client.delete(f"/api/tweets/{tweet_id}", headers=auth_headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    app.dependency_overrides = {}


def test_delete_tweet_integration_false(client, auth_headers):
    """Интеграционный тест DELETE /api/users/{id} с результатом False"""
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_delete_tweet():
        return False

    from app.dependencies import delete_tweet
    app.dependency_overrides[delete_tweet] = override_delete_tweet

    response = client.delete(f"/api/tweets/{tweet_id}", headers=auth_headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": False}

    app.dependency_overrides = {}


def test_like_tweet_integration(client, auth_headers):
    """Интеграционный тест POST /api/tweets/{id}/likes"""
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_like_tweet():
        return True

    from app.dependencies import like_tweet
    app.dependency_overrides[like_tweet] = override_like_tweet

    response = client.post(f"/api/tweets/{tweet_id}/likes", headers=auth_headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    app.dependency_overrides = {}


def test_like_tweet_integration_false(client, auth_headers):
    """Интеграционный тест POST /api/tweets/{id}/likes с результатом False"""
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_like_tweet():
        return False

    from app.dependencies import like_tweet
    app.dependency_overrides[like_tweet] = override_like_tweet

    response = client.post(f"/api/tweets/{tweet_id}/likes", headers=auth_headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": False}

    app.dependency_overrides = {}


def test_unlike_tweet_integration(client, auth_headers):
    """Интеграционный тест DELETE /api/tweets/{id}/likes"""
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_unlike_tweet():
        return True

    from app.dependencies import unlike_tweet
    app.dependency_overrides[unlike_tweet] = override_unlike_tweet

    response = client.delete(f"/api/tweets/{tweet_id}/likes", headers=auth_headers)

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    app.dependency_overrides = {}


# ========== Тесты на валидацию параметров ==========

def test_delete_tweet_invalid_id(client, auth_headers):
    """Тест DELETE /api/tweets/{id} с невалидным ID"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    response = client.delete(
        "/api/tweets/abc",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 422

    app.dependency_overrides = {}


def test_like_tweet_invalid_id(client, auth_headers):
    """Тест POST /api/tweets/{id}/likes с невалидным ID"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    response = client.post(
        "/api/tweets/abc/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 422

    app.dependency_overrides = {}


# ========== Тесты на обработку ошибок ==========

def test_delete_tweet_not_found(client, auth_headers):
    """Тест DELETE /api/tweets/{id} когда твит не найден"""
    headers = auth_headers
    tweet_id = 999

    app = client.app
    app.dependency_overrides = {}

    async def override_delete_tweet():
        raise NotFoundException("Tweet", tweet_id)

    from app.dependencies import delete_tweet
    app.dependency_overrides[delete_tweet] = override_delete_tweet

    response = client.delete(
        f"/api/tweets/{tweet_id}",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 404

    app.dependency_overrides = {}


def test_like_tweet_not_found(client, auth_headers):
    """Тест POST /api/tweets/{id}/likes когда твит не найден"""
    headers = auth_headers
    tweet_id = 999

    app = client.app
    app.dependency_overrides = {}

    async def override_like_tweet():
        raise NotFoundException("Tweet", tweet_id)

    from app.dependencies import like_tweet
    app.dependency_overrides[like_tweet] = override_like_tweet

    response = client.post(
        f"/api/tweets/{tweet_id}/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 404

    app.dependency_overrides = {}


def test_like_tweet_conflict(client, auth_headers):
    """Тест POST /api/tweets/{id}/likes когда уже лайкнуто"""
    headers = auth_headers
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_like_tweet():
        raise ConflictException("Already liked this tweet")

    from app.dependencies import like_tweet
    app.dependency_overrides[like_tweet] = override_like_tweet

    response = client.post(
        f"/api/tweets/{tweet_id}/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 409

    app.dependency_overrides = {}


def test_unlike_tweet_not_found(client, auth_headers):
    """Тест DELETE /api/tweets/{id}/likes когда лайк не найден"""
    headers = auth_headers
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    async def override_unlike_tweet():
        raise NotFoundException("Like", tweet_id)

    from app.dependencies import unlike_tweet
    app.dependency_overrides[unlike_tweet] = override_unlike_tweet

    response = client.delete(
        f"/api/tweets/{tweet_id}/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 404

    app.dependency_overrides = {}


# ========== Тесты с моками сервисов ==========

def test_create_tweet_with_mock_service(client, auth_headers, test_users):
    """Тест создания твита с мокнутым сервисом"""
    headers = auth_headers
    current_user_id = test_users[0]["user"].id
    expected_tweet_id = 123

    app = client.app
    app.dependency_overrides = {}

    # Мокаем сервис для создания твита
    mock_tweet_service = AsyncMock()
    mock_tweet_service.create_tweet = AsyncMock(return_value=expected_tweet_id)

    async def override_get_tweet_service():
        return mock_tweet_service

    from app.dependencies import get_tweet_service, create_tweet
    app.dependency_overrides[get_tweet_service] = override_get_tweet_service

    # Данные для создания твита
    tweet_data = {"content": "Test tweet content"}

    response = client.post(
        "/api/tweets/",
        json=tweet_data,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["tweet_id"] == expected_tweet_id

    # Проверяем, что сервис был вызван с правильными параметрами
    mock_tweet_service.create_tweet.assert_awaited_once()
    args, _ = mock_tweet_service.create_tweet.call_args
    assert args[0].id == current_user_id  # Проверяем ID пользователя
    assert args[1] == "Test tweet content"  # Проверяем контент
    # Проверяем media_ids, если они передаются
    # assert args[2] == []

    app.dependency_overrides = {}


def test_delete_tweet_with_mock_service(client, auth_headers, test_users):
    """Тест удаления твита с мокнутым сервисом"""
    headers = auth_headers
    tweet_id = 5
    current_user = test_users[0]["user"]  # Alice
    current_user_id = current_user.id

    app = client.app
    app.dependency_overrides = {}

    # Мокаем tweet_service
    mock_tweet_service = AsyncMock()
    mock_tweet_service.delete_tweet = AsyncMock(return_value=True)

    async def override_get_tweet_service():
        return mock_tweet_service

    # Не переопределяем delete_tweet, даем реальной зависимости работать
    from app.dependencies import get_tweet_service
    app.dependency_overrides[get_tweet_service] = override_get_tweet_service

    response = client.delete(
        f"/api/tweets/{tweet_id}",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    # Проверяем, что сервис был вызван с правильными параметрами
    mock_tweet_service.delete_tweet.assert_awaited_once()
    args, _ = mock_tweet_service.delete_tweet.call_args
    assert len(args) == 2
    # Проверяем по ID, а не по объекту
    assert args[0].id == current_user_id  # Проверяем ID пользователя
    assert args[1] == tweet_id  # Проверяем ID твита

    app.dependency_overrides = {}


def test_like_tweet_with_mock_service(client, auth_headers, test_users):
    """Тест лайка твита с мокнутым сервисом"""
    headers = auth_headers
    tweet_id = 5

    app = client.app
    app.dependency_overrides = {}

    # Мок-функция с правильной сигнатурой - без *args, **kwargs
    async def mock_like_tweet(
        tweet_id: int,
        tweet_service = None,
        current_user = None
    ):
        return True

    from app.dependencies import like_tweet
    app.dependency_overrides[like_tweet] = mock_like_tweet

    response = client.post(
        f"/api/tweets/{tweet_id}/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    app.dependency_overrides = {}


def test_unlike_tweet_with_mock_service(client, auth_headers, test_users):
    """Тест удаления лайка с мокнутым сервисом"""
    headers = auth_headers
    tweet_id = 5
    current_user_id = test_users[0]["user"].id

    app = client.app
    app.dependency_overrides = {}

    # Мокаем саму зависимость unlike_tweet, а не сервис
    async def mock_unlike_tweet(
        tweet_id: int,
        tweet_service = None,
        current_user = None
    ):
        return True

    from app.dependencies import unlike_tweet
    app.dependency_overrides[unlike_tweet] = mock_unlike_tweet

    response = client.delete(
        f"/api/tweets/{tweet_id}/likes",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    app.dependency_overrides = {}