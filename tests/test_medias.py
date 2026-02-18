import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile

from app.routes import medias
from app.schemas import MediaResponse
from app.core.exceptions import BusinessLogicException


# ========== Фикстуры ==========

@pytest.fixture
def app():
    """Фикстура создания приложения для тестов"""
    app = FastAPI()
    app.include_router(medias.router)
    return app


@pytest.fixture
def client(app):
    """Фикстура тестового клиента"""
    return TestClient(app)


@pytest.fixture
def mock_file():
    """Фикстура мок-файла для загрузки"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_image.jpg"
    file.content_type = "image/jpeg"
    file.size = 1024
    return file


# ========== Тесты роутера ==========

def test_router_prefix():
    """Тест префикса роутера"""
    assert medias.router.prefix == "/api/medias"
    assert medias.router.tags == ["medias"]


def test_router_routes_count():
    """Тест количества роутов"""
    assert len(medias.router.routes) == 1  # Только POST /


def test_router_paths():
    """Тест правильности путей в роутере"""
    paths = [route.path for route in medias.router.routes]

    assert "/api/medias/" in paths or "/api/medias" in paths


def test_router_methods():
    """Тест HTTP методов для каждого пути"""
    path_methods = {}
    for route in medias.router.routes:
        path_methods.setdefault(route.path, set()).update(route.methods)

    print(f"Path methods: {path_methods}")

    # Проверяем, что есть путь с POST методом
    found = False
    for path, methods in path_methods.items():
        if path in ['/api/medias/', '/api/medias'] and 'POST' in methods:
            found = True
            break

    assert found, "POST endpoint not found"
    assert len(path_methods) == 1, f"Expected 1 unique path, got {len(path_methods)}"


# ========== Unit-тесты эндпоинтов ==========

@pytest.mark.asyncio
async def test_upload_media_file_endpoint():
    """Тест эндпоинта upload_media_file"""
    media_id = 123
    mock_response = MagicMock(spec=MediaResponse)

    with patch('app.routes.medias.MediaResponse', return_value=mock_response) as mock_response_class:
        result = await medias.upload_media_file(media_id=media_id)

        assert result == mock_response
        mock_response_class.assert_called_once_with(result=True, media_id=media_id)


# ========== Интеграционные тесты с TestClient ==========

def test_upload_media_integration(client, auth_headers, test_users):
    """Интеграционный тест POST /api/medias/"""
    headers = auth_headers
    expected_media_id = 123

    app = client.app
    app.dependency_overrides = {}

    # Мокаем зависимость upload_media с правильной сигнатурой
    async def mock_upload_media(
        file: UploadFile,
        media_service = None,  # FastAPI ожидает эти параметры
        current_user = None
    ):
        return expected_media_id

    from app.dependencies import upload_media
    app.dependency_overrides[upload_media] = mock_upload_media

    # Создаем тестовый файл
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }

    response = client.post(
        "/api/medias/",
        files=files,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["media_id"] == expected_media_id

    app.dependency_overrides = {}


def test_upload_media_without_file(client, auth_headers, test_users):
    """Тест загрузки медиа без файла (должен вернуть 422)"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    # Отправляем запрос без файла
    response = client.post(
        "/api/medias/",
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    # FastAPI вернет 422, так как файл обязателен
    assert response.status_code == 422

    app.dependency_overrides = {}


# ========== Тесты на валидацию параметров ==========

def test_upload_media_invalid_file_type(client, auth_headers, test_users):
    """Тест загрузки файла с неверным типом"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    # Мокаем зависимость upload_media, чтобы она выбрасывала исключение
    async def mock_upload_media_with_error(
            file: UploadFile,
            media_service,
            current_user
    ):
        raise BusinessLogicException("File type not allowed")

    from app.dependencies import upload_media
    app.dependency_overrides[upload_media] = mock_upload_media_with_error

    # Создаем тестовый файл с неподдерживаемым типом
    files = {
        'file': ('test.gif', b'fake gif content', 'image/gif')
    }

    response = client.post(
        "/api/medias/",
        files=files,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    # Должен вернуть 400 Bad Request или 422 в зависимости от обработчика
    assert response.status_code in [400, 422]

    app.dependency_overrides = {}


def test_upload_media_file_too_large(client, auth_headers, test_users):
    """Тест загрузки слишком большого файла"""
    headers = auth_headers

    app = client.app
    app.dependency_overrides = {}

    # Мокаем зависимость upload_media, чтобы она выбрасывала исключение
    async def mock_upload_media_with_error(
            file: UploadFile,
            media_service,
            current_user
    ):
        raise BusinessLogicException("File too large")

    from app.dependencies import upload_media
    app.dependency_overrides[upload_media] = mock_upload_media_with_error

    # Создаем тестовый файл
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }

    response = client.post(
        "/api/medias/",
        files=files,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code in [400, 422]

    app.dependency_overrides = {}


# ========== Тесты с моками сервиса ==========

def test_upload_media_simple_mock(client, auth_headers, test_users):
    """Простой тест загрузки медиа с моком зависимости"""
    from app.dependencies import upload_media, get_current_user
    from fastapi import UploadFile, Depends

    headers = auth_headers
    expected_media_id = 123

    app = client.app
    app.dependency_overrides = {}

    # Мокаем get_current_user, чтобы он возвращал реального пользователя
    current_user = test_users[0]["user"]

    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Мокаем upload_media с правильной сигнатурой и Depends
    async def mock_upload_media(
            file: UploadFile,
            media_service=None,
            current_user=Depends(get_current_user)
    ):
        return expected_media_id

    app.dependency_overrides[upload_media] = mock_upload_media

    # Создаем тестовый файл
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }

    response = client.post(
        "/api/medias/",
        files=files,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["media_id"] == expected_media_id

    app.dependency_overrides = {}


def test_upload_media_without_auth(client):
    """Тест загрузки медиа без аутентификации"""
    # Создаем тестовый файл
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }

    response = client.post(
        "/api/medias/",
        files=files
        # Нет headers с аутентификацией
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 401


# ========== Тесты на обработку ошибок ==========

def test_upload_media_service_error(client, auth_headers, test_users):
    """Тест ошибки сервиса при загрузке медиа"""
    from app.dependencies import upload_media, get_current_user
    from fastapi import UploadFile, Depends
    from app.core.exceptions import BusinessLogicException

    headers = auth_headers
    current_user = test_users[0]["user"]

    app = client.app
    app.dependency_overrides = {}

    # Мокаем get_current_user
    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Мокаем upload_media с правильной сигнатурой, чтобы он выбрасывал исключение
    async def mock_upload_media_with_error(
        file: UploadFile,
        media_service = None,
        current_user = Depends(get_current_user)
    ):
        # Выбрасываем BusinessLogicException, который должен обрабатываться приложением
        raise BusinessLogicException("Service error")

    app.dependency_overrides[upload_media] = mock_upload_media_with_error

    # Создаем тестовый файл
    files = {
        'file': ('test.jpg', b'fake image content', 'image/jpeg')
    }

    response = client.post(
        "/api/medias/",
        files=files,
        headers=headers
    )

    print(f"Status code: {response.status_code}")
    print(f"Response body: {response.text}")

    # BusinessLogicException должен преобразовываться в 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

    app.dependency_overrides = {}