from fastapi import FastAPI
from app.api.routes import router
from app.core.error_handler import error_handler_middleware
from app.core.logger import setup_logger

app = FastAPI()

setup_logger()

app.middleware("http")(error_handler_middleware)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "API is running"}