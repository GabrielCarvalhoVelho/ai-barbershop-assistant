from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "AI Barbershop Assistant"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    api_key: str = ""
    rate_limit: str = "10/minute"
    database_url: str = "sqlite+aiosqlite:///./barbershop.db"
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_max_history: int = 10

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
    }

    @model_validator(mode="after")
    def validate_production_settings(self):
        if not self.debug:
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS_ORIGINS=['*'] não é permitido em produção. "
                    "Use origens específicas ou ative DEBUG=true."
                )
            if not self.api_key:
                raise ValueError(
                    "API_KEY é obrigatória em produção. "
                    "Defina API_KEY no .env ou ative DEBUG=true."
                )
            if not self.groq_api_key:
                raise ValueError(
                    "GROQ_API_KEY é obrigatória em produção. "
                    "Defina GROQ_API_KEY no .env ou ative DEBUG=true."
                )
        return self


settings = Settings()
