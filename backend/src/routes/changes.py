from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.schemas import CommitIn, CommitOut, DryRunIn, DryRunOut, UndoIn, UndoOut
from src.services.change_service import ChangeService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1", tags=["changes"])

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
        commit_row, cs = ChangeService(db).commit(change_set_id, payload)
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
        undone = ChangeService(db).undo_last(payload)
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

    return router
