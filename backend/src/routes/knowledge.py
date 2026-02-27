from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import (
    KnowledgeCreate,
    KnowledgeListOut,
    KnowledgeOut,
    KnowledgePatch,
)
from src.services.knowledge_service import KnowledgeService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

    @router.post("", response_model=KnowledgeOut, status_code=201)
    def create_knowledge(payload: KnowledgeCreate, db: Session = Depends(get_db_dep)):
        try:
            return KnowledgeService(db).create(payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc

    @router.get("", response_model=KnowledgeListOut)
    def list_knowledge(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: str = "active",
        category: Optional[str] = None,
        q: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = KnowledgeService(db).list(
            page=page,
            page_size=page_size,
            status=status,
            category=category,
            q=q,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.get("/{item_id}", response_model=KnowledgeOut)
    def get_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        item = KnowledgeService(db).get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.patch("/{item_id}", response_model=KnowledgeOut)
    def patch_knowledge(item_id: str, payload: KnowledgePatch, db: Session = Depends(get_db_dep)):
        try:
            item = KnowledgeService(db).patch(item_id, payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.post("/{item_id}/archive", response_model=KnowledgeOut)
    def archive_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        item = KnowledgeService(db).archive(item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.delete("/{item_id}", status_code=204)
    def delete_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        deleted = KnowledgeService(db).delete(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return Response(status_code=204)

    return router
