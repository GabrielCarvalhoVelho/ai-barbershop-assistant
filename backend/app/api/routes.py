from fastapi import APIRouter, Depends, Request
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.schemas.health_schema import HealthResponse
from app.controllers.chat_controller import ChatController
from app.controllers.health_controller import HealthController
from app.core.rate_limiter import limiter
from app.core.auth import require_api_key

root_router = APIRouter()
router = APIRouter(prefix="/api/v1")


@root_router.get("/")
@limiter.exempt
async def read_root():
    return {"message": "API is running"}


@router.get("/health", response_model=HealthResponse)
@limiter.exempt
async def health_check():
    return HealthController.check()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest):
    return ChatController.send_message(body)