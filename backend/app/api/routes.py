from fastapi import APIRouter

from app.core.rate_limiter import limiter
from app.schemas.base_schema import SuccessResponse

root_router = APIRouter()


@root_router.get("/", response_model=SuccessResponse)
@limiter.exempt
async def read_root():
    return SuccessResponse(data={"message": "API is running"})
