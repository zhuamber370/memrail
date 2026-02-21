from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.services.audit_service import list_audit_events


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

    @router.get("/events")
    def list_events(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db_dep),
    ):
        rows, total = list_audit_events(db, page=page, page_size=page_size)
        items = [
            {
                "event_id": r.id,
                "occurred_at": r.occurred_at,
                "actor": {"type": r.actor_type, "id": r.actor_id},
                "tool": r.tool,
                "action": r.action,
                "target": {"type": r.target_type, "id": r.target_id},
                "source_refs": r.source_refs_json,
                "before_hash": r.before_hash,
                "after_hash": r.after_hash,
            }
            for r in rows
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    return router
