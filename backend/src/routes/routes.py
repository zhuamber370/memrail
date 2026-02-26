from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from src.schemas import (
    NodeLogCreate,
    NodeLogListOut,
    NodeLogOut,
    RouteCreate,
    RouteEdgeCreate,
    RouteEdgeOut,
    RouteGraphOut,
    RouteListOut,
    RouteNodeCreate,
    RouteNodeOut,
    RouteNodePatch,
    RouteOut,
    RoutePatch,
)
from src.services.route_service import RouteGraphService, RouteService


def _raise_from_code(code: str) -> None:
    status_code = 422
    if code in {"ROUTE_NOT_FOUND", "ROUTE_NODE_NOT_FOUND", "ROUTE_EDGE_NOT_FOUND", "TASK_NOT_FOUND"}:
        status_code = 404
    elif code in {
        "ROUTE_ACTIVE_CONFLICT",
        "ROUTE_INVALID_STATUS_TRANSITION",
        "ROUTE_EDGE_DUPLICATE",
        "TASK_INVALID_STATUS_TRANSITION",
    }:
        status_code = 409
    raise HTTPException(status_code=status_code, detail={"code": code, "message": code.lower()})


def build_router(get_db_dep):
    router = APIRouter(prefix="/api/v1/routes", tags=["routes"])

    @router.post("", response_model=RouteOut, status_code=201)
    def create_route(payload: RouteCreate, db: Session = Depends(get_db_dep)):
        try:
            return RouteService(db).create(payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    @router.get("", response_model=RouteListOut)
    def list_routes(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        db: Session = Depends(get_db_dep),
    ):
        items, total = RouteService(db).list(page=page, page_size=page_size, task_id=task_id, status=status, q=q)
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @router.patch("/{route_id}", response_model=RouteOut)
    def patch_route(route_id: str, payload: RoutePatch, db: Session = Depends(get_db_dep)):
        try:
            updated = RouteService(db).patch(route_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))
        if updated is None:
            raise HTTPException(status_code=404, detail={"code": "ROUTE_NOT_FOUND", "message": "route not found"})
        return updated

    @router.post("/{route_id}/nodes", response_model=RouteNodeOut, status_code=201)
    def create_route_node(route_id: str, payload: RouteNodeCreate, db: Session = Depends(get_db_dep)):
        try:
            return RouteGraphService(db).create_node(route_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    @router.patch("/{route_id}/nodes/{node_id}", response_model=RouteNodeOut)
    def patch_route_node(route_id: str, node_id: str, payload: RouteNodePatch, db: Session = Depends(get_db_dep)):
        try:
            updated = RouteGraphService(db).patch_node(route_id, node_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ROUTE_NODE_NOT_FOUND", "message": "route node not found"},
            )
        return updated

    @router.delete("/{route_id}/nodes/{node_id}", status_code=204)
    def delete_route_node(route_id: str, node_id: str, db: Session = Depends(get_db_dep)):
        try:
            deleted = RouteGraphService(db).delete_node(route_id, node_id)
        except ValueError as exc:
            _raise_from_code(str(exc))
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"code": "ROUTE_NODE_NOT_FOUND", "message": "route node not found"},
            )
        return Response(status_code=204)

    @router.post("/{route_id}/edges", response_model=RouteEdgeOut, status_code=201)
    def create_route_edge(route_id: str, payload: RouteEdgeCreate, db: Session = Depends(get_db_dep)):
        try:
            return RouteGraphService(db).create_edge(route_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    @router.delete("/{route_id}/edges/{edge_id}", status_code=204)
    def delete_route_edge(route_id: str, edge_id: str, db: Session = Depends(get_db_dep)):
        try:
            deleted = RouteGraphService(db).delete_edge(route_id, edge_id)
        except ValueError as exc:
            _raise_from_code(str(exc))
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"code": "ROUTE_EDGE_NOT_FOUND", "message": "route edge not found"},
            )
        return Response(status_code=204)

    @router.get("/{route_id}/graph", response_model=RouteGraphOut)
    def get_route_graph(route_id: str, db: Session = Depends(get_db_dep)):
        try:
            nodes, edges = RouteGraphService(db).get_graph(route_id)
        except ValueError as exc:
            _raise_from_code(str(exc))
        return {"route_id": route_id, "nodes": nodes, "edges": edges}

    @router.post("/{route_id}/nodes/{node_id}/logs", response_model=NodeLogOut, status_code=201)
    def append_node_log(route_id: str, node_id: str, payload: NodeLogCreate, db: Session = Depends(get_db_dep)):
        try:
            return RouteGraphService(db).append_node_log(route_id, node_id, payload)
        except ValueError as exc:
            _raise_from_code(str(exc))

    @router.get("/{route_id}/nodes/{node_id}/logs", response_model=NodeLogListOut)
    def list_node_logs(route_id: str, node_id: str, db: Session = Depends(get_db_dep)):
        try:
            items = RouteGraphService(db).list_node_logs(route_id, node_id)
        except ValueError as exc:
            _raise_from_code(str(exc))
        return {"items": items}

    return router
