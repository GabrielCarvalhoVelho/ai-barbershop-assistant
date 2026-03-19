from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest
from app.services.chat_service import generate_response

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/chat")
def chat(request: ChatRequest):
    response = generate_response(request.message)
    return {"response": response}