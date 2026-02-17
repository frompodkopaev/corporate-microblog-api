import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas import (
    BasicResponse, TweetCreate, TweetInfo, TweetResponse,
    TweetFeed, MediaResponse, UserBasic, UserFollowings,
    UserResponse
)
from app.models import User, Tweet, Media


class TestBasicResponse:
    """Тесты для базовой схемы ответа"""

    def test_basic_response_default(self):
        """Тест создания BasicResponse со значением по умолчанию"""
        response = BasicResponse()
        assert response.result is True

    def test_basic_response_custom(self):
        """Тест создания BasicResponse с кастомным значением"""
        response = BasicResponse(result=False)
        assert response.result is False


class TestTweetCreate:
    """Тесты для схемы создания твита"""

    def test_tweet_create_valid(self):
        """Тест создания валидного TweetCreate"""
        tweet = TweetCreate(
            content="Test tweet content",
            media_ids=[1, 2, 3]
        )
        assert tweet.tweet_data == "Test tweet content"
        assert tweet.media_ids == [1, 2, 3]

    def test_tweet_create_alias_works(self):
        """Тест работы alias для content"""
        # Создаем через основное поле
        tweet = TweetCreate(content="Test content")

        # Проверяем доступ через property
        assert tweet.tweet_data == "Test content"

        # Проверяем сериализацию без alias
        dump = tweet.model_dump()
        assert dump["tweet_data"] == "Test content"
        assert "content" not in dump

        # Проверяем сериализацию с alias
        dump_alias = tweet.model_dump(by_alias=True)
        assert dump_alias["content"] == "Test content"
        assert "tweet_data" not in dump_alias

    def test_tweet_create_min_length(self):
        """Тест валидации минимальной длины"""
        with pytest.raises(ValidationError) as exc_info:
            TweetCreate(content="")  # Пустая строка

        errors = exc_info.value.errors()
        assert any(err['type'] == 'string_too_short' for err in errors)

    def test_tweet_create_max_length(self):
        """Тест валидации максимальной длины"""
        long_content = "a" * 1001
        with pytest.raises(ValidationError) as exc_info:
            TweetCreate(content=long_content)

        errors = exc_info.value.errors()
        assert any(err['type'] == 'string_too_long' for err in errors)

    def test_tweet_create_media_ids_default(self):
        """Тест значения по умолчанию для media_ids"""
        tweet = TweetCreate(content="Test content")
        assert tweet.media_ids == []  # default_factory=list

    def test_tweet_create_media_ids_none(self):
        """Тест передачи None в media_ids"""
        # Проверяем, что media_ids может быть None
        tweet = TweetCreate(content="Test content", media_ids=None)
        assert tweet.media_ids is None  # Проверяем, что None остается None

        # ИЛИ проверяем, что если не передавать media_ids, то используется значение по умолчанию
        tweet2 = TweetCreate(content="Test content")
        assert tweet2.media_ids == []

    def test_tweet_create_media_ids_custom(self):
        """Тест передачи кастомных media_ids"""
        tweet = TweetCreate(content="Test", media_ids=[5, 6, 7])
        assert tweet.media_ids == [5, 6, 7]

    def test_tweet_create_serialization(self):
        """Тест сериализации TweetCreate"""
        tweet = TweetCreate(content="Test", media_ids=[1, 2])

        # По умолчанию (без alias)
        data = tweet.model_dump()
        assert "tweet_data" in data
        assert "media_ids" in data
        assert "content" not in data

        # С alias
        data_alias = tweet.model_dump(by_alias=True)
        assert "content" in data_alias
        assert "media_ids" in data_alias


class TestUserBasic:
    """Тесты для базовой схемы пользователя"""

    def test_user_basic_creation(self):
        """Тест создания UserBasic"""
        user = UserBasic(id=1, name="Test User")
        assert user.id == 1
        assert user.name == "Test User"

    def test_user_basic_from_attributes(self):
        """Тест создания UserBasic из атрибутов модели"""
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.name = "Test User"

        user = UserBasic.model_validate(mock_user)
        assert user.id == 1
        assert user.name == "Test User"

    def test_user_basic_validation(self):
        """Тест валидации полей UserBasic"""
        # Проверка обязательных полей
        with pytest.raises(ValidationError):
            UserBasic(name="Test")  # пропущен id

        with pytest.raises(ValidationError):
            UserBasic(id=1)  # пропущено name


