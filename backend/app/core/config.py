from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://stefan:changeme@localhost:5432/stefetnitek"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "supersecretkey_change_in_production"
    ADMIN_PASSWORD: str = "admin123"
    CORS_ORIGINS: str = "*"
    ENVIRONMENT: str = "production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
