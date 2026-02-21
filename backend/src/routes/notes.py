from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.schemas import NoteAppend, NoteListOut, NoteOut
from src.services.note_service import NoteService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/notes", tags=["notes"])

    @router.post("/append", response_model=NoteOut, status_code=201)
    def append_note(payload: NoteAppend, db: Session = Depends(get_db_dep)):
        return NoteService(db).append(payload)

    @router.get("/search", response_model=NoteListOut)
    def search_notes(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db_dep),
    ):
        items, total = NoteService(db).search(page=page, page_size=page_size)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    return router
