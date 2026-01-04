import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestSyncAPI:
    def test_hello_world_endpoint(self, client):
        response = client.get("/hello-world")
        assert response.status_code == 200


class TestAsyncAPI:
    @pytest.mark.asyncio
    async def test_hello_world_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/hello-world")
            assert response.status_code == 200