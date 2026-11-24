"""A crash still returns CORS headers, so the browser shows the real 500."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_unhandled_error_keeps_cors_headers():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app)
    response = client.get("/boom", headers={"Origin": "http://localhost:4321"})
    assert response.status_code == 500
    assert response.json()["detail"].startswith("Something went wrong")
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"
