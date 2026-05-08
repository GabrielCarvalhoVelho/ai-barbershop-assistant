import pytest

from app.core.exceptions import AuthorizationError
from app.core.permissions import ensure_owner_or_admin, is_admin
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


def _make_user(*, user_id: int, company_id: int, role: UserRole) -> User:
    user = User(
        id=user_id,
        company_id=company_id,
        name="Test User",
        phone=f"+551100000{user_id:04d}",
        email=f"user{user_id}@test.com",
        password_hash=hash_password("pass"),
        role=role,
    )
    user.is_active = True
    return user


class TestIsAdmin:
    def test_admin_user_returns_true(self):
        user = _make_user(user_id=1, company_id=1, role=UserRole.ADMIN)
        assert is_admin(user) is True

    def test_customer_user_returns_false(self):
        user = _make_user(user_id=1, company_id=1, role=UserRole.CUSTOMER)
        assert is_admin(user) is False


class TestEnsureOwnerOrAdmin:
    def test_owner_passes(self):
        user = _make_user(user_id=10, company_id=1, role=UserRole.CUSTOMER)
        ensure_owner_or_admin(user, resource_owner_id=10)

    def test_non_owner_customer_raises(self):
        user = _make_user(user_id=10, company_id=1, role=UserRole.CUSTOMER)
        with pytest.raises(AuthorizationError):
            ensure_owner_or_admin(user, resource_owner_id=99)

    def test_admin_same_company_passes(self):
        admin = _make_user(user_id=1, company_id=5, role=UserRole.ADMIN)
        ensure_owner_or_admin(
            admin, resource_owner_id=99, resource_company_id=5
        )

    def test_admin_other_company_raises(self):
        admin = _make_user(user_id=1, company_id=5, role=UserRole.ADMIN)
        with pytest.raises(AuthorizationError):
            ensure_owner_or_admin(
                admin, resource_owner_id=99, resource_company_id=7
            )

    def test_admin_without_company_id_check_passes(self):
        admin = _make_user(user_id=1, company_id=5, role=UserRole.ADMIN)
        ensure_owner_or_admin(admin, resource_owner_id=99)

    def test_owner_check_ignores_company_id(self):
        user = _make_user(user_id=10, company_id=1, role=UserRole.CUSTOMER)
        ensure_owner_or_admin(
            user, resource_owner_id=10, resource_company_id=999
        )

    def test_custom_error_message(self):
        user = _make_user(user_id=10, company_id=1, role=UserRole.CUSTOMER)
        with pytest.raises(AuthorizationError) as exc:
            ensure_owner_or_admin(
                user,
                resource_owner_id=99,
                error_message="Mensagem específica.",
            )
        assert exc.value.message == "Mensagem específica."
