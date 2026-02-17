import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import inspect, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Relationship

from app.models import User, Follow, ApiKey, Tweet, Media, Like
from app.database import Base


class TestUser:
    """Тесты для модели User"""

    def test_user_model_structure(self):
        """Тест структуры модели User"""
        assert hasattr(User, '__tablename__')
        assert User.__tablename__ == 'users'

        # Проверяем наличие всех полей
        assert hasattr(User, 'id')
        assert hasattr(User, 'name')
        assert hasattr(User, 'followers')
        assert hasattr(User, 'following')
        assert hasattr(User, 'api_keys')
        assert hasattr(User, 'tweets')
        assert hasattr(User, 'likes')

    def test_user_columns(self):
        """Тест колонок модели User"""
        columns = inspect(User).columns

        # Проверяем колонку id
        id_col = columns.get('id')
        assert id_col is not None
        assert id_col.primary_key is True
        assert id_col.nullable is False

        # Проверяем колонку name
        name_col = columns.get('name')
        assert name_col is not None
        assert name_col.nullable is False
        assert isinstance(name_col.type, String)
        assert name_col.type.length == 255

    def test_user_relationships(self):
        """Тест отношений модели User"""
        mapper = inspect(User)

        # Проверяем отношение followers
        followers_rel = mapper.relationships.get('followers')
        assert followers_rel is not None
        assert followers_rel.direction.name == 'MANYTOMANY'
        assert followers_rel.secondary.name == 'followings'
        assert followers_rel.lazy == 'selectin'

        # Проверяем отношение following
        following_rel = mapper.relationships.get('following')
        assert following_rel is not None
        assert following_rel.direction.name == 'MANYTOMANY'
        assert following_rel.secondary.name == 'followings'
        assert following_rel.lazy == 'selectin'

        # Проверяем отношение api_keys
        api_keys_rel = mapper.relationships.get('api_keys')
        assert api_keys_rel is not None
        assert api_keys_rel.direction.name == 'ONETOMANY'
        # Проверяем наличие нужных опций каскада
        cascade = api_keys_rel.cascade
        assert 'delete' in cascade
        assert 'delete-orphan' in cascade
        assert api_keys_rel.lazy == 'selectin'  # <-- ИСПРАВЛЕНО

        # Проверяем отношение tweets
        tweets_rel = mapper.relationships.get('tweets')
        assert tweets_rel is not None
        assert tweets_rel.direction.name == 'ONETOMANY'
        # Проверяем наличие нужных опций каскада
        cascade = tweets_rel.cascade
        assert 'delete' in cascade
        assert 'delete-orphan' in cascade
        assert tweets_rel.lazy == 'selectin'  # <-- ИСПРАВЛЕНО

        # Проверяем отношение likes
        likes_rel = mapper.relationships.get('likes')
        assert likes_rel is not None
        assert likes_rel.direction.name == 'ONETOMANY'
        # Проверяем наличие нужных опций каскада
        cascade = likes_rel.cascade
        assert 'delete' in cascade
        assert 'delete-orphan' in cascade
        assert likes_rel.lazy == 'selectin'  # <-- ИСПРАВЛЕНО

    def test_user_creation(self):
        """Тест создания экземпляра User"""
        user = User(id=1, name='Test User')

        assert user.id == 1
        assert user.name == 'Test User'
        assert user.followers == []
        assert user.following == []
        assert user.api_keys == []
        assert user.tweets == []
        assert user.likes == []


