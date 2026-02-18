# Corporate Microblog API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql)](https://postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-4479A1?style=for-the-badge&logo=sqlalchemy)](https://sqlalchemy.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)](https://docker.com)

A corporate microblogging platform API that allows users to create posts, follow others, and interact with content in a secure and scalable way.

## Features

- **Users**: Profiles, followers/following relationships
- **Tweets**: Create, delete, like/unlike, media attachments
- **Media**: Upload images (JPEG, PNG, GIF, WebP, max 10MB)
- **Auth**: API key authentication with bcrypt

## Tech Stack

- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL 15** - Database
- **Pydantic** - Data validation
- **Docker** - Containerization

## Installation

### Local Development
```
# Clone repository
git clone <your-repo-url>
cd corporate-microblog-api

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Docker
```
docker-compose up -d
```
Server will be available at http://localhost:8000

### API Documentation

Once the server is running, you can access:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`

### Main Endpoints

#### Users
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/users/me` | Get current user | ✅ |
| GET | `/api/users/{user_id}` | Get user by ID | ✅ |
| POST | `/api/users/{user_id}/follow` | Follow a user | ✅ |
| DELETE | `/api/users/{user_id}/follow` | Unfollow a user | ✅ |

#### Tweets
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/tweets/` | Get tweet feed | ✅ |
| POST | `/api/tweets/` | Create tweet | ✅ |
| DELETE | `/api/tweets/{tweet_id}` | Delete tweet | ✅ |
| POST | `/api/tweets/{tweet_id}/likes` | Like tweet | ✅ |
| DELETE | `/api/tweets/{tweet_id}/likes` | Unlike tweet | ✅ |

#### Media
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/medias/` | Upload media | ✅ |

### 📊 Test Coverage

100% code coverage across all modules (492/492 statements) according to pytest-cov

| Module | Coverage |
|--------|----------|
| `app/core/error_handlers.py` | 100% |
| `app/core/exceptions.py` | 100% |
| `app/database.py` | 100% |
| `app/dependencies.py` | 100% |
| `app/main.py` | 100% |
| `app/models.py` | 100% |
| `app/routes/medias.py` | 100% |
| `app/routes/tweets.py` | 100% |
| `app/routes/users.py` | 100% |
| `app/schemas.py` | 100% |
| `app/services.py` | 100% |
| **Total** | **100% (492/492)** |