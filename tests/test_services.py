import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock, ANY
from datetime import datetime
from pathlib import Path
from uuid import UUID
import hashlib
from time import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import UploadFile

from app.services import (
    UserService, ApiKeyService, TweetService, MediaService
)
from app.models import User, ApiKey, Follow, Tweet, Media, Like
from app.core.exceptions import (
    NotFoundException, ConflictException, BusinessLogicException,
    ValidationException, InsufficientPermissionsException
)


class TestUserService:
    """Тесты для UserService"""

    @pytest.fixture
    def db_session(self):
        """Фикстура мок-сессии БД"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def user_service(self, db_session):
        """Фикстура UserService"""
        return UserService(db_session)

    @pytest.fixture
    def current_user(self):
        """Фикстура текущего пользователя"""
        return User(id=1, name="Current User")

    @pytest.mark.asyncio
    async def test_get_user_self(self, user_service, db_session, current_user):
        """Тест получения самого себя"""
        result = await user_service.get_user(current_user, current_user.id)

        assert result == current_user
        db_session.get.assert_not_called()  # Не должно быть запроса к БД

    @pytest.mark.asyncio
    async def test_get_user_other_exists(self, user_service, db_session, current_user):
        """Тест получения другого существующего пользователя"""
        other_user = User(id=2, name="Other User")
        db_session.get.return_value = other_user

        result = await user_service.get_user(current_user, 2)

        assert result == other_user
        db_session.get.assert_awaited_once_with(User, 2)

    @pytest.mark.asyncio
    async def test_get_user_other_not_found(self, user_service, db_session, current_user):
        """Тест получения несуществующего пользователя"""
        db_session.get.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.get_user(current_user, 999)

        assert "User" in str(exc_info.value)
        assert "999" in str(exc_info.value)
        db_session.get.assert_awaited_once_with(User, 999)

    @pytest.mark.asyncio
    async def test_follow_user_success(self, user_service, db_session, current_user):
        """Тест успешной подписки на пользователя"""
        following_id = 2

        # Настраиваем результат запроса
        mock_result = MagicMock()
        mock_result.first.return_value = (User(id=2), None)  # User существует, подписки нет
        db_session.execute.return_value = mock_result

        result = await user_service.follow_user(current_user, following_id)

        assert result is True
        db_session.execute.assert_awaited_once()
        db_session.add.assert_called_once()
        added_follow = db_session.add.call_args[0][0]
        assert isinstance(added_follow, Follow)
        assert added_follow.follower_id == current_user.id
        assert added_follow.following_id == following_id

    @pytest.mark.asyncio
    async def test_follow_user_self(self, user_service, current_user):
        """Тест попытки подписаться на самого себя"""
        with pytest.raises(BusinessLogicException) as exc_info:
            await user_service.follow_user(current_user, current_user.id)

        assert "User cannot follow himself" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_follow_user_not_found(self, user_service, db_session, current_user):
        """Тест подписки на несуществующего пользователя"""
        following_id = 999

        mock_result = MagicMock()
        mock_result.first.return_value = None  # User не найден
        db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.follow_user(current_user, following_id)

        assert "User" in str(exc_info.value)
        assert str(following_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_follow_user_already_following(self, user_service, db_session, current_user):
        """Тест повторной подписки"""
        following_id = 2

        mock_result = MagicMock()
        mock_follow = Follow(follower_id=current_user.id, following_id=following_id)
        mock_result.first.return_value = (User(id=2), mock_follow)  # Уже подписан
        db_session.execute.return_value = mock_result

        with pytest.raises(ConflictException) as exc_info:
            await user_service.follow_user(current_user, following_id)

        assert "Already following this user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unfollow_user_success(self, user_service, db_session, current_user):
        """Тест успешной отписки"""
        following_id = 2

        mock_follow = Follow(follower_id=current_user.id, following_id=following_id)
        mock_result = MagicMock()
        mock_result.first.return_value = (User(id=2), mock_follow)
        db_session.execute.return_value = mock_result

        result = await user_service.unfollow_user(current_user, following_id)

        assert result is True
        db_session.delete.assert_awaited_once_with(mock_follow)

    @pytest.mark.asyncio
    async def test_unfollow_user_self(self, user_service, current_user):
        """Тест попытки отписаться от самого себя"""
        with pytest.raises(BusinessLogicException) as exc_info:
            await user_service.unfollow_user(current_user, current_user.id)

        assert "User cannot unfollow himself" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unfollow_user_not_found(self, user_service, db_session, current_user):
        """Тест отписки от несуществующего пользователя"""
        following_id = 999

        mock_result = MagicMock()
        mock_result.first.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.unfollow_user(current_user, following_id)

        assert "User" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unfollow_user_not_following(self, user_service, db_session, current_user):
        """Тест отписки от пользователя, на которого не подписан"""
        following_id = 2

        mock_result = MagicMock()
        mock_result.first.return_value = (User(id=2), None)  # Не подписан
        db_session.execute.return_value = mock_result

        with pytest.raises(ConflictException) as exc_info:
            await user_service.unfollow_user(current_user, following_id)

        assert "Not following this user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_like_tweet_success(self, user_service, db_session, current_user):
        """Тест успешного лайка твита"""
        tweet_id = 10

        # Создаем мок твита без лайков
        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = tweet_id
        mock_tweet.likes_counter = 5
        mock_tweet.likes = []  # Нет лайков

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tweet
        db_session.execute.return_value = mock_result

        result = await user_service.like_tweet(current_user, tweet_id)

        assert result is True
        db_session.add.assert_called_once()
        added_like = db_session.add.call_args[0][0]
        assert isinstance(added_like, Like)
        assert added_like.tweet_id == tweet_id
        assert added_like.user_id == current_user.id
        assert mock_tweet.likes_counter == 6  # Увеличился счетчик

    @pytest.mark.asyncio
    async def test_like_tweet_not_found(self, user_service, db_session, current_user):
        """Тест лайка несуществующего твита"""
        tweet_id = 999

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.like_tweet(current_user, tweet_id)

        assert "Tweet" in str(exc_info.value)
        assert str(tweet_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_like_tweet_already_liked(self, user_service, db_session, current_user):
        """Тест повторного лайка"""
        tweet_id = 10

        # Создаем мок твита с уже существующим лайком
        mock_like = MagicMock(spec=Like)
        mock_like.user_id = current_user.id

        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = tweet_id
        mock_tweet.likes_counter = 5
        mock_tweet.likes = [mock_like]  # Уже есть лайк

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tweet
        db_session.execute.return_value = mock_result

        with pytest.raises(ConflictException) as exc_info:
            await user_service.like_tweet(current_user, tweet_id)

        assert "Tweet already liked" in str(exc_info.value)
        assert mock_tweet.likes_counter == 5  # Счетчик не изменился

    @pytest.mark.asyncio
    async def test_unlike_tweet_success(self, user_service, db_session, current_user):
        """Тест успешного снятия лайка"""
        tweet_id = 10

        mock_like = MagicMock(spec=Like)
        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.likes_counter = 5

        mock_result = MagicMock()
        mock_result.first.return_value = (mock_tweet, mock_like)
        db_session.execute.return_value = mock_result

        result = await user_service.unlike_tweet(current_user, tweet_id)

        assert result is True
        db_session.delete.assert_awaited_once_with(mock_like)
        assert mock_tweet.likes_counter == 4  # Уменьшился счетчик

    @pytest.mark.asyncio
    async def test_unlike_tweet_not_found(self, user_service, db_session, current_user):
        """Тест снятия лайка с несуществующего твита"""
        tweet_id = 999

        mock_result = MagicMock()
        mock_result.first.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.unlike_tweet(current_user, tweet_id)

        assert "Tweet" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unlike_tweet_not_liked(self, user_service, db_session, current_user):
        """Тест снятия несуществующего лайка"""
        tweet_id = 10

        mock_tweet = MagicMock(spec=Tweet)
        mock_result = MagicMock()
        mock_result.first.return_value = (mock_tweet, None)  # Нет лайка
        db_session.execute.return_value = mock_result

        with pytest.raises(ConflictException) as exc_info:
            await user_service.unlike_tweet(current_user, tweet_id)

        assert "Tweet not liked" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tweets_feed_list(self, user_service, db_session, current_user):
        """Тест получения ленты твитов"""
        mock_tweets = [MagicMock(spec=Tweet), MagicMock(spec=Tweet)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tweets
        db_session.execute.return_value = mock_result

        result = await user_service.get_tweets_feed_list(current_user)

        assert result == mock_tweets
        db_session.execute.assert_awaited_once()

        # Проверяем, что запрос содержит правильные условия
        call_args = db_session.execute.call_args[0][0]
        assert 'followings' in str(call_args)  # Должен быть JOIN с followings


class TestApiKeyService:
    """Тесты для ApiKeyService"""

    @pytest.fixture
    def db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def api_key_service(self, db_session):
        return ApiKeyService(db_session)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, api_key_service, db_session):
        """Тест успешной аутентификации"""
        api_key = "test-prefix-1234567890"
        prefix = api_key[:8]

        mock_user = User(id=1, name="Test User")
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.user = mock_user
        mock_api_key.verify_key.return_value = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result

        result = await api_key_service.authenticate(api_key)

        assert result == mock_user
        mock_api_key.verify_key.assert_called_once_with(api_key)

        # Проверяем кэширование
        assert api_key_service._cache != {}
        cache_key = hashlib.md5(api_key.encode()).hexdigest()
        assert cache_key in api_key_service._cache

    @pytest.mark.asyncio
    async def test_authenticate_from_cache(self, api_key_service):
        """Тест аутентификации из кэша"""
        api_key = "test-key-123"
        cache_key = hashlib.md5(api_key.encode()).hexdigest()
        mock_user = User(id=1, name="Cached User")

        # Добавляем в кэш
        api_key_service._cache[cache_key] = (mock_user, time())

        result = await api_key_service.authenticate(api_key)

        assert result == mock_user
        # Не должно быть запросов к БД

    @pytest.mark.asyncio
    async def test_authenticate_cache_expired(self, api_key_service, db_session):
        """Тест истекшего кэша"""
        api_key = "test-key-123"
        cache_key = hashlib.md5(api_key.encode()).hexdigest()
        mock_user = User(id=1, name="Expired User")

        # Добавляем в кэш с истекшим временем
        old_time = time() - api_key_service._cache_ttl - 1
        api_key_service._cache[cache_key] = (mock_user, old_time)

        # Мокаем успешный ответ от БД
        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.user = User(id=2, name="Fresh User")
        mock_api_key.verify_key.return_value = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result

        result = await api_key_service.authenticate(api_key)

        assert result.id == 2
        assert result.name == "Fresh User"
        assert cache_key in api_key_service._cache
        assert api_key_service._cache[cache_key][0].id == 2

    @pytest.mark.asyncio
    async def test_authenticate_key_not_found(self, api_key_service, db_session):
        """Тест аутентификации с несуществующим ключом"""
        api_key = "nonexistent-key"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        result = await api_key_service.authenticate(api_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_key(self, api_key_service, db_session):
        """Тест аутентификации с невалидным ключом"""
        api_key = "invalid-key"

        mock_api_key = MagicMock(spec=ApiKey)
        mock_api_key.verify_key.return_value = False  # Неверный ключ

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result

        result = await api_key_service.authenticate(api_key)

        assert result is None
        mock_api_key.verify_key.assert_called_once_with(api_key)


class TestTweetService:
    """Тесты для TweetService"""

    @pytest.fixture
    def db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def tweet_service(self, db_session):
        return TweetService(db_session)

    @pytest.fixture
    def current_user(self):
        return User(id=1, name="Tweet Author")

    @pytest.mark.asyncio
    async def test_create_tweet_success(self, tweet_service, db_session, current_user):
        """Тест успешного создания твита"""
        tweet_data = "Hello, world!"
        media_ids = None

        # Настраиваем flush для получения id
        async def flush_side_effect():
            new_tweet = db_session.add.call_args[0][0]
            new_tweet.id = 123

        db_session.flush.side_effect = flush_side_effect

        result = await tweet_service.create_tweet(current_user, tweet_data, media_ids)

        assert result == 123
        db_session.add.assert_called_once()
        added_tweet = db_session.add.call_args[0][0]
        assert isinstance(added_tweet, Tweet)
        assert added_tweet.user_id == current_user.id
        assert added_tweet.content == tweet_data
        db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_tweet_with_media(self, tweet_service, db_session, current_user):
        """Тест создания твита с медиа"""
        tweet_data = "Tweet with media"
        media_ids = [1, 2, 3]

        # Создаем реальные объекты Media (не моки)
        media_objects = [Media(id=i) for i in media_ids]

        # Мокаем результат запроса к БД
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = media_objects
        db_session.execute.return_value = mock_result

        # Настраиваем flush для установки ID нового твита
        added_tweet = None

        async def flush_side_effect():
            nonlocal added_tweet
            # Получаем добавленный твит
            added_tweet = db_session.add.call_args[0][0]
            added_tweet.id = 456

        db_session.flush.side_effect = flush_side_effect

        result = await tweet_service.create_tweet(current_user, tweet_data, media_ids)

        assert result == 456
        # Проверяем, что медиа добавлены в твит
        added_tweet = db_session.add.call_args[0][0]
        assert len(added_tweet.media) == 3
        assert added_tweet.media[0].id == 1
        assert added_tweet.media[1].id == 2
        assert added_tweet.media[2].id == 3

    @pytest.mark.asyncio
    async def test_create_tweet_empty_content(self, tweet_service, current_user):
        """Тест создания твита с пустым содержимым"""
        with pytest.raises(ValidationException) as exc_info:
            await tweet_service.create_tweet(current_user, "", [])

        assert "Tweet content cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_tweet_whitespace_only(self, tweet_service, current_user):
        """Тест создания твита только из пробелов"""
        with pytest.raises(ValidationException) as exc_info:
            await tweet_service.create_tweet(current_user, "   ", [])

        assert "Tweet content cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_tweet_too_long(self, tweet_service, current_user):
        """Тест создания слишком длинного твита"""
        long_content = "a" * 1001

        with pytest.raises(ValidationException) as exc_info:
            await tweet_service.create_tweet(current_user, long_content, [])

        assert "Tweet content too long" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_tweet_success(self, tweet_service, db_session, current_user):
        """Тест успешного удаления твита"""
        tweet_id = 123

        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = tweet_id
        mock_tweet.user_id = current_user.id  # Автор - текущий пользователь

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tweet
        db_session.execute.return_value = mock_result

        result = await tweet_service.delete_tweet(current_user, tweet_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_tweet_not_found(self, tweet_service, db_session, current_user):
        """Тест удаления несуществующего твита"""
        tweet_id = 999

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        with pytest.raises(NotFoundException) as exc_info:
            await tweet_service.delete_tweet(current_user, tweet_id)

        assert "Tweet" in str(exc_info.value)
        assert str(tweet_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_tweet_not_author(self, tweet_service, db_session, current_user):
        """Тест удаления чужого твита"""
        tweet_id = 123

        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = tweet_id
        mock_tweet.user_id = 999  # Другой автор

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tweet
        db_session.execute.return_value = mock_result

        with pytest.raises(InsufficientPermissionsException) as exc_info:
            await tweet_service.delete_tweet(current_user, tweet_id)

        assert "User not the author" in str(exc_info.value)


class TestMediaService:
    """Тесты для MediaService"""

    @pytest.fixture
    def db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def media_service(self, db_session, tmp_path):
        """Фикстура MediaService с временной директорией"""
        with patch('app.services.MediaService.UPLOAD_ROOT', tmp_path):
            service = MediaService(db_session)
            yield service

    @pytest.fixture
    def current_user(self):
        return User(id=42, name="Media Uploader")

    @pytest.fixture
    def mock_upload_file(self):
        """Фикстура мок-файла для загрузки"""
        file = AsyncMock(spec=UploadFile)
        file.filename = "test_image.jpg"
        file.content_type = "image/jpeg"
        file.size = 1024 * 1024  # 1MB
        file.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", None])
        return file

    @pytest.mark.asyncio
    async def test_upload_file_success(self, media_service, db_session, current_user, mock_upload_file, tmp_path):
        """Тест успешной загрузки файла"""

        # Настраиваем flush для получения id
        async def flush_side_effect():
            media = db_session.add.call_args[0][0]
            media.id = 100

        db_session.flush.side_effect = flush_side_effect

        result = await media_service.upload_file(current_user, mock_upload_file)

        assert result == 100
        db_session.add.assert_called_once()
        added_media = db_session.add.call_args[0][0]
        assert isinstance(added_media, Media)
        assert str(tmp_path) in added_media.link
        assert "user_42" in added_media.link

    @pytest.mark.asyncio
    async def test_upload_file_invalid_type(self, media_service, current_user):
        """Тест загрузки файла неразрешенного типа"""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024

        with pytest.raises(BusinessLogicException) as exc_info:
            await media_service.upload_file(current_user, mock_file)

        assert "File type" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, media_service, current_user):
        """Тест загрузки слишком большого файла"""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = 20 * 1024 * 1024  # 20MB

        with pytest.raises(BusinessLogicException) as exc_info:
            await media_service.upload_file(current_user, mock_file)

        assert "File too large" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_file_no_size(self, media_service, current_user, mock_upload_file, db_session, tmp_path):
        """Тест загрузки файла без указания размера"""
        mock_upload_file.size = None

        # Настраиваем мок для db_session
        db_session.add = AsyncMock()

        # Настраиваем flush
        async def flush_side_effect():
            media = db_session.add.call_args[0][0]
            media.id = 101

        db_session.flush = AsyncMock(side_effect=flush_side_effect)

        result = await media_service.upload_file(current_user, mock_upload_file)

        assert result == 101

    def test_validate_file_success(self, media_service):
        """Тест успешной валидации файла"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/png"
        mock_file.size = 5 * 1024 * 1024

        # Не должно быть исключения
        media_service._validate_file(mock_file)  # синхронный метод

    @pytest.mark.asyncio
    async def test_validate_file_invalid_type(self):
        """Тест валидации с неверным типом"""
        # Патчим создание директории
        with patch('pathlib.Path.mkdir'):
            # Создаем минимальный мок для db_session
            mock_db = AsyncMock()

            # Создаем реальный объект сервиса
            media_service = MediaService(db=mock_db)

            mock_file = MagicMock()
            mock_file.content_type = "image/gif"
            mock_file.size = 1024

            with pytest.raises(BusinessLogicException) as exc_info:
                await media_service._validate_file(mock_file)  # Добавили await

            assert "File type image/gif not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, media_service):
        """Тест валидации слишком большого файла"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = 15 * 1024 * 1024  # 15 MB

        with pytest.raises(BusinessLogicException) as exc_info:
            await media_service._validate_file(mock_file)

        assert "File too large" in str(exc_info.value)

    def test_generate_file_path_with_filename(self, media_service):
        """Тест генерации пути с именем файла"""
        user_id = 1
        filename = "test.jpg"

        path = media_service._generate_file_path(user_id, filename)

        assert isinstance(path, Path)
        assert "user_1" in str(path)
        assert path.suffix == ".jpg"
        assert len(path.stem) == 36  # UUID length

    def test_generate_file_path_without_filename(self, media_service):
        """Тест генерации пути без имени файла"""
        user_id = 1
        filename = None

        path = media_service._generate_file_path(user_id, filename)

        assert isinstance(path, Path)
        assert "user_1" in str(path)
        assert path.suffix == ".bin"  # Дефолтное расширение
        assert len(path.stem) == 36  # UUID length

    def test_generate_file_path_creates_dirs(self, media_service, tmp_path):
        """Тест создания директорий при генерации пути"""
        with patch('app.services.MediaService.UPLOAD_ROOT', tmp_path):
            user_id = 1
            filename = "test.jpg"

            path = media_service._generate_file_path(user_id, filename)

            assert path.parent.exists()
            assert path.parent.is_dir()