class TestFollow:
    """Тесты для модели Follow"""

    def test_follow_model_structure(self):
        """Тест структуры модели Follow"""
        assert hasattr(Follow, '__tablename__')
        assert Follow.__tablename__ == 'followings'

        # Проверяем наличие всех полей
        assert hasattr(Follow, 'id')
        assert hasattr(Follow, 'follower_id')
        assert hasattr(Follow, 'following_id')

    def test_follow_columns(self):
        """Тест колонок модели Follow"""
        columns = inspect(Follow).columns

        # Проверяем колонку id
        id_col = columns.get('id')
        assert id_col is not None
        assert id_col.primary_key is True

        # Проверяем колонку follower_id
        follower_col = columns.get('follower_id')
        assert follower_col is not None
        assert follower_col.nullable is False
        assert follower_col.foreign_keys is not None

        # Проверяем колонку following_id
        following_col = columns.get('following_id')
        assert following_col is not None
        assert following_col.nullable is False
        assert following_col.foreign_keys is not None

    def test_follow_constraints(self):
        """Тест ограничений модели Follow"""
        table_args = Follow.__table_args__

        # Проверяем наличие UniqueConstraint
        unique_constraints = [arg for arg in table_args if isinstance(arg, UniqueConstraint)]
        assert len(unique_constraints) == 1

        # Получаем имена колонок из UniqueConstraint
        constraint = unique_constraints[0]
        assert constraint.name == 'uq_follower_following'

        # Преобразуем ColumnCollection в список имен
        column_names = [col.name for col in constraint.columns]
        assert column_names == ['follower_id', 'following_id']

        # Проверяем наличие индексов
        indexes = [arg for arg in table_args if isinstance(arg, Index)]
        assert len(indexes) == 2
        index_names = [idx.name for idx in indexes]
        assert 'ix_follow_follower_following' in index_names
        assert 'ix_follow_following_follower' in index_names

    def test_follow_creation(self):
        """Тест создания экземпляра Follow"""
        follow = Follow(id=1, follower_id=1, following_id=2)

        assert follow.id == 1
        assert follow.follower_id == 1
        assert follow.following_id == 2


class TestApiKey:
    """Тесты для модели ApiKey"""

    def test_apikey_model_structure(self):
        """Тест структуры модели ApiKey"""
        assert hasattr(ApiKey, '__tablename__')
        assert ApiKey.__tablename__ == 'api_keys'

        # Проверяем наличие всех полей
        assert hasattr(ApiKey, 'id')
        assert hasattr(ApiKey, 'user_id')
        assert hasattr(ApiKey, 'key_prefix')
        assert hasattr(ApiKey, 'key_hash')
        assert hasattr(ApiKey, 'user')

    def test_apikey_columns(self):
        """Тест колонок модели ApiKey"""
        columns = inspect(ApiKey).columns

        # Проверяем колонку key_prefix
        prefix_col = columns.get('key_prefix')
        assert prefix_col is not None
        assert prefix_col.nullable is False
        assert prefix_col.unique is True
        assert prefix_col.index is True
        assert isinstance(prefix_col.type, String)
        assert prefix_col.type.length == 8

        # Проверяем колонку key_hash
        hash_col = columns.get('key_hash')
        assert hash_col is not None
        assert hash_col.nullable is False
        assert hash_col.unique is True
        assert hash_col.index is True
        assert isinstance(hash_col.type, String)
        assert hash_col.type.length == 255

    def test_apikey_relationships(self):
        """Тест отношений модели ApiKey"""
        mapper = inspect(ApiKey)

        # Проверяем отношение user
        user_rel = mapper.relationships.get('user')
        assert user_rel is not None
        assert user_rel.direction.name == 'MANYTOONE'
        assert user_rel.lazy == 'joined'

    def test_apikey_hash_key(self):
        """Тест метода hash_key"""
        test_key = "my-secret-api-key"

        with patch('bcrypt.gensalt', return_value=b'salt') as mock_gensalt, \
                patch('bcrypt.hashpw', return_value=b'hashed_key') as mock_hashpw:
            result = ApiKey.hash_key(test_key)

            mock_gensalt.assert_called_once()
            mock_hashpw.assert_called_once_with(test_key.encode(), b'salt')
            assert result == 'hashed_key'

    def test_apikey_verify_key_success(self):
        """Тест успешной верификации ключа"""
        api_key = ApiKey()
        api_key.key_hash = 'stored_hash'
        test_key = "test-key"

        with patch('bcrypt.checkpw', return_value=True) as mock_checkpw:
            result = api_key.verify_key(test_key)

            mock_checkpw.assert_called_once_with(test_key.encode(), 'stored_hash'.encode())
            assert result is True

    def test_apikey_verify_key_failure(self):
        """Тест неуспешной верификации ключа"""
        api_key = ApiKey()
        api_key.key_hash = 'stored_hash'
        test_key = "wrong-key"

        with patch('bcrypt.checkpw', return_value=False) as mock_checkpw:
            result = api_key.verify_key(test_key)

            mock_checkpw.assert_called_once()
            assert result is False

    def test_apikey_creation(self):
        """Тест создания экземпляра ApiKey"""
        api_key = ApiKey(
            id=1,
            user_id=1,
            key_prefix='abc123',
            key_hash='hashed_value'
        )

        assert api_key.id == 1
        assert api_key.user_id == 1
        assert api_key.key_prefix == 'abc123'
        assert api_key.key_hash == 'hashed_value'


