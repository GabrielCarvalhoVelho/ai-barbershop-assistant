from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.api.routes import root_router, router
from app.core.error_handler import (
    business_exception_handler,
    error_handler_middleware,
    validation_exception_handler,
)
from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.logger import setup_logger
from app.core.rate_limiter import limiter

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.state.limiter = limiter

setup_logger()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)
app.middleware("http")(error_handler_middleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(BusinessError, business_exception_handler)

app.include_router(root_router)
app.include_router(router)