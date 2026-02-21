from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.schemas import CycleCreate, CycleListOut, CycleOut
from src.services.task_service import CycleService


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/cycles", tags=["cycles"])

    @router.post("", response_model=CycleOut, status_code=201)
    def create_cycle(payload: CycleCreate, db: Session = Depends(get_db_dep)):
        return CycleService(db).create(
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
        )

    @router.get("", response_model=CycleListOut)
    def list_cycles(db: Session = Depends(get_db_dep)):
        return {"items": CycleService(db).list()}

    return router
