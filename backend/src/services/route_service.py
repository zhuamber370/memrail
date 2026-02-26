from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models import NodeLog, Route, RouteEdge, RouteNode, Task
from src.schemas import (
    NodeLogCreate,
    RouteCreate,
    RouteEdgeCreate,
    RouteNodeCreate,
    RouteNodePatch,
    RoutePatch,
)
from src.services.audit_service import log_audit_event


ROUTE_TRANSITIONS = {
    "candidate": {"active", "parked", "cancelled"},
    "active": {"parked", "completed", "cancelled"},
    "parked": {"active", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class RouteService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: RouteCreate) -> Route:
        self._validate_task(payload.task_id)
        if payload.status == "active":
            self._ensure_single_active(task_id=payload.task_id)
        route = Route(
            id=f"rte_{uuid.uuid4().hex[:12]}",
            task_id=payload.task_id,
            name=payload.name,
            goal=payload.goal,
            status=payload.status,
            priority=payload.priority,
            owner=payload.owner,
        )
        self.db.add(route)
        if payload.status == "active":
            self._promote_task_to_in_progress(payload.task_id)
        self.db.commit()
        self.db.refresh(route)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_route",
            target_type="route",
            target_id=route.id,
            source_refs=[f"route://{route.id}"],
        )
        return route

    def list(
        self,
        *,
        page: int,
        page_size: int,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ):
        stmt = select(Route)
        count_stmt = select(func.count()).select_from(Route)

        if task_id:
            stmt = stmt.where(Route.task_id == task_id)
            count_stmt = count_stmt.where(Route.task_id == task_id)
        if status:
            stmt = stmt.where(Route.status == status)
            count_stmt = count_stmt.where(Route.status == status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Route.name.ilike(like), Route.goal.ilike(like)))
            count_stmt = count_stmt.where(or_(Route.name.ilike(like), Route.goal.ilike(like)))

        stmt = stmt.order_by(Route.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def patch(self, route_id: str, payload: RoutePatch) -> Optional[Route]:
        route = self.db.get(Route, route_id)
        if route is None:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        next_status = patch_data.get("status")
        if next_status and next_status != route.status:
            self._validate_route_transition(route.status, next_status)
            if next_status == "active":
                self._ensure_single_active(task_id=route.task_id, ignore_route_id=route.id)
                self._promote_task_to_in_progress(route.task_id)

        for key, value in patch_data.items():
            setattr(route, key, value)

        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="patch_route",
            target_type="route",
            target_id=route.id,
            source_refs=[f"route://{route.id}"],
        )
        return route

    def _ensure_single_active(self, task_id: Optional[str], ignore_route_id: Optional[str] = None) -> None:
        stmt = select(Route).where(Route.status == "active")
        if task_id:
            stmt = stmt.where(Route.task_id == task_id)
        if ignore_route_id:
            stmt = stmt.where(Route.id != ignore_route_id)
        existing = self.db.scalar(stmt.limit(1))
        if existing is not None:
            raise ValueError("ROUTE_ACTIVE_CONFLICT")

    def _validate_route_transition(self, current_status: str, next_status: str) -> None:
        allowed = ROUTE_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise ValueError("ROUTE_INVALID_STATUS_TRANSITION")

    def _validate_task(self, task_id: str) -> None:
        if self.db.get(Task, task_id) is None:
            raise ValueError("TASK_NOT_FOUND")

    def _promote_task_to_in_progress(self, task_id: str) -> None:
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError("TASK_NOT_FOUND")
        if task.status in {"done", "cancelled"}:
            raise ValueError("TASK_INVALID_STATUS_TRANSITION")
        if task.status == "todo":
            task.status = "in_progress"
            self.db.add(task)


