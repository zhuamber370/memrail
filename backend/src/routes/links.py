from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import LinkCreate, LinkListOut, LinkOut
from src.services.link_service import LinkService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/links", tags=["links"])

    @router.get("", response_model=LinkListOut)
    def list_links(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        from_type: Optional[str] = None,
        from_id: Optional[str] = None,
        to_type: Optional[str] = None,
        to_id: Optional[str] = None,
        relation: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = LinkService(db).list(
            page=page,
            page_size=page_size,
            from_type=from_type,
            from_id=from_id,
            to_type=to_type,
            to_id=to_id,
            relation=relation,
        )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

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
