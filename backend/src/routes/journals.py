from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.schemas import JournalItemListOut, JournalListOut, JournalOut, JournalUpsertAppendIn
from src.services.journal_service import JournalService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/journals", tags=["journals"])

    @router.post("/upsert-append", response_model=JournalOut)
    def upsert_append_journal(payload: JournalUpsertAppendIn, db: Session = Depends(get_db_dep)):
        try:
            return JournalService(db).upsert_append(payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc

    @router.get("", response_model=JournalListOut)
    def list_journals(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = JournalService(db).list(
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.get("/{journal_date}", response_model=JournalOut)
    def get_journal(journal_date: date, db: Session = Depends(get_db_dep)):
        row = JournalService(db).get_by_date(journal_date)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "JOURNAL_NOT_FOUND", "message": "journal not found"})
        return row

    @router.get("/{journal_date}/items", response_model=JournalItemListOut)
    def list_journal_items(journal_date: date, db: Session = Depends(get_db_dep)):
        row = JournalService(db).get_by_date(journal_date)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "JOURNAL_NOT_FOUND", "message": "journal not found"})
        items = JournalService(db).list_items_by_journal_date(journal_date)
        return {"items": items}

    return router
