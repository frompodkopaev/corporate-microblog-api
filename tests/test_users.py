import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.routes import users
from app.models import User
from app.schemas import UserResponse, BasicResponse, UserFollowings
from app.dependencies import get_current_user, get_user_by_id, follow_user, unfollow_user
from app.core.exceptions import NotFoundException, ConflictException


# ========== Тесты роутера ==========

def test_router_prefix():
    """Тест префикса роутера"""
    assert users.router.prefix == "/api/users"
    assert users.router.tags == ["users"]


def test_router_routes_count():
    """Тест количества роутов"""
    assert len(users.router.routes) == 4


def test_router_paths():
    """Тест правильности путей в роутере"""
    paths = [route.path for route in users.router.routes]

    assert "/api/users/me" in paths
    assert "/api/users/{user_id}" in paths
    assert "/api/users/{user_id}/follow" in paths


def test_router_methods():
    """Тест HTTP методов для каждого пути"""
    path_methods = {}
    for route in users.router.routes:
        path_methods.setdefault(route.path, set()).update(route.methods)

    assert path_methods['/api/users/me'] == {'GET'}
    assert path_methods['/api/users/{user_id}'] == {'GET'}
    assert path_methods['/api/users/{user_id}/follow'] == {'POST', 'DELETE'}
    assert len(path_methods) == 3


# ========== Unit-тесты эндпоинтов ==========

@pytest.mark.asyncio
async def test_get_current_user_info_endpoint():
    """Тест эндпоинта get_current_user_info"""
    mock_user = User(id=1, name="Current User")
    mock_response = MagicMock(spec=UserResponse)

    with patch('app.routes.users.UserResponse.create', new_callable=AsyncMock,
               return_value=mock_response) as mock_create:
        result = await users.get_current_user_info(user=mock_user)

        assert result == mock_response
        mock_create.assert_awaited_once_with(mock_user)


@pytest.mark.asyncio
async def test_get_user_info_by_id_endpoint():
    """Тест эндпоинта get_user_info_by_id"""
    user_id = 5
    mock_user = User(id=5, name="Requested User")
    mock_response = MagicMock(spec=UserResponse)

    with patch('app.routes.users.UserResponse.create', new_callable=AsyncMock,
               return_value=mock_response) as mock_create:
        result = await users.get_user_info_by_id(user_id=user_id, user=mock_user)

        assert result == mock_response
        mock_create.assert_awaited_once_with(mock_user)


