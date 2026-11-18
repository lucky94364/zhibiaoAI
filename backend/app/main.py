from datetime import datetime, timezone
from typing import Literal
from pathlib import Path
from tempfile import TemporaryFile

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.repositories.database import Database
from app.api.core import router
from app.services.common import DomainError, new_id
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
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
    database = Database(settings.database_url)
    @asynccontextmanager
    async def lifespan(app):
        yield
        database.engine.dispose()
    app = FastAPI(title="智标 AI", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.include_router(router(database, settings.demo_actor_id), prefix=settings.api_prefix)

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = new_id('request')
        response = await call_next(request)
        response.headers['X-Request-Id'] = request.state.request_id
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, error: DomainError):
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message, "retryable": False, "details": error.details}, "request_id": request.state.request_id})

    @app.exception_handler(OperationalError)
    async def database_unavailable(request: Request, error):
        return JSONResponse(status_code=503, content={"error": {"code": "DATABASE_UNAVAILABLE", "message": "数据库不可用，请检查迁移和连接配置", "retryable": True, "details": {}}, "request_id": request.state.request_id})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # Do not echo input payloads or credentials in validation errors.
        return JSONResponse(status_code=422, content={"error": {"code": "INPUT_INVALID", "message": "请求字段或请求头不符合接口约定", "retryable": False, "details": {"fields": [list(e['loc']) for e in error.errors()]}}, "request_id": request.state.request_id})
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])

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