class TestTweetInfo:
    """Тесты для схемы информации о твите"""

    def test_tweet_info_creation(self):
        """Тест создания TweetInfo напрямую"""
        author = UserBasic(id=1, name="Author")
        likes = [
            UserBasic(id=2, name="User 2"),
            UserBasic(id=3, name="User 3")
        ]

        tweet_info = TweetInfo(
            id=1,
            content="Test content",
            attachments=["/img1.jpg", "/img2.jpg"],
            author=author,
            likes=likes
        )

        assert tweet_info.id == 1
        assert tweet_info.content == "Test content"
        assert tweet_info.attachments == ["/img1.jpg", "/img2.jpg"]
        assert tweet_info.author == author
        assert tweet_info.likes == likes

    def test_tweet_info_from_orm(self):
        """Тест создания TweetInfo из ORM модели"""
        # Создаем мок твита
        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = 1
        mock_tweet.content = "Test content"

        # Мокаем медиа
        mock_media1 = MagicMock(spec=Media)
        mock_media1.link = "/img1.jpg"
        mock_media2 = MagicMock(spec=Media)
        mock_media2.link = "/img2.jpg"
        mock_tweet.media = [mock_media1, mock_media2]

        # Мокаем автора
        mock_author = MagicMock(spec=User)
        mock_author.id = 10
        mock_author.name = "Author"
        mock_tweet.author = mock_author

        # Мокаем лайки
        mock_liker1 = MagicMock(spec=User)
        mock_liker1.id = 20
        mock_liker1.name = "Liker 1"
        mock_liker2 = MagicMock(spec=User)
        mock_liker2.id = 21
        mock_liker2.name = "Liker 2"

        mock_like1 = MagicMock()
        mock_like1.user = mock_liker1
        mock_like2 = MagicMock()
        mock_like2.user = mock_liker2
        mock_tweet.likes = [mock_like1, mock_like2]

        # Тестируем from_orm
        tweet_info = TweetInfo.from_orm(mock_tweet)

        assert tweet_info.id == 1
        assert tweet_info.content == "Test content"
        assert tweet_info.attachments == ["/img1.jpg", "/img2.jpg"]
        assert tweet_info.author.id == 10
        assert tweet_info.author.name == "Author"
        assert len(tweet_info.likes) == 2
        assert tweet_info.likes[0].id == 20
        assert tweet_info.likes[0].name == "Liker 1"
        assert tweet_info.likes[1].id == 21
        assert tweet_info.likes[1].name == "Liker 2"

    def test_tweet_info_from_orm_empty_relations(self):
        """Тест создания TweetInfo с пустыми отношениями"""
        mock_tweet = MagicMock(spec=Tweet)
        mock_tweet.id = 1
        mock_tweet.content = "Test"
        mock_tweet.media = []
        mock_tweet.author = MagicMock(spec=User)
        mock_tweet.author.id = 1
        mock_tweet.author.name = "Author"
        mock_tweet.likes = []

        tweet_info = TweetInfo.from_orm(mock_tweet)

        assert tweet_info.attachments == []
        assert tweet_info.likes == []

    def test_tweet_info_config(self):
        """Тест конфигурации TweetInfo"""
        assert TweetInfo.model_config.get("from_attributes") is True


class TestTweetResponse:
    """Тесты для схемы ответа с твитом"""

    def test_tweet_response_creation(self):
        """Тест создания TweetResponse"""
        response = TweetResponse(tweet_id=123)
        assert response.result is True  # из BasicResponse
        assert response.tweet_id == 123

    def test_tweet_response_inheritance(self):
        """Тест наследования от BasicResponse"""
        assert issubclass(TweetResponse, BasicResponse)
        response = TweetResponse(tweet_id=123, result=False)
        assert response.result is False


