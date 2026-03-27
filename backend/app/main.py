from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import root_router, router
from app.core.config import settings
from app.core.error_handler import (
    app_exception_handler,
    error_handler_middleware,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppError
from app.core.logger import setup_logger
from app.core.rate_limiter import limiter
from app.db.database import create_tables, dispose_engine
import app.models  # noqa: F401 — registra models no SQLAlchemy antes do create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
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
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AppError, app_exception_handler)

app.include_router(root_router)
app.include_router(router)