class RouteGraphService:
    def __init__(self, db: Session):
        self.db = db

    def create_node(self, route_id: str, payload: RouteNodeCreate) -> RouteNode:
        self._ensure_route(route_id)
        order_hint = payload.order_hint
        if order_hint <= 0:
            max_hint = self.db.scalar(
                select(func.max(RouteNode.order_hint)).where(RouteNode.route_id == route_id)
            )
            order_hint = int(max_hint or 0) + 1

        node = RouteNode(
            id=f"rtn_{uuid.uuid4().hex[:12]}",
            route_id=route_id,
            node_type=payload.node_type,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            order_hint=order_hint,
            assignee_type=payload.assignee_type,
            assignee_id=payload.assignee_id,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_route_node",
            target_type="route_node",
            target_id=node.id,
            source_refs=[f"route://{route_id}"],
        )
        return node

    def patch_node(self, route_id: str, node_id: str, payload: RouteNodePatch) -> Optional[RouteNode]:
        self._ensure_route(route_id)
        node = self.db.scalar(
            select(RouteNode).where(RouteNode.id == node_id, RouteNode.route_id == route_id)
        )
        if node is None:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        for key, value in patch_data.items():
            setattr(node, key, value)

        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="patch_route_node",
            target_type="route_node",
            target_id=node.id,
            source_refs=[f"route://{route_id}"],
        )
        return node

    def delete_node(self, route_id: str, node_id: str) -> bool:
        self._ensure_route(route_id)
        node = self.db.scalar(
            select(RouteNode).where(RouteNode.id == node_id, RouteNode.route_id == route_id)
        )
        if node is None:
            return False

        self.db.delete(node)
        self.db.commit()
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="delete_route_node",
            target_type="route_node",
            target_id=node_id,
            source_refs=[f"route://{route_id}"],
        )
        return True

    def create_edge(self, route_id: str, payload: RouteEdgeCreate) -> RouteEdge:
        self._ensure_route(route_id)
        if payload.from_node_id == payload.to_node_id:
            raise ValueError("ROUTE_EDGE_SELF_LOOP")

        from_node = self.db.get(RouteNode, payload.from_node_id)
        to_node = self.db.get(RouteNode, payload.to_node_id)
        if from_node is None or to_node is None:
            raise ValueError("ROUTE_EDGE_NODE_NOT_FOUND")
        if from_node.route_id != route_id or to_node.route_id != route_id:
            raise ValueError("ROUTE_EDGE_CROSS_ROUTE")

        existing = self.db.scalar(
            select(RouteEdge).where(
                RouteEdge.route_id == route_id,
                RouteEdge.from_node_id == payload.from_node_id,
                RouteEdge.to_node_id == payload.to_node_id,
            )
        )
        if existing is not None:
            raise ValueError("ROUTE_EDGE_DUPLICATE")

        edge = RouteEdge(
            id=f"red_{uuid.uuid4().hex[:12]}",
            route_id=route_id,
            from_node_id=payload.from_node_id,
            to_node_id=payload.to_node_id,
            relation=payload.relation,
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_route_edge",
            target_type="route_edge",
            target_id=edge.id,
            source_refs=[f"route://{route_id}"],
        )
        return edge

    def delete_edge(self, route_id: str, edge_id: str) -> bool:
        self._ensure_route(route_id)
        edge = self.db.scalar(select(RouteEdge).where(RouteEdge.id == edge_id, RouteEdge.route_id == route_id))
        if edge is None:
            return False

        self.db.delete(edge)
        self.db.commit()
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="delete_route_edge",
            target_type="route_edge",
            target_id=edge_id,
            source_refs=[f"route://{route_id}"],
        )
        return True

    def get_graph(self, route_id: str) -> tuple[list[RouteNode], list[RouteEdge]]:
        self._ensure_route(route_id)
        nodes = list(
            self.db.scalars(
                select(RouteNode)
                .where(RouteNode.route_id == route_id)
                .order_by(RouteNode.order_hint.asc(), RouteNode.created_at.asc())
            )
        )
        edges = list(
            self.db.scalars(
                select(RouteEdge)
                .where(RouteEdge.route_id == route_id)
                .order_by(RouteEdge.created_at.asc())
            )
        )
        return nodes, edges

    def append_node_log(self, route_id: str, node_id: str, payload: NodeLogCreate) -> NodeLog:
        node = self._ensure_node_in_route(route_id, node_id)
        log = NodeLog(
            id=f"nlg_{uuid.uuid4().hex[:12]}",
            node_id=node.id,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            content=payload.content,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="append_route_node_log",
            target_type="route_node",
            target_id=node.id,
            source_refs=[f"route://{route_id}"],
        )
        return log

    def list_node_logs(self, route_id: str, node_id: str) -> list[NodeLog]:
        self._ensure_node_in_route(route_id, node_id)
        return list(
            self.db.scalars(
                select(NodeLog).where(NodeLog.node_id == node_id).order_by(NodeLog.created_at.desc())
            )
        )

    def _ensure_route(self, route_id: str) -> Route:
        route = self.db.get(Route, route_id)
        if route is None:
            raise ValueError("ROUTE_NOT_FOUND")
        return route

    def _ensure_node_in_route(self, route_id: str, node_id: str) -> RouteNode:
        self._ensure_route(route_id)
        node = self.db.scalar(select(RouteNode).where(RouteNode.id == node_id, RouteNode.route_id == route_id))
        if node is None:
            raise ValueError("ROUTE_NODE_NOT_FOUND")
        return node
