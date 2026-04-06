from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.modules.health.controller import HealthController

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
@limiter.exempt
async def health_check(session: AsyncSession = Depends(get_session)):
    response, db_ok = await HealthController.check(session)
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(response),
    )
