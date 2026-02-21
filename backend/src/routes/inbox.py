from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.schemas import InboxCapture, InboxOut
from src.services.inbox_service import InboxService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])

    @router.post("/captures", response_model=InboxOut, status_code=201)
    def capture(payload: InboxCapture, db: Session = Depends(get_db_dep)):
        return InboxService(db).capture(payload)

    return router
