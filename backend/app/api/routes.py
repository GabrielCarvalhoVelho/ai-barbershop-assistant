from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.schemas.health_schema import HealthResponse
from app.services.chat_service import generate_response

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return generate_response(request.message)