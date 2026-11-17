from datetime import datetime, timezone
from typing import Literal
from pathlib import Path
from tempfile import TemporaryFile

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.settings import Settings

CapabilityState = Literal["available", "unavailable", "not_configured", "unknown"]

class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"
    version: str = "0.1.0"
    timestamp: datetime

class Capabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ai_provider: Literal["mock", "haier_workflow", "internal_model"]
    is_simulated: bool
    parser_pdf: CapabilityState = "unavailable"
    ocr: CapabilityState = "unavailable"
    word_converter: CapabilityState = "unavailable"
    storage: CapabilityState
    database: CapabilityState
    workflow_api: CapabilityState = "unavailable"

def probe_storage(settings: Settings) -> CapabilityState:
    try:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryFile(dir=settings.storage_dir) as file:
            file.write(b"probe")
            file.flush()
            file.seek(0)
            if file.read() != b"probe":
                return "unavailable"
        return "available"
    except OSError:
        return "unavailable"

def probe_database(settings: Settings) -> CapabilityState:
    engine = None
    try:
        url = make_url(settings.database_url)
        if url.get_backend_name() == "sqlite" and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"timeout": 2} if url.get_backend_name() == "sqlite" else {})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "available"
    except Exception:
        return "unavailable"
    finally:
        if engine is not None:
            engine.dispose()

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="智标 AI", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["GET"], allow_headers=["*"])

    @app.get(settings.api_prefix + "/health", response_model=Health, operation_id="get_health")
    def health() -> Health:
        return Health(timestamp=datetime.now(timezone.utc))

    @app.get(settings.api_prefix + "/capabilities", response_model=Capabilities, operation_id="get_capabilities")
    def capabilities() -> Capabilities:
        # Configuration alone never proves an unimplemented adapter is available.
        return Capabilities(ai_provider=settings.ai_provider, is_simulated=settings.ai_provider == "mock",
                            storage=probe_storage(settings), database=probe_database(settings))
    return app

app = create_app()
