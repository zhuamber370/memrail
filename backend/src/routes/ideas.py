from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.schemas import IdeaCreate, IdeaListOut, IdeaOut, IdeaPatch, IdeaPromoteIn, RouteNodeOut
from src.services.idea_service import IdeaService


def _raise_from_code(code: str) -> None:
    status_code = 422
    if code in {"IDEA_NOT_FOUND", "ROUTE_NOT_FOUND", "TASK_NOT_FOUND"}:
        status_code = 404
    elif code in {"IDEA_INVALID_STATUS_TRANSITION", "IDEA_NOT_READY", "IDEA_ROUTE_TASK_MISMATCH"}:
        status_code = 409
    raise HTTPException(status_code=status_code, detail={"code": code, "message": code.lower()})


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/ideas", tags=["ideas"])

    @router.post("", response_model=IdeaOut, status_code=201)
    def create_idea(payload: IdeaCreate, db: Session = Depends(get_db_dep)):
        try:
            return IdeaService(db).create(payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    @router.get("", response_model=IdeaListOut)
    def list_ideas(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = IdeaService(db).list(page=page, page_size=page_size, task_id=task_id, status=status, q=q)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.patch("/{idea_id}", response_model=IdeaOut)
    def patch_idea(idea_id: str, payload: IdeaPatch, db: Session = Depends(get_db_dep)):
        try:
            updated = IdeaService(db).patch(idea_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))
        if updated is None:
            raise HTTPException(status_code=404, detail={"code": "IDEA_NOT_FOUND", "message": "idea not found"})
        return updated

    @router.post("/{idea_id}/promote", response_model=RouteNodeOut, status_code=201)
    def promote_idea(idea_id: str, payload: IdeaPromoteIn, db: Session = Depends(get_db_dep)):
        try:
            return IdeaService(db).promote(idea_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    return router
