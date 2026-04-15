from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.api.routes import root_router
from app.core.config import settings
from app.db.seed import seed_dev_data
from app.core.error_handler import (
    app_exception_handler,
    error_handler_middleware,
    http_exception_handler,
    integrity_error_handler,
    operational_error_handler,
    rate_limit_exception_handler,
    sqlalchemy_error_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppError
from app.core.logger import setup_logger
from app.core.middleware import RequestIDMiddleware
from app.core.rate_limiter import limiter
from app.db.database import async_session, create_tables, dispose_engine
from app.modules.chat.conversation_routes import router as conversation_router
from app.modules.chat.routes import router as chat_router
from app.modules.auth.routes import router as auth_router
from app.modules.health.routes import router as health_router
import app.models  # noqa: F401 — registra models no SQLAlchemy antes do create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.debug:
        await create_tables()
        async with async_session() as session:
            await seed_dev_data(session)
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.state.limiter = limiter

setup_logger()

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)
app.middleware("http")(error_handler_middleware)

# Exception handlers — ordem: específicos primeiro, genéricos depois
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)

app.include_router(root_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(health_router)
app.include_router(auth_router)
