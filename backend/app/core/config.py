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
        cap = ["capacitor://localhost", "http://localhost", "ionic://localhost"]
        configured = [o.strip() for o in self.CORS_ORIGINS.split(",")]
        seen: set = set()
        result: List[str] = []
        for o in cap + configured:
            if o not in seen:
                seen.add(o)
                result.append(o)
        return result

    class Config:
        env_file = ".env"


settings = Settings()