class TestTweetFeed:
    """Тесты для схемы ленты твитов"""

    def test_tweet_feed_creation(self):
        """Тест создания TweetFeed"""
        feed = TweetFeed()
        assert feed.result is True
        assert feed.tweets == []

    def test_tweet_feed_with_tweets(self):
        """Тест создания TweetFeed с твитами"""
        tweet_info1 = MagicMock(spec=TweetInfo)
        tweet_info2 = MagicMock(spec=TweetInfo)

        feed = TweetFeed(tweets=[tweet_info1, tweet_info2])
        assert len(feed.tweets) == 2

    def test_tweet_feed_create_method(self):
        """Тест фабричного метода create"""
        # Создаем моки твитов
        mock_tweet1 = MagicMock(spec=Tweet)
        mock_tweet2 = MagicMock(spec=Tweet)

        with patch('app.schemas.TweetInfo.from_orm') as mock_from_orm:
            mock_info1 = MagicMock(spec=TweetInfo)
            mock_info2 = MagicMock(spec=TweetInfo)
            mock_from_orm.side_effect = [mock_info1, mock_info2]

            feed = TweetFeed.create([mock_tweet1, mock_tweet2])

            assert feed.result is True
            assert feed.tweets == [mock_info1, mock_info2]
            assert mock_from_orm.call_count == 2


class TestMediaResponse:
    """Тесты для схемы ответа с медиа"""

    def test_media_response_creation(self):
        """Тест создания MediaResponse"""
        response = MediaResponse(media_id=456)
        # Обратите внимание: в коде media_id: int = True - это баг? Должно быть значение
        assert response.media_id == 456

    def test_media_response_config(self):
        """Тест конфигурации MediaResponse"""
        assert MediaResponse.model_config.get("from_attributes") is True


class TestUserFollowings:
    """Тесты для схемы пользователя с подписками"""

    def test_user_followings_creation(self):
        """Тест создания UserFollowings напрямую"""
        followers = [
            UserBasic(id=2, name="Follower 1"),
            UserBasic(id=3, name="Follower 2")
        ]
        following = [
            UserBasic(id=4, name="Following 1")
        ]

        user = UserFollowings(
            id=1,
            name="Test User",
            followers=followers,
            following=following
        )

        assert user.id == 1
        assert user.name == "Test User"
        assert len(user.followers) == 2
        assert len(user.following) == 1

    @pytest.mark.asyncio
    async def test_user_followings_from_orm_async(self):
        """Тест асинхронного создания UserFollowings из ORM"""
        # Создаем реальные объекты User
        mock_user = User(id=1, name="Test User")

        # Создаем реальных пользователей для followers и following
        follower1 = User(id=2, name="Follower 1")
        follower2 = User(id=3, name="Follower 2")
        following1 = User(id=4, name="Following 1")

        # Создаем списки
        mock_followers = [follower1, follower2]
        mock_following = [following1]

        # Создаем мок для awaitable_attrs
        mock_awaitable_attrs = AsyncMock()

        # Создаем корутины
        async def get_followers():
            return mock_followers

        async def get_following():
            return mock_following

        mock_awaitable_attrs.followers = get_followers()
        mock_awaitable_attrs.following = get_following()

        # Патчим awaitable_attrs
        with patch.object(User, 'awaitable_attrs', mock_awaitable_attrs):
            user_info = await UserFollowings.from_orm_async(mock_user)

            assert user_info.id == 1
            assert user_info.name == "Test User"
            assert len(user_info.followers) == 2
            assert user_info.followers[0].id == 2
            assert user_info.followers[0].name == "Follower 1"
            assert user_info.followers[1].id == 3
            assert len(user_info.following) == 1
            assert user_info.following[0].id == 4
            assert user_info.following[0].name == "Following 1"

    @pytest.mark.asyncio
    async def test_user_followings_from_orm_async_empty(self):
        """Тест асинхронного создания с пустыми списками"""
        mock_user = AsyncMock(spec=User)
        mock_user.id = 1
        mock_user.name = "Test User"

        # Создаем мок для awaitable_attrs
        mock_awaitable_attrs = AsyncMock()

        # followers и following должны быть корутинами, которые можно await
        # Создаем AsyncMock и сразу его вызываем, чтобы получить корутину
        mock_awaitable_attrs.followers = AsyncMock(return_value=[])()
        mock_awaitable_attrs.following = AsyncMock(return_value=[])()

        mock_user.awaitable_attrs = mock_awaitable_attrs

        user_info = await UserFollowings.from_orm_async(mock_user)

        assert user_info.followers == []
        assert user_info.following == []