class TestTweet:
    """Тесты для модели Tweet"""

    def test_tweet_model_structure(self):
        """Тест структуры модели Tweet"""
        assert hasattr(Tweet, '__tablename__')
        assert Tweet.__tablename__ == 'tweets'

        # Проверяем наличие всех полей
        assert hasattr(Tweet, 'id')
        assert hasattr(Tweet, 'user_id')
        assert hasattr(Tweet, 'content')
        assert hasattr(Tweet, 'likes_counter')
        assert hasattr(Tweet, 'author')
        assert hasattr(Tweet, 'media')
        assert hasattr(Tweet, 'likes')

    def test_tweet_columns(self):
        """Тест колонок модели Tweet"""
        columns = inspect(Tweet).columns

        # Проверяем колонку content
        content_col = columns.get('content')
        assert content_col is not None
        assert content_col.nullable is False
        assert isinstance(content_col.type, String)
        assert content_col.type.length == 1000

        # Проверяем колонку likes_counter
        likes_col = columns.get('likes_counter')
        assert likes_col is not None

        # Проверяем default значение
        assert likes_col.default is not None
        assert likes_col.default.arg == 0  # <-- доступ к значению через .arg

        # Проверяем индекс
        assert likes_col.index is True

    def test_tweet_relationships(self):
        """Тест отношений модели Tweet"""
        mapper = inspect(Tweet)

        # Проверяем отношение author
        author_rel = mapper.relationships.get('author')
        assert author_rel is not None
        assert author_rel.direction.name == 'MANYTOONE'

        # Проверяем отношение media
        media_rel = mapper.relationships.get('media')
        assert media_rel is not None
        assert media_rel.direction.name == 'ONETOMANY'

        # Проверяем каскад
        cascade = media_rel.cascade
        assert 'delete' in cascade
        assert 'delete-orphan' in cascade

        assert media_rel.lazy == 'selectin'

        # Проверяем отношение likes
        likes_rel = mapper.relationships.get('likes')
        assert likes_rel is not None
        assert likes_rel.direction.name == 'ONETOMANY'

        # Проверяем каскад
        cascade = likes_rel.cascade
        assert 'delete' in cascade
        assert 'delete-orphan' in cascade

        assert likes_rel.lazy == 'selectin'

    def test_tweet_creation(self):
        """Тест создания экземпляра Tweet"""
        tweet = Tweet(
            id=1,
            user_id=1,
            content='Test tweet content',
            likes_counter=5
        )

        assert tweet.id == 1
        assert tweet.user_id == 1
        assert tweet.content == 'Test tweet content'
        assert tweet.likes_counter == 5
        assert tweet.media == []
        assert tweet.likes == []


class TestMedia:
    """Тесты для модели Media"""

    def test_media_model_structure(self):
        """Тест структуры модели Media"""
        assert hasattr(Media, '__tablename__')
        assert Media.__tablename__ == 'medias'

        # Проверяем наличие всех полей
        assert hasattr(Media, 'id')
        assert hasattr(Media, 'link')
        assert hasattr(Media, 'tweet_id')
        assert hasattr(Media, 'tweet')

    def test_media_columns(self):
        """Тест колонок модели Media"""
        columns = inspect(Media).columns

        # Проверяем колонку link
        link_col = columns.get('link')
        assert link_col is not None
        assert link_col.nullable is True
        assert isinstance(link_col.type, String)
        assert link_col.type.length == 500

        # Проверяем колонку tweet_id
        tweet_id_col = columns.get('tweet_id')
        assert tweet_id_col is not None
        assert tweet_id_col.nullable is True
        assert tweet_id_col.index is True
        assert tweet_id_col.foreign_keys is not None

    def test_media_relationships(self):
        """Тест отношений модели Media"""
        mapper = inspect(Media)

        # Проверяем отношение tweet
        tweet_rel = mapper.relationships.get('tweet')
        assert tweet_rel is not None
        assert tweet_rel.direction.name == 'MANYTOONE'

    def test_media_creation(self):
        """Тест создания экземпляра Media"""
        media = Media(
            id=1,
            link='/uploads/test.jpg',
            tweet_id=1
        )

        assert media.id == 1
        assert media.link == '/uploads/test.jpg'
        assert media.tweet_id == 1


