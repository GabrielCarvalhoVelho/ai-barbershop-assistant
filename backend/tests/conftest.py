import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.rate_limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)
