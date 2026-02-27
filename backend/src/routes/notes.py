from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import (
    NoteAppend,
    NoteBatchClassifyIn,
    NoteBatchClassifyOut,
    NoteListOut,
    NoteOut,
    NotePatch,
    NoteSourceListOut,
    NoteTopicSummaryOut,
)
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
        topic_id: Optional[str] = None,
        unclassified: bool = False,
        status: str = "active",
        q: Optional[str] = None,
        tag: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = NoteService(db).search(
            page=page,
            page_size=page_size,
            topic_id=topic_id,
            unclassified=unclassified,
            status=status,
            q=q,
            tag=tag,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.patch("/{note_id}", response_model=NoteOut)
    def patch_note(note_id: str, payload: NotePatch, db: Session = Depends(get_db_dep)):
        try:
            updated = NoteService(db).patch(note_id, payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc
        if not updated:
            raise HTTPException(status_code=404, detail={"code": "NOTE_NOT_FOUND", "message": "note not found"})
        return updated

    @router.delete("/{note_id}", status_code=204)
    def delete_note(note_id: str, db: Session = Depends(get_db_dep)):
        deleted = NoteService(db).delete(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"code": "NOTE_NOT_FOUND", "message": "note not found"})
        return Response(status_code=204)

    @router.get("/{note_id}/sources", response_model=NoteSourceListOut)
    def list_note_sources(note_id: str, db: Session = Depends(get_db_dep)):
        try:
            items = NoteService(db).list_sources(note_id)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=404, detail={"code": code, "message": code.lower()}) from exc
        return {"items": items}

    @router.post("/batch-classify", response_model=NoteBatchClassifyOut)
    def batch_classify(payload: NoteBatchClassifyIn, db: Session = Depends(get_db_dep)):
        try:
            return NoteService(db).batch_classify(payload.note_ids, payload.topic_id)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc

    @router.get("/topic-summary", response_model=NoteTopicSummaryOut)
    def topic_summary(
        status: str = "active",
        db: Session = Depends(get_db_dep),
    ):
        items = NoteService(db).topic_summary(status=status)
        return {"items": items}

    return router