class TestLike:
    """Тесты для модели Like"""

    def test_like_model_structure(self):
        """Тест структуры модели Like"""
        assert hasattr(Like, '__tablename__')
        assert Like.__tablename__ == 'likes'

        # Проверяем наличие всех полей
        assert hasattr(Like, 'tweet_id')
        assert hasattr(Like, 'user_id')
        assert hasattr(Like, 'tweet')
        assert hasattr(Like, 'user')

    def test_like_columns(self):
        """Тест колонок модели Like"""
        columns = inspect(Like).columns

        # Проверяем колонку tweet_id
        tweet_id_col = columns.get('tweet_id')
        assert tweet_id_col is not None
        assert tweet_id_col.primary_key is True
        assert tweet_id_col.nullable is False

        # Проверяем колонку user_id
        user_id_col = columns.get('user_id')
        assert user_id_col is not None
        assert user_id_col.primary_key is True
        assert user_id_col.nullable is False

    def test_like_constraints(self):
        """Тест ограничений модели Like"""
        table_args = Like.__table_args__

        # Проверяем наличие UniqueConstraint
        unique_constraints = [arg for arg in table_args if isinstance(arg, UniqueConstraint)]
        assert len(unique_constraints) == 1

        constraint = unique_constraints[0]
        assert constraint.name == 'uq_like_tweet_user'

        # Преобразуем ColumnCollection в список имен
        column_names = [col.name for col in constraint.columns]
        assert column_names == ['tweet_id', 'user_id']

        # Проверяем наличие индексов
        indexes = [arg for arg in table_args if isinstance(arg, Index)]
        assert len(indexes) == 2
        index_names = [idx.name for idx in indexes]
        assert 'ix_like_tweet_user' in index_names
        assert 'ix_like_user_tweet' in index_names

    def test_like_relationships(self):
        """Тест отношений модели Like"""
        mapper = inspect(Like)

        # Проверяем отношение tweet
        tweet_rel = mapper.relationships.get('tweet')
        assert tweet_rel is not None
        assert tweet_rel.direction.name == 'MANYTOONE'

        # Проверяем отношение user
        user_rel = mapper.relationships.get('user')
        assert user_rel is not None
        assert user_rel.direction.name == 'MANYTOONE'

    def test_like_creation(self):
        """Тест создания экземпляра Like"""
        like = Like(tweet_id=1, user_id=2)

        assert like.tweet_id == 1
        assert like.user_id == 2


class TestModelRelationships:
    """Тесты для проверки связей между моделями"""

    def test_user_tweet_relationship(self):
        """Тест связи User - Tweet"""
        user = User(id=1, name='Test User')
        tweet = Tweet(id=1, user_id=1, content='Test')

        user.tweets.append(tweet)

        assert len(user.tweets) == 1
        assert user.tweets[0] == tweet
        assert tweet.author == user

    def test_tweet_media_relationship(self):
        """Тест связи Tweet - Media"""
        tweet = Tweet(id=1, user_id=1, content='Test')
        media = Media(id=1, link='/test.jpg', tweet_id=1)

        tweet.media.append(media)

        assert len(tweet.media) == 1
        assert tweet.media[0] == media
        assert media.tweet == tweet

    def test_user_like_tweet_relationship(self):
        """Тест связи User - Like - Tweet"""
        user = User(id=1, name='Test User')
        tweet = Tweet(id=1, user_id=2, content='Test')
        like = Like(tweet_id=1, user_id=1)

        user.likes.append(like)
        tweet.likes.append(like)

        assert len(user.likes) == 1
        assert len(tweet.likes) == 1
        assert user.likes[0] == like
        assert tweet.likes[0] == like
        assert like.user == user
        assert like.tweet == tweet

    def test_user_api_keys_relationship(self):
        """Тест связи User - ApiKey"""
        user = User(id=1, name='Test User')
        api_key = ApiKey(
            id=1,
            user_id=1,
            key_prefix='test',
            key_hash='hash'
        )

        user.api_keys.append(api_key)

        assert len(user.api_keys) == 1
        assert user.api_keys[0] == api_key
        assert api_key.user == user

    def test_follow_relationship(self):
        """Тест связи подписок"""
        user1 = User(id=1, name='User 1')
        user2 = User(id=2, name='User 2')

        # Проверяем, что отношения настроены правильно
        assert hasattr(user1, 'followers')
        assert hasattr(user1, 'following')
        assert hasattr(user2, 'followers')
        assert hasattr(user2, 'following')