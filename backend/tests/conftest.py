from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from tenacity import wait_none

from app import ai_client
from app.db import database as db
from app.main import app


@pytest.fixture
def session() -> Iterator[Session]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as test_session:
        yield test_session

    test_engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[db.get_session] = lambda: session

    # No context manager: do not run the production lifespan in API tests.
    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post(
        "/auth/register",
        json={"username": "test-user", "password": "a-secure-password"},
    )
    assert response.status_code == 201
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    return client


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    """Keep retry tests instant: same attempts, no sleeping between them."""
    monkeypatch.setattr(ai_client, "RETRY_WAIT", wait_none())


@pytest.fixture
def fake_ai():
    """Install a fake ai-service for one test; returns the list of requests seen."""
    calls: list[httpx.Request] = []

    def install(handler):
        def recording(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        def override():
            client = ai_client.AIClient(
                "http://ai-service.test", transport=httpx.MockTransport(recording)
            )
            yield client
            client.close()

        app.dependency_overrides[ai_client.get_ai_client] = override
        return calls

    return install
