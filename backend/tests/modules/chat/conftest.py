import pytest

from app.core.security import create_access_token


@pytest.fixture
def chat_token():
    """JWT para user_id=1 (company_id=1) — criado pelo setup_db global."""
    return create_access_token({"sub": "1"})


@pytest.fixture
def auth_headers(chat_token):
    return {"Authorization": f"Bearer {chat_token}"}


@pytest.fixture
def user2_token():
    """JWT para user_id=2 (company_id=2) — para testes de IDOR."""
    return create_access_token({"sub": "2"})


@pytest.fixture
def user2_headers(user2_token):
    return {"Authorization": f"Bearer {user2_token}"}