class TestUserResponse:
    """Тесты для схемы ответа с пользователем"""

    def test_user_response_creation(self):
        """Тест создания UserResponse напрямую"""
        user_followings = MagicMock(spec=UserFollowings)

        response = UserResponse(user=user_followings)
        assert response.result is True
        assert response.user == user_followings

    @pytest.mark.asyncio
    async def test_user_response_create(self):
        """Тест асинхронного фабричного метода create"""
        mock_user = AsyncMock(spec=User)

        # Мокаем UserFollowings.from_orm_async
        mock_user_info = MagicMock(spec=UserFollowings)

        with patch('app.schemas.UserFollowings.from_orm_async',
                   new_callable=AsyncMock, return_value=mock_user_info) as mock_from_orm:
            response = await UserResponse.create(mock_user)

            assert response.result is True
            assert response.user == mock_user_info
            mock_from_orm.assert_awaited_once_with(mock_user)

    def test_user_response_config(self):
        """Тест конфигурации UserResponse"""
        assert UserResponse.model_config.get("from_attributes") is True


class TestSchemaIntegration:
    """Интеграционные тесты для схем"""

    def test_tweet_feed_with_tweet_info(self):
        """Тест создания TweetFeed с реальными TweetInfo"""
        author = UserBasic(id=1, name="Author")
        likes = [UserBasic(id=2, name="Liker")]

        tweet_info = TweetInfo(
            id=1,
            content="Test",
            attachments=["/img.jpg"],
            author=author,
            likes=likes
        )

        feed = TweetFeed(tweets=[tweet_info])

        assert feed.tweets[0].id == 1
        assert feed.tweets[0].author.name == "Author"
        assert feed.tweets[0].likes[0].name == "Liker"

    def test_user_response_with_user_followings(self):
        """Тест создания UserResponse с реальным UserFollowings"""
        followers = [UserBasic(id=2, name="Follower")]
        following = [UserBasic(id=3, name="Following")]

        user_followings = UserFollowings(
            id=1,
            name="User",
            followers=followers,
            following=following
        )

        response = UserResponse(user=user_followings)

        assert response.user.id == 1
        assert response.user.followers[0].name == "Follower"
        assert response.user.following[0].name == "Following"

    def test_json_serialization(self):
        """Тест сериализации в JSON"""
        tweet_create = TweetCreate(content="Test", media_ids=[1, 2])

        # Сериализуем с by_alias=True, чтобы использовать alias 'content'
        json_data = tweet_create.model_dump_json(by_alias=True)
        assert '"content"' in json_data

        # Десериализуем - ожидаем поле 'content'
        parsed = TweetCreate.model_validate_json(json_data)
        assert parsed.tweet_data == "Test"
        assert parsed.media_ids == [1, 2]


class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_tweet_create_media_ids_mixed_types(self):
        """Тест media_ids с разными типами (должны быть int)"""
        # Pydantic должен преобразовать строки в int если возможно
        tweet = TweetCreate(content="Test", media_ids=["1", "2", "3"])
        assert all(isinstance(x, int) for x in tweet.media_ids)
        assert tweet.media_ids == [1, 2, 3]

    def test_tweet_info_empty_attachments(self):
        """Тест TweetInfo с пустыми attachments"""
        author = UserBasic(id=1, name="Author")
        tweet_info = TweetInfo(
            id=1,
            content="Test",
            attachments=[],
            author=author,
            likes=[]
        )
        assert tweet_info.attachments == []

    def test_user_basic_str_representation(self):
        """Тест строкового представления"""
        user = UserBasic(id=1, name="Test")
        # Pydantic модели имеют хорошее repr
        repr_str = repr(user)
        assert "id=1" in repr_str
        assert "name='Test'" in repr_str