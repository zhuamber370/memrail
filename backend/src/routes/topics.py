from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.schemas import TopicCreate, TopicListOut, TopicOut
from src.services.task_service import TopicService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/topics", tags=["topics"])

    @router.post("", response_model=TopicOut, status_code=201)
    def create_topic(payload: TopicCreate, db: Session = Depends(get_db_dep)):
        try:
            return TopicService(db).create(payload)
        except ValueError as exc:
            code = str(exc)
            if code == "TOPIC_TAXONOMY_LOCKED":
                status_code = 403
            elif code == "TOPIC_NAME_CONFLICT":
                status_code = 409
            else:
                status_code = 422
            raise HTTPException(
                status_code=status_code,
                detail={"code": code, "message": code.lower()},
            ) from exc

    @router.get("", response_model=TopicListOut)
    def list_topics(db: Session = Depends(get_db_dep)):
        items = TopicService(db).list()
        return {"items": items}

    return router
