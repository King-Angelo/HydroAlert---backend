from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/hydroalert"
    
    # JWT
    jwt_secret_key: str = "change-me-please"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    
    # App
    app_name: str = "Hydro Alert API"
    debug: bool = False
    
    # WebSocket
    websocket_cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
