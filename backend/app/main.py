from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.api.routes import router
from app.core.error_handler import (
    business_exception_handler,
    error_handler_middleware,
    validation_exception_handler,
)
from app.core.exceptions import BusinessError
from app.core.logger import setup_logger

app = FastAPI()

setup_logger()

app.middleware("http")(error_handler_middleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(BusinessError, business_exception_handler)

app.include_router(router)