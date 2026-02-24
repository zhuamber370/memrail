from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.schemas import (
    ChangeSetDetailOut,
    ChangeSetListOut,
    CommitIn,
    CommitOut,
    DryRunIn,
    DryRunOut,
    UndoIn,
    UndoOut,
)
from src.services.change_service import ChangeService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1", tags=["changes"])

    @router.get("/changes", response_model=ChangeSetListOut)
    def list_changes(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = ChangeService(db).list_changes(page=page, page_size=page_size, status=status)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.post("/changes/dry-run", response_model=DryRunOut)
    def dry_run(payload: DryRunIn, db: Session = Depends(get_db_dep)):
        cs = ChangeService(db).dry_run(payload)
        diff_items = cs.diff_json
        diff = [str(item.get("text", "")) for item in diff_items]
        return {
            "change_set_id": cs.id,
            "summary": cs.summary_json,
            "diff": diff,
            "diff_items": diff_items,
            "status": "proposed",
        }

    @router.post("/changes/{change_set_id}/commit", response_model=CommitOut)
    def commit(change_set_id: str, payload: CommitIn, db: Session = Depends(get_db_dep)):
        try:
            commit_row, cs = ChangeService(db).commit(change_set_id, payload)
        except (ValueError, ValidationError) as exc:
            code = str(exc) if str(exc) else "CHANGE_COMMIT_FAILED"
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc
        if not commit_row or not cs:
            raise HTTPException(status_code=404, detail="change_set not found")
        return {
            "commit_id": commit_row.id,
            "change_set_id": cs.id,
            "status": "committed",
            "committed_at": commit_row.committed_at,
        }

    @router.post("/commits/undo-last", response_model=UndoOut)
    def undo_last(payload: UndoIn, db: Session = Depends(get_db_dep)):
        try:
            undone = ChangeService(db).undo_last(payload)
        except ValueError as exc:
            code = str(exc) if str(exc) else "CHANGE_UNDO_FAILED"
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc
        if not undone:
            raise HTTPException(
                status_code=409,
                detail={"code": "NO_COMMIT_TO_UNDO", "message": "no commit to undo"},
            )
        undone_commit_id, revert_commit_id = undone
        return {
            "undone_commit_id": undone_commit_id,
            "revert_commit_id": revert_commit_id,
            "status": "reverted",
        }

    @router.get("/changes/{change_set_id}", response_model=ChangeSetDetailOut)
    def get_change(change_set_id: str, db: Session = Depends(get_db_dep)):
        row = ChangeService(db).get_change(change_set_id)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "CHANGE_SET_NOT_FOUND", "message": "change set not found"})
        return row

    return router
