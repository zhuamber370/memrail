from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import (
    TaskArchiveIn,
    TaskArchiveOut,
    TaskBatchUpdateIn,
    TaskBatchUpdateOut,
    TaskCreate,
    TaskListOut,
    TaskOut,
    TaskPatch,
    TaskViewsSummaryOut,
)
from src.services.task_service import TaskService
from src.validators.task_validator import ensure_patch_has_fields


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

    @router.post("", response_model=TaskOut, status_code=201)
    def create_task(payload: TaskCreate, db: Session = Depends(get_db_dep)):
        try:
            return TaskService(db).create(payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(
                status_code=422,
                detail={"code": code, "message": code.lower()},
            ) from exc

    @router.get("", response_model=TaskListOut)
    def list_tasks(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: Optional[str] = None,
        priority: Optional[str] = None,
        archived: Optional[bool] = None,
        topic_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        blocked: Optional[bool] = None,
        stale_days: Optional[int] = Query(default=None, ge=1),
        due_before: Optional[date] = None,
        updated_before: Optional[datetime] = None,
        view: Optional[str] = None,
        q: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = TaskService(db).list(
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            archived=archived,
            topic_id=topic_id,
            cycle_id=cycle_id,
            blocked=blocked,
            stale_days=stale_days,
            due_before=due_before,
            updated_before=updated_before,
            view=view,
            q=q,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.patch("/{task_id}", response_model=TaskOut)
    def patch_task(task_id: str, payload: TaskPatch, db: Session = Depends(get_db_dep)):
        try:
            ensure_patch_has_fields(payload)
            updated = TaskService(db).patch(task_id, payload)
        except ValueError as exc:
            code = str(exc)
            status_code = 409 if code == "TASK_INVALID_STATUS_TRANSITION" else 422
            raise HTTPException(
                status_code=status_code,
                detail={"code": code, "message": code.lower()},
            ) from exc
        if not updated:
            raise HTTPException(status_code=404, detail="task not found")
        return updated

    @router.post("/batch-update", response_model=TaskBatchUpdateOut)
    def batch_update_tasks(payload: TaskBatchUpdateIn, db: Session = Depends(get_db_dep)):
        try:
            ensure_patch_has_fields(payload.patch)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result = TaskService(db).batch_update(payload.task_ids, payload.patch)
        return result

    @router.post("/{task_id}/reopen", response_model=TaskOut)
    def reopen_task(task_id: str, db: Session = Depends(get_db_dep)):
        updated = TaskService(db).reopen(task_id)
        if not updated:
            raise HTTPException(status_code=404, detail="task not found")
        return updated

    @router.get("/views/summary", response_model=TaskViewsSummaryOut)
    def task_views_summary(db: Session = Depends(get_db_dep)):
        return TaskService(db).views_summary()

    @router.delete("/{task_id}", status_code=204)
    def delete_task(task_id: str, db: Session = Depends(get_db_dep)):
        deleted = TaskService(db).delete(task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "task not found"})
        return Response(status_code=204)

    @router.post("/archive-cancelled", response_model=TaskArchiveOut)
    def archive_cancelled_tasks(db: Session = Depends(get_db_dep)):
        archived = TaskService(db).archive_cancelled()
        return {"archived": archived}

    @router.post("/archive-selected", response_model=TaskArchiveOut)
    def archive_selected_tasks(payload: TaskArchiveIn, db: Session = Depends(get_db_dep)):
        archived = TaskService(db).archive_selected(payload.task_ids)
        return {"archived": archived}

    return router
