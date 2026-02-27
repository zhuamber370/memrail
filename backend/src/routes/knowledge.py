from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import (
    KnowledgeCreate,
    KnowledgeMigrationCandidatesOut,
    KnowledgeMigrationCommitIn,
    KnowledgeMigrationCommitOut,
    KnowledgeDetailOut,
    KnowledgeEvidenceIn,
    KnowledgeEvidenceOut,
    KnowledgeListOut,
    KnowledgePatch,
)
from src.services.knowledge_service import KnowledgeService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

    @router.post("", response_model=KnowledgeDetailOut, status_code=201)
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
        type: Optional[str] = None,
        topic_id: Optional[str] = None,
        status: str = "active",
        q: Optional[str] = None,
        tag: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = KnowledgeService(db).list(
            page=page,
            page_size=page_size,
            type=type,
            topic_id=topic_id,
            status=status,
            q=q,
            tag=tag,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.get("/migration/candidates", response_model=KnowledgeMigrationCandidatesOut)
    def list_migration_candidates(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=20),
        db: Session = Depends(get_db_dep),
    ):
        items, total = KnowledgeService(db).list_migration_candidates(page=page, page_size=page_size)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.post("/migration/commit", response_model=KnowledgeMigrationCommitOut)
    def commit_migration(payload: KnowledgeMigrationCommitIn, db: Session = Depends(get_db_dep)):
        try:
            return KnowledgeService(db).commit_migration(note_ids=payload.note_ids)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc

    @router.get("/{item_id}", response_model=KnowledgeDetailOut)
    def get_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        item = KnowledgeService(db).get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.patch("/{item_id}", response_model=KnowledgeDetailOut)
    def patch_knowledge(item_id: str, payload: KnowledgePatch, db: Session = Depends(get_db_dep)):
        try:
            item = KnowledgeService(db).patch(item_id, payload)
        except ValueError as exc:
            code = str(exc)
            raise HTTPException(status_code=422, detail={"code": code, "message": code.lower()}) from exc
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.post("/{item_id}/archive", response_model=KnowledgeDetailOut)
    def archive_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        item = KnowledgeService(db).archive(item_id)
        if not item:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return item

    @router.post("/{item_id}/evidences", response_model=KnowledgeEvidenceOut, status_code=201)
    def append_evidence(item_id: str, payload: KnowledgeEvidenceIn, db: Session = Depends(get_db_dep)):
        evidence = KnowledgeService(db).append_evidence(item_id, payload)
        if not evidence:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return evidence

    @router.delete("/{item_id}", status_code=204)
    def delete_knowledge(item_id: str, db: Session = Depends(get_db_dep)):
        deleted = KnowledgeService(db).delete(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_NOT_FOUND", "message": "not found"})
        return Response(status_code=204)

    return router
