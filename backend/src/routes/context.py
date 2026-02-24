from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.schemas import ContextBundleOut
from src.services.context_service import ContextService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/context", tags=["context"])

    @router.get("/bundle", response_model=ContextBundleOut)
    def get_context_bundle(
        intent: str = Query(min_length=1),
        window_days: int = Query(default=14, ge=1, le=90),
        topic_id: Optional[list[str]] = Query(default=None),
        include_done: bool = False,
        tasks_limit: int = Query(default=20, ge=1, le=200),
        notes_limit: int = Query(default=20, ge=1, le=200),
        journals_limit: int = Query(default=14, ge=1, le=200),
        db: Session = Depends(get_db_dep),
    ):
        return ContextService(db).bundle(
            intent=intent,
            window_days=window_days,
            topic_ids=topic_id,
            include_done=include_done,
            tasks_limit=tasks_limit,
            notes_limit=notes_limit,
            journals_limit=journals_limit,
        )

    return router
