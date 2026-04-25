from app.core.config import settings
from app.core.logger import get_logger
from app.core.security import create_access_token
from app.models.user import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserMeResponse
from app.modules.auth.service import authenticate_user, register_user
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class AuthController:
    @staticmethod
    async def login(body: LoginRequest, user_repo: UserRepository) -> SuccessResponse:
        logger.info("Login attempt")
        user = await authenticate_user(body.phone, body.password, user_repo)
        token = create_access_token({"sub": str(user.id)})
        expires_in = settings.jwt_access_token_expire_minutes * 60
        logger.info("Login bem-sucedido: user_id=%s", user.id)
        return SuccessResponse(data=TokenResponse(access_token=token, expires_in=expires_in).model_dump())

    @staticmethod
    async def register(request: RegisterRequest, user_repo: UserRepository) -> SuccessResponse:
        logger.info("Registro iniciado")
        user = await register_user(
            phone=request.phone,
            password=request.password,
            name=request.name,
            email=request.email,
            user_repo=user_repo,
        )
        token = create_access_token({"sub": str(user.id)})
        expires_in = settings.jwt_access_token_expire_minutes * 60
        logger.info("Registro concluído: user_id=%s", user.id)
        return SuccessResponse(data=TokenResponse(access_token=token, expires_in=expires_in).model_dump())

    @staticmethod
    async def me(current_user: User) -> SuccessResponse:
        return SuccessResponse(data=UserMeResponse.model_validate(current_user).model_dump())
