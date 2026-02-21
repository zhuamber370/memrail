from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.schemas import LinkCreate, LinkOut
from src.services.link_service import LinkService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/links", tags=["links"])

    @router.post("", response_model=LinkOut, status_code=201)
    def create_link(payload: LinkCreate, db: Session = Depends(get_db_dep)):
        return LinkService(db).create(payload)

    @router.delete("/{link_id}", status_code=204)
    def delete_link(link_id: str, db: Session = Depends(get_db_dep)):
        deleted = LinkService(db).delete(link_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="link not found")
        return Response(status_code=204)

    return router
