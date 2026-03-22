from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Barbershop Assistant"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    api_key: str = ""
    rate_limit: str = "10/minute"
    database_url: str = "sqlite+aiosqlite:///./barbershop.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def warn_wildcard_cors(self):
        if "*" in self.cors_origins and not self.debug:
            raise ValueError(
                "CORS_ORIGINS=['*'] não é permitido em produção. "
                "Use origens específicas ou ative DEBUG=true."
            )
        return self


settings = Settings()
