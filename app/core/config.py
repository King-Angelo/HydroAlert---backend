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
    
    # File Upload Configuration
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list[str] = ["image/jpeg", "image/png", "image/webp"]
    max_files_per_report: int = 5
    
    # Storage paths
    evidence_dir: str = "uploads/evidence"
    temp_dir: str = "uploads/temp"
    
    # Cloud Storage Configuration
    cloud_storage_enabled: bool = False
    cloud_storage_bucket: str = "hydroalert-evidence"
    cloud_storage_public_url: str = "https://storage.googleapis.com/hydroalert-evidence"
    cloud_storage_credentials_path: Optional[str] = None
    cloud_storage_make_public: bool = False
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file_enabled: bool = True
    log_console_enabled: bool = True
    
    class Config:
        env_file = ".env"


settings = Settings()
