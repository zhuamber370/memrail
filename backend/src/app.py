from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.db import Base, build_engine, build_session_local, ensure_runtime_schema, get_db
from src.middleware.auth import ApiKeyAuthMiddleware
from src.middleware.error_handler import RequestIdMiddleware, install_error_handlers
from src.routes.audit import build_router as build_audit_router
from src.routes.changes import build_router as build_changes_router
from src.routes.cycles import build_router as build_cycles_router
from src.routes.inbox import build_router as build_inbox_router
from src.routes.links import build_router as build_links_router
from src.routes.notes import build_router as build_notes_router
from src.routes.tasks import build_router as build_tasks_router
from src.routes.topics import build_router as build_topics_router


def _build_runtime(database_url: str):
    engine = build_engine(database_url)
    session_local = build_session_local(engine)
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    return engine, session_local


def create_app(
    database_url: Optional[str] = None, require_auth: bool = False, api_key: Optional[str] = None
) -> FastAPI:
    runtime_db_url = database_url or settings.database_url
    _, session_local = _build_runtime(runtime_db_url)

    def get_db_dep():
        yield from get_db(session_local)

    app = FastAPI(title="AFKMS Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    if require_auth:
        app.add_middleware(ApiKeyAuthMiddleware, api_key=api_key or "dev-api-key")
    install_error_handlers(app)
    app.include_router(build_tasks_router(get_db_dep))
    app.include_router(build_topics_router(get_db_dep))
    app.include_router(build_cycles_router(get_db_dep))
    app.include_router(build_inbox_router(get_db_dep))
    app.include_router(build_notes_router(get_db_dep))
    app.include_router(build_links_router(get_db_dep))
    app.include_router(build_changes_router(get_db_dep))
    app.include_router(build_audit_router(get_db_dep))

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