@pytest.mark.asyncio
async def test_follow_user_by_id_endpoint():
    """Тест эндпоинта follow_user_by_id"""
    user_id = 5
    result_value = True

    result = await users.follow_user_by_id(user_id=user_id, result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is True


@pytest.mark.asyncio
async def test_follow_user_by_id_false():
    """Тест эндпоинта follow_user_by_id с результатом False"""
    user_id = 5
    result_value = False

    result = await users.follow_user_by_id(user_id=user_id, result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is False


@pytest.mark.asyncio
async def test_unfollow_user_by_id_endpoint():
    """Тест эндпоинта unfollow_user_by_id"""
    user_id = 5
    result_value = True

    result = await users.unfollow_user_by_id(user_id=user_id, result=result_value)

    assert isinstance(result, BasicResponse)
    assert result.result is True


# ========== Интеграционные тесты с TestClient ==========

@pytest.mark.asyncio
async def test_get_current_user_info_integration(client, test_users, auth_headers):
    """Интеграционный тест GET /api/users/me"""
    headers = auth_headers
    current_user_data = test_users[0]  # Alice
    current_user = current_user_data["user"]
    user_id = current_user.id

    user_followings = UserFollowings(
        id=user_id,
        name=current_user.name,
        followers=[],
        following=[]
    )

    real_response = UserResponse(result=True, user=user_followings)

    app = client.app
    app.dependency_overrides = {}

    with patch('app.routes.users.UserResponse.create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = real_response

        response = client.get(
            "/api/users/me",
            headers=headers
        )

        print(f"Status code: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200
        assert response.json() == {
            "result": True,
            "user": {
                "id": user_id,
                "name": current_user.name,
                "followers": [],
                "following": []
            }
        }

        mock_create.assert_awaited_once()
        called_args = mock_create.call_args[0]
        assert len(called_args) == 1
        called_user = called_args[0]
        assert called_user.id == current_user.id
        assert called_user.name == current_user.name

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_user_by_id_integration(client, test_users, auth_headers):
    """Интеграционный тест GET /api/users/{id}"""
    target_user_data = test_users[1]  # Bob
    target_user = target_user_data["user"]
    user_id = target_user.id

    headers = auth_headers

    user_followings = UserFollowings(
        id=user_id,
        name=target_user.name,
        followers=[],
        following=[]
    )

    real_response = UserResponse(result=True, user=user_followings)

    app = client.app
    app.dependency_overrides = {}

    with patch('app.routes.users.UserResponse.create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = real_response

        response = client.get(
            f"/api/users/{user_id}",
            headers=headers
        )

        print(f"Status code: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200
        assert response.json() == {
            "result": True,
            "user": {
                "id": user_id,
                "name": target_user.name,
                "followers": [],
                "following": []
            }
        }

        mock_create.assert_awaited_once()
        called_args = mock_create.call_args[0]
        assert len(called_args) == 1
        called_user = called_args[0]
        assert called_user.id == target_user.id
        assert called_user.name == target_user.name

    app.dependency_overrides = {}


def test_follow_user_integration(client, auth_headers, test_users):
    """Интеграционный тест POST /api/users/{id}/follow"""
    user_id = 2  # Bob
    headers = auth_headers  # Alice

    app = client.app
    app.dependency_overrides = {}

    current_user_id = test_users[0]["user"].id  # ID Alice = 1

    mock_user_service = AsyncMock()
    mock_user_service.follow_user.return_value = True

    async def override_get_user_service():
        return mock_user_service

    from app.dependencies import get_user_service
    app.dependency_overrides[get_user_service] = override_get_user_service

    response = client.post(
        f"/api/users/{user_id}/follow",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    # Проверяем по ID, а не по объекту
    mock_user_service.follow_user.assert_awaited_once()
    args, _ = mock_user_service.follow_user.call_args
    assert len(args) == 2
    assert args[0].id == current_user_id  # Проверяем ID первого аргумента
    assert args[1] == user_id  # Проверяем ID второго аргумента

    app.dependency_overrides = {}


def test_follow_user_integration_false(client, auth_headers, test_users):
    """Интеграционный тест POST /api/users/{id}/follow с результатом False"""
    user_id = 2  # Bob
    headers = auth_headers  # Alice

    current_user_id = test_users[0]["user"].id  # ID Alice = 1

    app = client.app
    app.dependency_overrides = {}

    mock_user_service = AsyncMock()
    mock_user_service.follow_user.return_value = False

    async def override_get_user_service():
        return mock_user_service

    from app.dependencies import get_user_service
    app.dependency_overrides[get_user_service] = override_get_user_service

    response = client.post(
        f"/api/users/{user_id}/follow",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": False}

    mock_user_service.follow_user.assert_awaited_once()
    args, _ = mock_user_service.follow_user.call_args
    assert len(args) == 2
    assert args[0].id == current_user_id
    assert args[1] == user_id

    app.dependency_overrides = {}


def test_unfollow_user_integration(client, auth_headers, test_users):
    """Интеграционный тест DELETE /api/users/{id}/follow"""
    user_id = 2  # Bob
    headers = auth_headers  # Alice

    current_user_id = test_users[0]["user"].id  # ID Alice = 1

    app = client.app
    app.dependency_overrides = {}

    mock_user_service = AsyncMock()
    mock_user_service.unfollow_user.return_value = True

    async def override_get_user_service():
        return mock_user_service

    from app.dependencies import get_user_service
    app.dependency_overrides[get_user_service] = override_get_user_service

    response = client.delete(
        f"/api/users/{user_id}/follow",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    assert response.json() == {"result": True}

    mock_user_service.unfollow_user.assert_awaited_once()
    args, _ = mock_user_service.unfollow_user.call_args
    assert len(args) == 2
    assert args[0].id == current_user_id
    assert args[1] == user_id

    app.dependency_overrides = {}


# ========== Тесты на валидацию параметров ==========

def test_get_user_by_id_invalid_id(client, auth_headers):
    """Тест GET /api/users/{id} с невалидным ID"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    response = client.get(
        "/api/users/abc",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 422

    app.dependency_overrides = {}


# ========== Тесты на обработку ошибок ==========

def test_get_user_by_id_not_found(client, auth_headers):
    """Тест GET /api/users/{id} когда пользователь не найден"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    mock_user_service = AsyncMock()
    mock_user_service.get_user = AsyncMock(side_effect=NotFoundException("User", 999))

    async def override_get_user_service():
        return mock_user_service

    from app.dependencies import get_user_service
    app.dependency_overrides[get_user_service] = override_get_user_service

    response = client.get(
        "/api/users/999",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 404

    app.dependency_overrides = {}


def test_follow_user_conflict(client, auth_headers):
    """Тест POST /api/users/{id}/follow когда уже подписан"""
    headers = auth_headers
    user_id = 2  # Bob

    app = client.app
    app.dependency_overrides = {}

    mock_user_service = AsyncMock()
    mock_user_service.follow_user.side_effect = ConflictException("Already following this user")

    async def override_get_user_service():
        return mock_user_service

    from app.dependencies import get_user_service
    app.dependency_overrides[get_user_service] = override_get_user_service

    response = client.post(
        f"/api/users/{user_id}/follow",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 409

    app.dependency_overrides = {}


# ========== Тесты с реальными данными ==========

def test_get_existing_user_alice(client, auth_headers, test_users):
    """Тест получения Alice"""
    headers = auth_headers
    target_user = test_users[0]["user"]  # Alice
    user_id = target_user.id

    app = client.app
    app.dependency_overrides = {}

    response = client.get(
        f"/api/users/{user_id}",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["user"]["id"] == user_id
    assert data["user"]["name"] == target_user.name

    app.dependency_overrides = {}


def test_get_existing_user_bob(client, auth_headers, test_users):
    """Тест получения Bob"""
    headers = auth_headers
    target_user = test_users[1]["user"]  # Bob
    user_id = target_user.id

    app = client.app
    app.dependency_overrides = {}

    response = client.get(
        f"/api/users/{user_id}",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["user"]["id"] == user_id
    assert data["user"]["name"] == target_user.name

    app.dependency_overrides = {}


def test_get_existing_user_charly(client, auth_headers, test_users):
    """Тест получения Charly"""
    headers = auth_headers
    target_user = test_users[2]["user"]  # Charly
    user_id = target_user.id

    app = client.app
    app.dependency_overrides = {}

    response = client.get(
        f"/api/users/{user_id}",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["user"]["id"] == user_id
    assert data["user"]["name"] == target_user.name

    app.dependency_overrides = {}


def test_get_nonexistent_user_by_id(client, auth_headers):
    """Тест получения несуществующего пользователя"""
    headers = auth_headers
    user_id = 999

    app = client.app
    app.dependency_overrides = {}

    response = client.get(
        f"/api/users/{user_id}",
        headers=headers
    )

    print(f"User ID: {user_id}, Status: {response.status_code}")
    assert response.status_code == 404

    app.dependency_overrides = {}