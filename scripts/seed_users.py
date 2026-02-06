import asyncio
import sys
from pathlib import Path
import json
import secrets


sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models import User, ApiKey, Base

DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/corporative_microblog_api"


async def recreate_db():
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()

async def seed_users():
    """Create 3 users for testing API"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        users_data = [
            {"name": "Alice Developer"},
            {"name": "Bob Tester"},
            {"name": "Charly Manager"}
        ]

        users_info = []

        for data in users_data:
            user = User(**data)
            session.add(user)
            await session.flush()

            api_key_value = secrets.token_urlsafe(32)
            key_prefix = api_key_value[:8]
            key_hash = ApiKey.hash_key(api_key_value)

            api_key = ApiKey(
                user_id=user.id,
                key_prefix=key_prefix,
                key_hash=key_hash,
            )
            session.add(api_key)

            users_info.append({
                "username": user.name,
                "user_id": user.id,
                "api_key": api_key_value
            })

        await session.commit()

        with open('test_users.json', 'w') as f:
            json.dump([
                info
                for info in users_info
            ], f, indent=2, ensure_ascii=False)

        print(f"\n Информация о пользователях сохранена в test_users.json")

        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(recreate_db())
    asyncio.run(seed_users())