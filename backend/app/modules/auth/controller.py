from app.core.logger import get_logger
from app.core.security import create_access_token
from app.models.user import User
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserMeResponse
from app.modules.auth.service import authenticate_user
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class AuthController:
    @staticmethod
    async def login(request: LoginRequest, user_repo: UserRepository) -> SuccessResponse:
        logger.info("Login: email=%s", request.email)
        user = await authenticate_user(request.email, request.password, user_repo)
        token = create_access_token({"sub": str(user.id)})
        logger.info("Login bem-sucedido: user_id=%s", user.id)
        return SuccessResponse(data=TokenResponse(access_token=token).model_dump())

    @staticmethod
    async def me(current_user: User) -> SuccessResponse:
        return SuccessResponse(data=UserMeResponse.model_validate(current_user).model_dump())
