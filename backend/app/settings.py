from pathlib import Path
from typing import Literal
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZB_", env_file=PROJECT_ROOT / ".env", extra="ignore")
    env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./var/zhb.db"
    storage_dir: Path = Path("var/storage")
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 50
    task_concurrency: Literal[1] = 1
    ai_provider: Literal["mock", "haier_workflow", "internal_model"] = "mock"
    ai_timeout_seconds: int = 120
    workflow_base_url: str = ""
    workflow_api_key: SecretStr = SecretStr("")
    model_base_url: str = ""
    model_api_key: SecretStr = SecretStr("")
    model_name: str = ""
    ocr_provider: Literal["none", "paddleocr"] = "none"
    libreoffice_bin: str = ""
    demo_actor_id: str = "demo-user"

    @field_validator("storage_dir")
    @classmethod
    def root_storage(cls, value: Path) -> Path:
        return (PROJECT_ROOT / value).resolve()

    @field_validator("database_url")
    @classmethod
    def root_database(cls, value: str) -> str:
        from sqlalchemy.engine import make_url
        url = make_url(value)
        if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
            return "sqlite:///" + str((PROJECT_ROOT / url.database).resolve())
        return url.render_as_string(hide_password=False)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
