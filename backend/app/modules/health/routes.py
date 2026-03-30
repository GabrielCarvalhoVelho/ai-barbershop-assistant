from fastapi import APIRouter

from app.core.rate_limiter import limiter
from app.modules.health.controller import HealthController
from app.schemas.base_schema import SuccessResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=SuccessResponse)
@limiter.exempt
async def health_check():
    return HealthController.check()
