from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models import Idea, Route, RouteNode, Topic
from src.schemas import IdeaCreate, IdeaPatch, IdeaPromoteIn
from src.services.audit_service import log_audit_event


IDEA_TRANSITIONS = {
    "captured": {"triage", "rejected"},
    "triage": {"discovery", "rejected"},
    "discovery": {"ready", "rejected", "triage"},
    "ready": {"discovery", "rejected"},
    "rejected": set(),
}


class IdeaService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: IdeaCreate) -> Idea:
        if payload.topic_id:
            self._validate_topic(payload.topic_id)

        idea = Idea(
            id=f"ida_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            problem=payload.problem,
            hypothesis=payload.hypothesis,
            status=payload.status,
            topic_id=payload.topic_id,
            source=payload.source,
        )
        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_idea",
            target_type="idea",
            target_id=idea.id,
            source_refs=[idea.source],
        )
        return idea

    def list(self, *, page: int, page_size: int, status: Optional[str] = None, q: Optional[str] = None):
        stmt = select(Idea)
        count_stmt = select(func.count()).select_from(Idea)

        if status:
            stmt = stmt.where(Idea.status == status)
            count_stmt = count_stmt.where(Idea.status == status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Idea.title.ilike(like), Idea.problem.ilike(like), Idea.hypothesis.ilike(like)))
            count_stmt = count_stmt.where(
                or_(Idea.title.ilike(like), Idea.problem.ilike(like), Idea.hypothesis.ilike(like))
            )

        stmt = stmt.order_by(Idea.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def patch(self, idea_id: str, payload: IdeaPatch) -> Optional[Idea]:
        idea = self.db.get(Idea, idea_id)
        if idea is None:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        next_status = patch_data.get("status")
        if next_status and next_status != idea.status:
            self._validate_transition(idea.status, next_status)

        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            self._validate_topic(patch_data["topic_id"])

        for key, value in patch_data.items():
            setattr(idea, key, value)

        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="patch_idea",
            target_type="idea",
            target_id=idea.id,
            source_refs=[idea.source],
        )
        return idea

    def promote(self, idea_id: str, payload: IdeaPromoteIn) -> RouteNode:
        idea = self.db.get(Idea, idea_id)
        if idea is None:
            raise ValueError("IDEA_NOT_FOUND")
        if idea.status != "ready":
            raise ValueError("IDEA_NOT_READY")

        route = self.db.get(Route, payload.route_id)
        if route is None:
            raise ValueError("ROUTE_NOT_FOUND")

        max_hint = self.db.scalar(select(func.max(RouteNode.order_hint)).where(RouteNode.route_id == route.id))
        order_hint = int(max_hint or 0) + 1

        default_description = "\n\n".join(
            [part for part in [idea.problem.strip(), idea.hypothesis.strip()] if part]
        )
        node = RouteNode(
            id=f"rtn_{uuid.uuid4().hex[:12]}",
            route_id=route.id,
            node_type=payload.node_type,
            title=(payload.title or idea.title).strip(),
            description=(payload.description if payload.description is not None else default_description),
            status="todo",
            order_hint=order_hint,
            assignee_type="human",
            assignee_id=None,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="promote_idea_to_route_node",
            target_type="route_node",
            target_id=node.id,
            source_refs=[idea.source],
            metadata={"idea_id": idea.id, "route_id": route.id},
        )
        return node

    def _validate_transition(self, current: str, next_status: str) -> None:
        allowed = IDEA_TRANSITIONS.get(current, set())
        if next_status not in allowed:
            raise ValueError("IDEA_INVALID_STATUS_TRANSITION")

    def _validate_topic(self, topic_id: str) -> None:
        if self.db.get(Topic, topic_id) is None:
            raise ValueError("TOPIC_NOT_FOUND")
