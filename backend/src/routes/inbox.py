from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.schemas import InboxCapture, InboxDetailOut, InboxListOut, InboxOut
from src.services.inbox_service import InboxService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])

    @router.post("/captures", response_model=InboxOut, status_code=201)
    def capture(payload: InboxCapture, db: Session = Depends(get_db_dep)):
        return InboxService(db).capture(payload)

    @router.get("", response_model=InboxListOut)
    def list_inbox(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = InboxService(db).list(page=page, page_size=page_size, status=status)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.get("/{inbox_id}", response_model=InboxDetailOut)
    def get_inbox(inbox_id: str, db: Session = Depends(get_db_dep)):
        item = InboxService(db).get(inbox_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "INBOX_NOT_FOUND", "message": "inbox not found"})
        return item

    return router
