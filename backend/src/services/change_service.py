from __future__ import annotations

from datetime import date, datetime, timezone
import uuid
from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    ChangeAction,
    ChangeSet,
    Commit,
    Idea,
    InboxItem,
    Journal,
    Link,
    NodeLog,
    Note,
    NoteSource,
    Route,
    RouteEdge,
    RouteNode,
    Task,
    TaskSource,
    Topic,
)
from src.schemas import (
    CommitIn,
    DryRunIn,
    IdeaCreate,
    IdeaPatch,
    IdeaPromoteIn,
    InboxCapture,
    JournalUpsertAppendIn,
    KnowledgeCreate,
    KnowledgePatch,
    LinkCreate,
    NodeLogCreate,
    NoteAppend,
    NotePatch,
    RouteCreate,
    RouteEdgeCreate,
    RouteEdgePatch,
    RouteNodeCreate,
    RouteNodePatch,
    RoutePatch,
    TaskCreate,
    TaskPatch,
    UndoIn,
)
from src.services.audit_service import log_audit_event
from src.services.idea_service import IDEA_TRANSITIONS
from src.services.knowledge_category import infer_knowledge_category
from src.services.route_service import ROUTE_TRANSITIONS, RouteGraphService, RouteService
from src.services.task_service import TaskService

TASK_DATE_FIELDS = {"due"}
TASK_DATETIME_FIELDS = {"archived_at"}

CREATE_ACTIONS = {
    "create_task",
    "append_note",
    "link_entities",
    "create_link",
    "create_idea",
    "promote_idea",
    "create_route",
    "create_route_node",
    "create_route_edge",
    "append_route_node_log",
    "create_knowledge",
    "capture_inbox",
}

UPDATE_ACTIONS = {
    "update_task",
    "patch_note",
    "upsert_journal_append",
    "patch_idea",
    "patch_route",
    "patch_route_node",
    "patch_route_edge",
    "patch_knowledge",
    "archive_knowledge",
}


class ChangeService:
    def __init__(self, db: Session):
        self.db = db

    def list_changes(self, *, page: int, page_size: int, status: Optional[str] = None) -> tuple[list[dict], int]:
        stmt = select(ChangeSet)
        count_stmt = select(func.count()).select_from(ChangeSet)
        if status:
            stmt = stmt.where(ChangeSet.status == status)
            count_stmt = count_stmt.where(ChangeSet.status == status)
        stmt = stmt.order_by(desc(ChangeSet.created_at)).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)

        cs_ids = [row.id for row in rows]
        action_counts: dict[str, int] = {}
        if cs_ids:
            count_rows = list(
                self.db.execute(
                    select(ChangeAction.change_set_id, func.count())
                    .where(ChangeAction.change_set_id.in_(cs_ids))
                    .group_by(ChangeAction.change_set_id)
                ).all()
            )
            action_counts = {row[0]: int(row[1]) for row in count_rows}

        items = [
            {
                "change_set_id": row.id,
                "status": row.status,
                "actor": {"type": row.actor_type, "id": row.actor_id},
                "tool": row.tool,
                "summary": row.summary_json,
                "actions_count": action_counts.get(row.id, 0),
                "created_at": row.created_at,
                "committed_at": row.committed_at,
            }
            for row in rows
        ]
        return items, total

    def get_change(self, change_set_id: str) -> Optional[dict]:
        row = self.db.get(ChangeSet, change_set_id)
        if not row:
            return None
        actions = list(
            self.db.scalars(
                select(ChangeAction)
                .where(ChangeAction.change_set_id == change_set_id)
                .order_by(ChangeAction.action_index.asc(), ChangeAction.id.asc())
            )
        )
        return {
            "change_set_id": row.id,
            "status": row.status,
            "actor": {"type": row.actor_type, "id": row.actor_id},
            "tool": row.tool,
            "summary": row.summary_json,
            "diff_items": row.diff_json,
            "created_at": row.created_at,
            "committed_at": row.committed_at,
            "actions": [
                {
                    "action_id": action.id,
                    "action_index": action.action_index,
                    "action_type": action.action_type,
                    "payload": action.payload_json,
                    "apply_result": action.apply_result_json,
                }
                for action in actions
            ],
        }

    def reject(self, change_set_id: str) -> Optional[str]:
        row = self.db.get(ChangeSet, change_set_id)
        if not row:
            return None
        if row.status != "proposed":
            raise ValueError("CHANGE_SET_NOT_PROPOSED")
        self.db.delete(row)
        self.db.commit()
        return change_set_id

    def dry_run(self, payload: DryRunIn) -> ChangeSet:
        for action in payload.actions:
            self._prevalidate_dry_run_action(action.type, action.payload)

        creates = sum(1 for a in payload.actions if a.type in CREATE_ACTIONS)
        updates = sum(1 for a in payload.actions if a.type in UPDATE_ACTIONS)
        diff_items = [self._build_diff_item(a.type, a.payload) for a in payload.actions]
        if not diff_items:
            diff_items = [
                {
                    "entity": "unknown",
                    "action": "other",
                    "fields": [],
                    "text": "no-op",
                }
            ]
        summary = {
            "creates": creates,
            "updates": updates,
            "duplicate_candidates": 0,
            "task_create": 0,
            "task_update": 0,
            "note_append": 0,
            "note_patch": 0,
            "journal_upsert": 0,
            "idea_create": 0,
            "idea_patch": 0,
            "idea_promote": 0,
            "route_create": 0,
            "route_patch": 0,
            "route_node_create": 0,
            "route_node_patch": 0,
            "route_node_delete": 0,
            "route_edge_create": 0,
            "route_edge_patch": 0,
            "route_edge_delete": 0,
            "route_node_log_append": 0,
            "knowledge_create": 0,
            "knowledge_patch": 0,
            "knowledge_archive": 0,
            "knowledge_delete": 0,
            "link_create": 0,
            "link_delete": 0,
            "inbox_capture": 0,
        }
        for action in payload.actions:
            if action.type == "create_task":
                summary["task_create"] += 1
            elif action.type == "update_task":
                summary["task_update"] += 1
            elif action.type == "append_note":
                summary["note_append"] += 1
            elif action.type == "patch_note":
                summary["note_patch"] += 1
            elif action.type == "upsert_journal_append":
                summary["journal_upsert"] += 1
            elif action.type == "create_idea":
                summary["idea_create"] += 1
            elif action.type == "patch_idea":
                summary["idea_patch"] += 1
            elif action.type == "promote_idea":
                summary["idea_promote"] += 1
            elif action.type == "create_route":
                summary["route_create"] += 1
            elif action.type == "patch_route":
                summary["route_patch"] += 1
            elif action.type == "create_route_node":
                summary["route_node_create"] += 1
            elif action.type == "patch_route_node":
                summary["route_node_patch"] += 1
            elif action.type == "delete_route_node":
                summary["route_node_delete"] += 1
            elif action.type == "create_route_edge":
                summary["route_edge_create"] += 1
            elif action.type == "patch_route_edge":
                summary["route_edge_patch"] += 1
            elif action.type == "delete_route_edge":
                summary["route_edge_delete"] += 1
            elif action.type == "append_route_node_log":
                summary["route_node_log_append"] += 1
            elif action.type == "create_knowledge":
                summary["knowledge_create"] += 1
            elif action.type == "patch_knowledge":
                summary["knowledge_patch"] += 1
            elif action.type == "archive_knowledge":
                summary["knowledge_archive"] += 1
            elif action.type == "delete_knowledge":
                summary["knowledge_delete"] += 1
            elif action.type in {"link_entities", "create_link"}:
                summary["link_create"] += 1
            elif action.type == "delete_link":
                summary["link_delete"] += 1
            elif action.type == "capture_inbox":
                summary["inbox_capture"] += 1
            for key in action.payload.keys():
                if key in {"task_id", "note_id", "id"}:
                    continue
                field_key = f"field_{key}"
                summary[field_key] = summary.get(field_key, 0) + 1

        change_set = ChangeSet(
            id=f"chg_{uuid.uuid4().hex[:12]}",
            actor_type=payload.actor.type,
            actor_id=payload.actor.id,
            tool=payload.tool,
            status="proposed",
            summary_json=summary,
            diff_json=diff_items,
        )
        self.db.add(change_set)
        self.db.flush()
        for idx, action in enumerate(payload.actions, start=1):
            self.db.add(
                ChangeAction(
                    id=f"cha_{uuid.uuid4().hex[:12]}",
                    change_set_id=change_set.id,
                    action_index=idx,
                    action_type=action.type,
                    payload_json=action.payload,
                    apply_result_json=None,
                )
            )
        self.db.commit()
        self.db.refresh(change_set)
        return change_set

    def _prevalidate_dry_run_action(self, action_type: str, payload: dict[str, Any]) -> None:
        if action_type == "create_task":
            model = TaskCreate.model_validate(payload)
            validator = TaskService(self.db)
            validator._validate_topic(model.topic_id)
            validator._validate_cancel_reason_for_cancelled_status(model.status, model.cancelled_reason)
            return
        if action_type == "update_task":
            task_id = payload.get("task_id")
            if not task_id:
                raise ValueError("TASK_ID_REQUIRED")
            patch_payload = {k: v for k, v in payload.items() if k != "task_id"}
            patch_model = TaskPatch.model_validate(patch_payload)
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            return
        if action_type == "append_note":
            model = NoteAppend.model_validate(payload)
            if model.topic_id:
                TaskService(self.db)._validate_topic(model.topic_id)
            return
        if action_type == "patch_note":
            note_id = payload.get("note_id")
            if not note_id:
                raise ValueError("NOTE_ID_REQUIRED")
            note = self.db.get(Note, note_id)
            if note is None:
                raise ValueError("NOTE_NOT_FOUND")
            body_append = payload.get("body_append")
            raw_patch = {k: v for k, v in payload.items() if k not in {"note_id", "body_append", "source"}}
            patch_model = NotePatch.model_validate(raw_patch)
            patch_data = patch_model.model_dump(exclude_unset=True)
            if body_append is None and not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            if "topic_id" in patch_data and patch_data["topic_id"] is not None:
                TaskService(self.db)._validate_topic(patch_data["topic_id"])
            if body_append is not None and not str(body_append).strip():
                raise ValueError("NOTE_BODY_APPEND_REQUIRED")
            return
        if action_type == "upsert_journal_append":
            model = JournalUpsertAppendIn.model_validate(payload)
            if not model.append_text.strip():
                raise ValueError("JOURNAL_APPEND_TEXT_REQUIRED")
            return
        if action_type == "create_idea":
            model = IdeaCreate.model_validate(payload)
            if self.db.get(Task, model.task_id) is None:
                raise ValueError("TASK_NOT_FOUND")
            if model.topic_id and self.db.get(Topic, model.topic_id) is None:
                raise ValueError("TOPIC_NOT_FOUND")
            return
        if action_type == "patch_idea":
            idea_id = payload.get("idea_id")
            if not idea_id:
                raise ValueError("IDEA_ID_REQUIRED")
            idea = self.db.get(Idea, idea_id)
            if idea is None:
                raise ValueError("IDEA_NOT_FOUND")
            raw_patch = {k: v for k, v in payload.items() if k != "idea_id"}
            patch_model = IdeaPatch.model_validate(raw_patch)
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            if "status" in patch_data and patch_data["status"] != idea.status:
                allowed = IDEA_TRANSITIONS.get(idea.status, set())
                if patch_data["status"] not in allowed:
                    raise ValueError("IDEA_INVALID_STATUS_TRANSITION")
            if "topic_id" in patch_data and patch_data["topic_id"] is not None:
                if self.db.get(Topic, patch_data["topic_id"]) is None:
                    raise ValueError("TOPIC_NOT_FOUND")
            return
        if action_type == "promote_idea":
            idea_id = payload.get("idea_id")
            if not idea_id:
                raise ValueError("IDEA_ID_REQUIRED")
            idea = self.db.get(Idea, idea_id)
            if idea is None:
                raise ValueError("IDEA_NOT_FOUND")
            if idea.status != "ready":
                raise ValueError("IDEA_NOT_READY")
            model = IdeaPromoteIn.model_validate({k: v for k, v in payload.items() if k != "idea_id"})
            route = self.db.get(Route, model.route_id)
            if route is None:
                raise ValueError("ROUTE_NOT_FOUND")
            if route.task_id and idea.task_id and route.task_id != idea.task_id:
                raise ValueError("IDEA_ROUTE_TASK_MISMATCH")
            return
        if action_type == "create_route":
            model = RouteCreate.model_validate(payload)
            validator = RouteService(self.db)
            validator._validate_task(model.task_id)
            validator._validate_parent_route(model.parent_route_id)
            if model.status == "active":
                validator._ensure_single_active(task_id=model.task_id)
                task = self.db.get(Task, model.task_id)
                if task is None:
                    raise ValueError("TASK_NOT_FOUND")
                if task.status in {"done", "cancelled"}:
                    raise ValueError("TASK_INVALID_STATUS_TRANSITION")
            return
        if action_type == "patch_route":
            route_id = payload.get("route_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            route = self.db.get(Route, route_id)
            if route is None:
                raise ValueError("ROUTE_NOT_FOUND")
            patch_model = RoutePatch.model_validate({k: v for k, v in payload.items() if k != "route_id"})
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            validator = RouteService(self.db)
            if "parent_route_id" in patch_data and patch_data["parent_route_id"] != route.parent_route_id:
                if route.status != "candidate":
                    raise ValueError("ROUTE_PARENT_REWIRE_FORBIDDEN")
                validator._validate_parent_route(patch_data["parent_route_id"])
            if "status" in patch_data and patch_data["status"] != route.status:
                validator._validate_route_transition(route.status, patch_data["status"])
                if patch_data["status"] == "active":
                    validator._ensure_single_active(task_id=route.task_id, ignore_route_id=route.id)
                    if route.task_id:
                        task = self.db.get(Task, route.task_id)
                        if task is None:
                            raise ValueError("TASK_NOT_FOUND")
                        if task.status in {"done", "cancelled"}:
                            raise ValueError("TASK_INVALID_STATUS_TRANSITION")
            return
        if action_type == "create_route_node":
            route_id = payload.get("route_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            model = RouteNodeCreate.model_validate({k: v for k, v in payload.items() if k != "route_id"})
            graph = RouteGraphService(self.db)
            graph._ensure_route(route_id)
            graph._ensure_parent_node_valid(route_id=route_id, parent_node_id=model.parent_node_id, node_id=None)
            return
        if action_type == "patch_route_node":
            route_id = payload.get("route_id")
            node_id = payload.get("node_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            if not node_id:
                raise ValueError("ROUTE_NODE_ID_REQUIRED")
            graph = RouteGraphService(self.db)
            graph._ensure_node_in_route(route_id, node_id)
            patch_model = RouteNodePatch.model_validate(
                {k: v for k, v in payload.items() if k not in {"route_id", "node_id"}}
            )
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            if "parent_node_id" in patch_data:
                graph._ensure_parent_node_valid(
                    route_id=route_id,
                    parent_node_id=patch_data.get("parent_node_id"),
                    node_id=node_id,
                )
            return
        if action_type == "delete_route_node":
            route_id = payload.get("route_id")
            node_id = payload.get("node_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            if not node_id:
                raise ValueError("ROUTE_NODE_ID_REQUIRED")
            graph = RouteGraphService(self.db)
            graph._ensure_node_in_route(route_id, node_id)
            has_successor = self.db.scalar(
                select(func.count()).where(RouteEdge.route_id == route_id, RouteEdge.from_node_id == node_id)
            )
            if int(has_successor or 0) > 0:
                raise ValueError("ROUTE_NODE_HAS_SUCCESSORS")
            return
        if action_type == "create_route_edge":
            route_id = payload.get("route_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            model = RouteEdgeCreate.model_validate({k: v for k, v in payload.items() if k != "route_id"})
            graph = RouteGraphService(self.db)
            graph._ensure_route(route_id)
            if model.from_node_id == model.to_node_id:
                raise ValueError("ROUTE_EDGE_SELF_LOOP")
            from_node = self.db.get(RouteNode, model.from_node_id)
            to_node = self.db.get(RouteNode, model.to_node_id)
            if from_node is None or to_node is None:
                raise ValueError("ROUTE_EDGE_NODE_NOT_FOUND")
            if from_node.route_id != route_id or to_node.route_id != route_id:
                raise ValueError("ROUTE_EDGE_CROSS_ROUTE")
            existing = self.db.scalar(
                select(RouteEdge).where(
                    RouteEdge.route_id == route_id,
                    RouteEdge.from_node_id == model.from_node_id,
                    RouteEdge.to_node_id == model.to_node_id,
                )
            )
            if existing is not None:
                raise ValueError("ROUTE_EDGE_DUPLICATE")
            expected_relation = graph._infer_edge_relation(
                from_node_type=from_node.node_type, to_node_type=to_node.node_type
            )
            if model.relation != expected_relation:
                raise ValueError("ROUTE_EDGE_RELATION_MISMATCH")
            return
        if action_type == "patch_route_edge":
            route_id = payload.get("route_id")
            edge_id = payload.get("edge_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            if not edge_id:
                raise ValueError("ROUTE_EDGE_ID_REQUIRED")
            edge = self.db.scalar(select(RouteEdge).where(RouteEdge.id == edge_id, RouteEdge.route_id == route_id))
            if edge is None:
                raise ValueError("ROUTE_EDGE_NOT_FOUND")
            patch_model = RouteEdgePatch.model_validate(
                {k: v for k, v in payload.items() if k not in {"route_id", "edge_id"}}
            )
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            return
        if action_type == "delete_route_edge":
            route_id = payload.get("route_id")
            edge_id = payload.get("edge_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            if not edge_id:
                raise ValueError("ROUTE_EDGE_ID_REQUIRED")
            edge = self.db.scalar(select(RouteEdge).where(RouteEdge.id == edge_id, RouteEdge.route_id == route_id))
            if edge is None:
                raise ValueError("ROUTE_EDGE_NOT_FOUND")
            return
        if action_type == "append_route_node_log":
            route_id = payload.get("route_id")
            node_id = payload.get("node_id")
            if not route_id:
                raise ValueError("ROUTE_ID_REQUIRED")
            if not node_id:
                raise ValueError("ROUTE_NODE_ID_REQUIRED")
            RouteGraphService(self.db)._ensure_node_in_route(route_id, node_id)
            NodeLogCreate.model_validate({k: v for k, v in payload.items() if k not in {"route_id", "node_id"}})
            return
        if action_type == "create_knowledge":
            KnowledgeCreate.model_validate(payload)
            return
        if action_type == "patch_knowledge":
            item_id = payload.get("item_id") or payload.get("note_id")
            if not item_id:
                raise ValueError("KNOWLEDGE_ID_REQUIRED")
            note = self.db.get(Note, item_id)
            if note is None:
                raise ValueError("KNOWLEDGE_NOT_FOUND")
            patch_model = KnowledgePatch.model_validate(
                {k: v for k, v in payload.items() if k not in {"item_id", "note_id"}}
            )
            patch_data = patch_model.model_dump(exclude_unset=True)
            if not patch_data:
                raise ValueError("NO_PATCH_FIELDS")
            return
        if action_type == "archive_knowledge":
            item_id = payload.get("item_id") or payload.get("note_id")
            if not item_id:
                raise ValueError("KNOWLEDGE_ID_REQUIRED")
            note = self.db.get(Note, item_id)
            if note is None:
                raise ValueError("KNOWLEDGE_NOT_FOUND")
            return
        if action_type == "delete_knowledge":
            item_id = payload.get("item_id") or payload.get("note_id")
            if not item_id:
                raise ValueError("KNOWLEDGE_ID_REQUIRED")
            note = self.db.get(Note, item_id)
            if note is None:
                raise ValueError("KNOWLEDGE_NOT_FOUND")
            return
        if action_type in {"create_link", "link_entities"}:
            LinkCreate.model_validate(payload)
            return
        if action_type == "delete_link":
            link_id = payload.get("link_id")
            if not link_id:
                raise ValueError("LINK_ID_REQUIRED")
            link = self.db.get(Link, link_id)
            if link is None:
                raise ValueError("LINK_NOT_FOUND")
            return
        if action_type == "capture_inbox":
            InboxCapture.model_validate(payload)
            return

    def commit(self, change_set_id: str, payload: CommitIn) -> tuple[Optional[Commit], Optional[ChangeSet]]:
        change_set = self.db.get(ChangeSet, change_set_id)
        if not change_set:
            return None, None

        if payload.client_request_id:
            idem_commit = self.db.scalars(
                select(Commit).where(Commit.client_request_id == payload.client_request_id).limit(1)
            ).first()
            if idem_commit:
                idem_change_set = self.db.get(ChangeSet, idem_commit.change_set_id)
                return idem_commit, idem_change_set

        existing = self.db.scalars(select(Commit).where(Commit.change_set_id == change_set_id).limit(1)).first()
        if existing:
            if change_set.status != "committed":
                change_set.status = "committed"
                change_set.committed_at = existing.committed_at
                self.db.add(change_set)
                self.db.commit()
                self.db.refresh(change_set)
            return existing, change_set

        actions = list(
            self.db.scalars(
                select(ChangeAction)
                .where(ChangeAction.change_set_id == change_set_id)
                .order_by(ChangeAction.action_index.asc(), ChangeAction.id.asc())
            )
        )
        if not actions:
            raise ValueError("CHANGESET_ACTIONS_EMPTY")

        change_set.status = "committed"
        change_set.committed_at = datetime.now(timezone.utc)
        commit = Commit(
            id=f"cmt_{uuid.uuid4().hex[:12]}",
            change_set_id=change_set_id,
            committed_by_type=payload.approved_by.type,
            committed_by_id=payload.approved_by.id,
            committed_at=change_set.committed_at,
            client_request_id=payload.client_request_id,
        )

        try:
            for action in actions:
                action.apply_result_json = self._apply_action(action)
                self.db.add(action)
                applied = action.apply_result_json or {}
                target_type = str(applied.get("entity") or "unknown")
                target_id = str(applied.get("entity_id") or change_set.id)
                log_audit_event(
                    self.db,
                    actor_type=payload.approved_by.type,
                    actor_id=payload.approved_by.id,
                    tool=change_set.tool,
                    action="changes_apply_action",
                    target_type=target_type,
                    target_id=target_id,
                    source_refs=self._extract_source_refs(action.action_type, action.payload_json or {}),
                    metadata={
                        "request_id": payload.client_request_id,
                        "change_set_id": change_set.id,
                        "commit_id": commit.id,
                        "action_id": action.id,
                        "action_index": action.action_index,
                        "action_type": action.action_type,
                    },
                    auto_commit=False,
                )

            self.db.add(change_set)
            self.db.add(commit)
            self.db.commit()
            self.db.refresh(commit)
            self.db.refresh(change_set)
        except (ValidationError, ValueError):
            self.db.rollback()
            raise
        except IntegrityError:
            self.db.rollback()
            if payload.client_request_id:
                idem_commit = self.db.scalars(
                    select(Commit).where(Commit.client_request_id == payload.client_request_id).limit(1)
                ).first()
                if idem_commit:
                    idem_change_set = self.db.get(ChangeSet, idem_commit.change_set_id)
                    return idem_commit, idem_change_set
            raise
        return commit, change_set

    def undo_last(self, payload: UndoIn) -> Optional[tuple[str, str]]:
        if payload.client_request_id:
            idempotent = self._find_undo_commit_by_client_request_id(payload.client_request_id)
            if idempotent:
                return idempotent

        target = self.db.execute(
            select(Commit, ChangeSet)
            .join(ChangeSet, ChangeSet.id == Commit.change_set_id)
            .where(ChangeSet.tool != "undo", ChangeSet.status == "committed")
            # Use change-set committed_at (python-side timestamp) for deterministic recency.
            .order_by(desc(ChangeSet.committed_at), desc(Commit.id))
            .limit(1)
        ).first()
        if not target:
            return None
        target_commit, target_change_set = target

        actions = list(
            self.db.scalars(
                select(ChangeAction)
                .where(ChangeAction.change_set_id == target_change_set.id)
                .order_by(ChangeAction.action_index.desc(), ChangeAction.id.desc())
            )
        )
        if not actions:
            raise ValueError("CHANGESET_ACTIONS_EMPTY")

        now = datetime.now(timezone.utc)
        revert_change_set = ChangeSet(
            id=f"chg_{uuid.uuid4().hex[:12]}",
            actor_type=payload.requested_by.type,
            actor_id=payload.requested_by.id,
            tool="undo",
            status="committed",
            summary_json={
                "undone_change_set_id": target_change_set.id,
                "undone_commit_id": target_commit.id,
            },
            diff_json=[
                {
                    "entity": "changeset",
                    "action": "revert",
                    "fields": [],
                    "text": f"undo change_set={target_change_set.id}",
                }
            ],
            committed_at=now,
        )
        revert_commit = Commit(
            id=f"cmt_{uuid.uuid4().hex[:12]}",
            change_set_id=revert_change_set.id,
            committed_by_type=payload.requested_by.type,
            committed_by_id=payload.requested_by.id,
            committed_at=now,
            client_request_id=payload.client_request_id,
        )
        try:
            for action in actions:
                self._rollback_action(action)
                applied = action.apply_result_json or {}
                target_type = str(applied.get("entity") or "unknown")
                target_id = str(applied.get("entity_id") or target_change_set.id)
                log_audit_event(
                    self.db,
                    actor_type=payload.requested_by.type,
                    actor_id=payload.requested_by.id,
                    tool="undo",
                    action="changes_undo_action",
                    target_type=target_type,
                    target_id=target_id,
                    source_refs=[payload.reason],
                    metadata={
                        "request_id": payload.client_request_id,
                        "undone_change_set_id": target_change_set.id,
                        "undone_commit_id": target_commit.id,
                        "revert_commit_id": revert_commit.id,
                        "action_id": action.id,
                        "action_index": action.action_index,
                        "action_type": action.action_type,
                    },
                    auto_commit=False,
                )

            target_change_set.status = "reverted"
            self.db.add(target_change_set)
            self.db.add(revert_change_set)
            self.db.add(revert_commit)
            self.db.commit()
            self.db.refresh(revert_commit)
            return target_commit.id, revert_commit.id
        except IntegrityError:
            self.db.rollback()
            if payload.client_request_id:
                idempotent = self._find_undo_commit_by_client_request_id(payload.client_request_id)
                if idempotent:
                    return idempotent
            raise
        except ValueError:
            self.db.rollback()
            raise

    def _build_diff_line(self, action_type: str, payload: dict) -> str:
        if action_type == "create_task":
            parts = []
            for key in ["title", "status", "priority", "cycle_id", "due"]:
                if key in payload and payload.get(key) is not None:
                    parts.append(f"{key}={payload.get(key)}")
            if not parts:
                return "create_task prepared"
            return f"create_task: {', '.join(parts)}"
        if action_type == "update_task":
            fields = [k for k in payload.keys() if k not in {"task_id"}]
            return f"update_task: {', '.join(fields)}" if fields else "update_task prepared"
        if action_type == "append_note":
            fields = [k for k in payload.keys() if k not in {"id", "note_id"}]
            return f"append_note: {', '.join(fields)}" if fields else "append_note prepared"
        if action_type == "patch_note":
            fields = [k for k in payload.keys() if k not in {"id", "note_id"}]
            return f"patch_note: {', '.join(fields)}" if fields else "patch_note prepared"
        if action_type == "upsert_journal_append":
            date_value = payload.get("journal_date")
            return f"upsert_journal_append: journal_date={date_value}" if date_value else "upsert_journal_append prepared"
        if action_type in {"link_entities", "create_link"}:
            fields = [k for k in payload.keys() if k not in {"id"}]
            return f"link_entities: {', '.join(fields)}" if fields else "link_entities prepared"
        if action_type == "delete_link":
            return f"delete_link: link_id={payload.get('link_id')}" if payload.get("link_id") else "delete_link prepared"
        if action_type in {
            "create_idea",
            "patch_idea",
            "promote_idea",
            "create_route",
            "patch_route",
            "create_route_node",
            "patch_route_node",
            "delete_route_node",
            "create_route_edge",
            "patch_route_edge",
            "delete_route_edge",
            "append_route_node_log",
            "create_knowledge",
            "patch_knowledge",
            "archive_knowledge",
            "delete_knowledge",
            "capture_inbox",
        }:
            fields = [k for k in payload.keys() if k not in {"id"}]
            return f"{action_type}: {', '.join(fields)}" if fields else f"{action_type} prepared"
        return f"{action_type} prepared"

    def _build_diff_item(self, action_type: str, payload: dict) -> dict:
        entity_map = {
            "create_task": "task",
            "update_task": "task",
            "append_note": "note",
            "patch_note": "note",
            "upsert_journal_append": "journal",
            "link_entities": "link",
            "create_link": "link",
            "delete_link": "link",
            "create_idea": "idea",
            "patch_idea": "idea",
            "promote_idea": "route_node",
            "create_route": "route",
            "patch_route": "route",
            "create_route_node": "route_node",
            "patch_route_node": "route_node",
            "delete_route_node": "route_node",
            "create_route_edge": "route_edge",
            "patch_route_edge": "route_edge",
            "delete_route_edge": "route_edge",
            "append_route_node_log": "node_log",
            "create_knowledge": "knowledge",
            "patch_knowledge": "knowledge",
            "archive_knowledge": "knowledge",
            "delete_knowledge": "knowledge",
            "capture_inbox": "inbox",
        }
        action_map = {
            "create_task": "create",
            "update_task": "update",
            "append_note": "append",
            "patch_note": "update",
            "upsert_journal_append": "upsert",
            "link_entities": "link",
            "create_link": "create",
            "delete_link": "delete",
            "create_idea": "create",
            "patch_idea": "update",
            "promote_idea": "create",
            "create_route": "create",
            "patch_route": "update",
            "create_route_node": "create",
            "patch_route_node": "update",
            "delete_route_node": "delete",
            "create_route_edge": "create",
            "patch_route_edge": "update",
            "delete_route_edge": "delete",
            "append_route_node_log": "append",
            "create_knowledge": "create",
            "patch_knowledge": "update",
            "archive_knowledge": "archive",
            "delete_knowledge": "delete",
            "capture_inbox": "create",
        }
        fields = [k for k in payload.keys() if k not in {"id", "task_id", "note_id", "idea_id"}]
        text = self._build_diff_line(action_type, payload)
        return {
            "entity": entity_map.get(action_type, "unknown"),
            "action": action_map.get(action_type, "other"),
            "fields": fields,
            "text": text,
        }

    def _apply_action(self, action: ChangeAction) -> dict:
        payload = action.payload_json or {}
        if action.action_type == "create_task":
            return self._apply_create_task(payload)
        if action.action_type == "update_task":
            return self._apply_update_task(payload)
        if action.action_type == "append_note":
            return self._apply_append_note(payload)
        if action.action_type == "patch_note":
            return self._apply_patch_note(payload)
        if action.action_type == "upsert_journal_append":
            return self._apply_upsert_journal_append(payload)
        if action.action_type in {"link_entities", "create_link"}:
            return self._apply_link(payload)
        if action.action_type == "delete_link":
            return self._apply_delete_link(payload)
        if action.action_type == "create_idea":
            return self._apply_create_idea(payload)
        if action.action_type == "patch_idea":
            return self._apply_patch_idea(payload)
        if action.action_type == "promote_idea":
            return self._apply_promote_idea(payload)
        if action.action_type == "create_route":
            return self._apply_create_route(payload)
        if action.action_type == "patch_route":
            return self._apply_patch_route(payload)
        if action.action_type == "create_route_node":
            return self._apply_create_route_node(payload)
        if action.action_type == "patch_route_node":
            return self._apply_patch_route_node(payload)
        if action.action_type == "delete_route_node":
            return self._apply_delete_route_node(payload)
        if action.action_type == "create_route_edge":
            return self._apply_create_route_edge(payload)
        if action.action_type == "patch_route_edge":
            return self._apply_patch_route_edge(payload)
        if action.action_type == "delete_route_edge":
            return self._apply_delete_route_edge(payload)
        if action.action_type == "append_route_node_log":
            return self._apply_append_route_node_log(payload)
        if action.action_type == "create_knowledge":
            return self._apply_create_knowledge(payload)
        if action.action_type == "patch_knowledge":
            return self._apply_patch_knowledge(payload)
        if action.action_type == "archive_knowledge":
            return self._apply_archive_knowledge(payload)
        if action.action_type == "delete_knowledge":
            return self._apply_delete_knowledge(payload)
        if action.action_type == "capture_inbox":
            return self._apply_capture_inbox(payload)
        raise ValueError("CHANGE_ACTION_TYPE_UNSUPPORTED")

    def _apply_create_task(self, payload: dict) -> dict:
        model = TaskCreate.model_validate(payload)
        validator = TaskService(self.db)
        validator._validate_topic(model.topic_id)
        validator._validate_cancel_reason_for_cancelled_status(model.status, model.cancelled_reason)

        task = Task(
            id=f"tsk_{uuid.uuid4().hex[:12]}",
            title=model.title,
            description=model.description,
            acceptance_criteria=model.acceptance_criteria,
            topic_id=model.topic_id,
            status=model.status,
            cancelled_reason=model.cancelled_reason,
            priority=model.priority,
            due=model.due,
            source=model.source,
            cycle_id=model.cycle_id,
        )
        self.db.add(task)
        self.db.flush()
        source_entry_id = f"tsrc_{uuid.uuid4().hex[:12]}"
        self.db.add(
            TaskSource(
                id=source_entry_id,
                task_id=task.id,
                source_kind="text",
                source_ref=model.source,
                excerpt=None,
            )
        )
        return {
            "status": "applied",
            "action_type": "create_task",
            "entity": "task",
            "entity_id": task.id,
            "source_entry_id": source_entry_id,
        }

    def _apply_update_task(self, payload: dict) -> dict:
        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("TASK_ID_REQUIRED")
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError("TASK_NOT_FOUND")

        patch_payload = {k: v for k, v in payload.items() if k != "task_id"}
        patch_model = TaskPatch.model_validate(patch_payload)
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        validator = TaskService(self.db)
        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            validator._validate_topic(patch_data["topic_id"])
        if "status" in patch_data:
            validator._validate_status_transition(task.status, patch_data["status"])
        validator._validate_cancel_reason_patch(task=task, patch_data=patch_data)

        before = {key: self._json_safe(getattr(task, key)) for key in patch_data.keys()}
        for key, value in patch_data.items():
            setattr(task, key, value)
        self.db.add(task)
        source_entry_id: Optional[str] = None
        if patch_data.get("source"):
            source_entry_id = f"tsrc_{uuid.uuid4().hex[:12]}"
            self.db.add(
                TaskSource(
                    id=source_entry_id,
                    task_id=task.id,
                    source_kind="text",
                    source_ref=str(patch_data["source"]),
                    excerpt=None,
                )
            )
        after = {key: self._json_safe(getattr(task, key)) for key in patch_data.keys()}
        result = {
            "status": "applied",
            "action_type": "update_task",
            "entity": "task",
            "entity_id": task.id,
            "before": before,
            "after": after,
        }
        if source_entry_id:
            result["source_entry_id"] = source_entry_id
        return result

    def _apply_append_note(self, payload: dict) -> dict:
        model = NoteAppend.model_validate(payload)
        validator = TaskService(self.db)
        if model.topic_id:
            validator._validate_topic(model.topic_id)

        note = Note(
            id=f"nte_{uuid.uuid4().hex[:12]}",
            title=model.title,
            body=model.body,
            tags_json=model.tags,
            topic_id=model.topic_id,
            status="active",
        )
        self.db.add(note)
        self.db.flush()
        for src in model.sources:
            self.db.add(
                NoteSource(
                    id=f"src_{uuid.uuid4().hex[:12]}",
                    note_id=note.id,
                    source_type=src.type,
                    source_value=src.value,
                )
            )
        return {
            "status": "applied",
            "action_type": "append_note",
            "entity": "note",
            "entity_id": note.id,
        }

    def _apply_patch_note(self, payload: dict) -> dict:
        note_id = payload.get("note_id")
        if not note_id:
            raise ValueError("NOTE_ID_REQUIRED")
        note = self.db.get(Note, note_id)
        if note is None:
            raise ValueError("NOTE_NOT_FOUND")

        body_append = payload.get("body_append")
        source_value = payload.get("source")
        raw_patch = {k: v for k, v in payload.items() if k not in {"note_id", "body_append", "source"}}
        patch_model = NotePatch.model_validate(raw_patch)
        patch_data = patch_model.model_dump(exclude_unset=True)
        if body_append is None and not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            TaskService(self.db)._validate_topic(patch_data["topic_id"])

        touched_fields: set[str] = set()
        for key in ("title", "body", "topic_id", "status"):
            if key in patch_data:
                touched_fields.add(key)
        if "tags" in patch_data:
            touched_fields.add("tags_json")
        if body_append is not None:
            touched_fields.add("body")

        if not touched_fields:
            raise ValueError("NO_PATCH_FIELDS")

        before = {field: self._json_safe(getattr(note, field)) for field in touched_fields}

        if "title" in patch_data:
            note.title = patch_data["title"]
        if "body" in patch_data:
            note.body = patch_data["body"]
        if body_append is not None:
            append_text = str(body_append).strip()
            if not append_text:
                raise ValueError("NOTE_BODY_APPEND_REQUIRED")
            note.body = self._append_block(note.body, append_text)
        if "topic_id" in patch_data:
            note.topic_id = patch_data["topic_id"]
        if "status" in patch_data:
            note.status = patch_data["status"]
        if "tags" in patch_data:
            note.tags_json = patch_data["tags"] or []

        after = {field: self._json_safe(getattr(note, field)) for field in touched_fields}

        source_entry_id: Optional[str] = None
        if source_value:
            source_entry_id = f"src_{uuid.uuid4().hex[:12]}"
            self.db.add(
                NoteSource(
                    id=source_entry_id,
                    note_id=note.id,
                    source_type="text",
                    source_value=str(source_value),
                )
            )

        self.db.add(note)
        result = {
            "status": "applied",
            "action_type": "patch_note",
            "entity": "note",
            "entity_id": note.id,
            "before": before,
            "after": after,
        }
        if source_entry_id:
            result["source_entry_id"] = source_entry_id
        return result

    def _apply_upsert_journal_append(self, payload: dict) -> dict:
        model = JournalUpsertAppendIn.model_validate(payload)
        append_text = model.append_text.strip()
        if not append_text:
            raise ValueError("JOURNAL_APPEND_TEXT_REQUIRED")

        journal = self.db.scalars(select(Journal).where(Journal.journal_date == model.journal_date)).first()
        created = journal is None
        if created:
            journal = Journal(
                id=f"jrn_{uuid.uuid4().hex[:12]}",
                journal_date=model.journal_date,
                raw_content=append_text,
                digest="",
                triage_status="open",
                source=model.source,
            )
            before_raw = None
            after_raw = append_text
        else:
            assert journal is not None
            before_raw = journal.raw_content
            journal.raw_content = self._append_block(journal.raw_content, append_text)
            if not journal.source:
                journal.source = model.source
            after_raw = journal.raw_content

        self.db.add(journal)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "upsert_journal_append",
            "entity": "journal",
            "entity_id": journal.id,
            "journal_date": journal.journal_date.isoformat(),
            "created": created,
            "before_raw_content": before_raw,
            "after_raw_content": after_raw,
            "source": model.source,
        }

    def _apply_link(self, payload: dict) -> dict:
        model = LinkCreate.model_validate(payload)
        link = Link(
            id=f"lnk_{uuid.uuid4().hex[:12]}",
            from_type=model.from_type,
            from_id=model.from_id,
            to_type=model.to_type,
            to_id=model.to_id,
            relation=model.relation,
        )
        self.db.add(link)
        return {
            "status": "applied",
            "action_type": "link_entities",
            "entity": "link",
            "entity_id": link.id,
        }

    def _apply_delete_link(self, payload: dict) -> dict:
        link_id = payload.get("link_id")
        if not link_id:
            raise ValueError("LINK_ID_REQUIRED")
        link = self.db.get(Link, link_id)
        if link is None:
            raise ValueError("LINK_NOT_FOUND")
        before = {
            "id": link.id,
            "from_type": link.from_type,
            "from_id": link.from_id,
            "to_type": link.to_type,
            "to_id": link.to_id,
            "relation": link.relation,
            "created_at": self._json_safe(link.created_at),
        }
        self.db.delete(link)
        return {
            "status": "applied",
            "action_type": "delete_link",
            "entity": "link",
            "entity_id": link_id,
            "before": before,
        }

    def _apply_create_idea(self, payload: dict) -> dict:
        model = IdeaCreate.model_validate(payload)
        if self.db.get(Task, model.task_id) is None:
            raise ValueError("TASK_NOT_FOUND")
        if model.topic_id and self.db.get(Topic, model.topic_id) is None:
            raise ValueError("TOPIC_NOT_FOUND")
        idea = Idea(
            id=f"ida_{uuid.uuid4().hex[:12]}",
            task_id=model.task_id,
            title=model.title,
            problem=model.problem,
            hypothesis=model.hypothesis,
            status=model.status,
            topic_id=model.topic_id,
            source=model.source,
        )
        self.db.add(idea)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "create_idea",
            "entity": "idea",
            "entity_id": idea.id,
        }

    def _apply_patch_idea(self, payload: dict) -> dict:
        idea_id = payload.get("idea_id")
        if not idea_id:
            raise ValueError("IDEA_ID_REQUIRED")
        idea = self.db.get(Idea, idea_id)
        if idea is None:
            raise ValueError("IDEA_NOT_FOUND")
        patch_model = IdeaPatch.model_validate({k: v for k, v in payload.items() if k != "idea_id"})
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        if "status" in patch_data and patch_data["status"] != idea.status:
            allowed = IDEA_TRANSITIONS.get(idea.status, set())
            if patch_data["status"] not in allowed:
                raise ValueError("IDEA_INVALID_STATUS_TRANSITION")
        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            if self.db.get(Topic, patch_data["topic_id"]) is None:
                raise ValueError("TOPIC_NOT_FOUND")

        before = {k: self._json_safe(getattr(idea, k)) for k in patch_data.keys()}
        for key, value in patch_data.items():
            setattr(idea, key, value)
        self.db.add(idea)
        after = {k: self._json_safe(getattr(idea, k)) for k in patch_data.keys()}
        return {
            "status": "applied",
            "action_type": "patch_idea",
            "entity": "idea",
            "entity_id": idea.id,
            "before": before,
            "after": after,
        }

    def _apply_promote_idea(self, payload: dict) -> dict:
        idea_id = payload.get("idea_id")
        if not idea_id:
            raise ValueError("IDEA_ID_REQUIRED")
        idea = self.db.get(Idea, idea_id)
        if idea is None:
            raise ValueError("IDEA_NOT_FOUND")
        if idea.status != "ready":
            raise ValueError("IDEA_NOT_READY")

        model = IdeaPromoteIn.model_validate({k: v for k, v in payload.items() if k != "idea_id"})
        route = self.db.get(Route, model.route_id)
        if route is None:
            raise ValueError("ROUTE_NOT_FOUND")
        if route.task_id and idea.task_id and route.task_id != idea.task_id:
            raise ValueError("IDEA_ROUTE_TASK_MISMATCH")

        max_hint = self.db.scalar(select(func.max(RouteNode.order_hint)).where(RouteNode.route_id == route.id))
        order_hint = int(max_hint or 0) + 1
        default_description = "\n\n".join(
            [part for part in [idea.problem.strip(), idea.hypothesis.strip()] if part]
        )
        node = RouteNode(
            id=f"rtn_{uuid.uuid4().hex[:12]}",
            route_id=route.id,
            node_type=model.node_type,
            title=(model.title or idea.title).strip(),
            description=(model.description if model.description is not None else default_description),
            status="waiting",
            order_hint=order_hint,
            assignee_type="human",
            assignee_id=None,
        )
        self.db.add(node)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "promote_idea",
            "entity": "route_node",
            "entity_id": node.id,
            "idea_id": idea.id,
            "route_id": route.id,
        }

    def _apply_create_route(self, payload: dict) -> dict:
        model = RouteCreate.model_validate(payload)
        validator = RouteService(self.db)
        validator._validate_task(model.task_id)
        validator._validate_parent_route(model.parent_route_id)
        task_before_status: Optional[str] = None
        task_after_status: Optional[str] = None
        if model.status == "active":
            validator._ensure_single_active(task_id=model.task_id)
            task = self.db.get(Task, model.task_id)
            if task is None:
                raise ValueError("TASK_NOT_FOUND")
            if task.status in {"done", "cancelled"}:
                raise ValueError("TASK_INVALID_STATUS_TRANSITION")
            task_before_status = task.status
            if task.status == "todo":
                task.status = "in_progress"
                self.db.add(task)
            task_after_status = task.status

        route = Route(
            id=f"rte_{uuid.uuid4().hex[:12]}",
            task_id=model.task_id,
            name=model.name,
            goal=model.goal,
            status=model.status,
            priority=model.priority,
            owner=model.owner,
            parent_route_id=model.parent_route_id,
        )
        self.db.add(route)
        self.db.flush()
        result = {
            "status": "applied",
            "action_type": "create_route",
            "entity": "route",
            "entity_id": route.id,
        }
        if task_before_status is not None:
            result["task_id"] = model.task_id
            result["task_before_status"] = task_before_status
            result["task_after_status"] = task_after_status
        return result

    def _apply_patch_route(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        route = self.db.get(Route, route_id)
        if route is None:
            raise ValueError("ROUTE_NOT_FOUND")

        patch_model = RoutePatch.model_validate({k: v for k, v in payload.items() if k != "route_id"})
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        validator = RouteService(self.db)
        if "parent_route_id" in patch_data and patch_data["parent_route_id"] != route.parent_route_id:
            if route.status != "candidate":
                raise ValueError("ROUTE_PARENT_REWIRE_FORBIDDEN")
            validator._validate_parent_route(patch_data["parent_route_id"])

        task_before_status: Optional[str] = None
        task_after_status: Optional[str] = None
        if "status" in patch_data and patch_data["status"] != route.status:
            validator._validate_route_transition(route.status, patch_data["status"])
            if patch_data["status"] == "active":
                validator._ensure_single_active(task_id=route.task_id, ignore_route_id=route.id)
                if route.task_id:
                    task = self.db.get(Task, route.task_id)
                    if task is None:
                        raise ValueError("TASK_NOT_FOUND")
                    if task.status in {"done", "cancelled"}:
                        raise ValueError("TASK_INVALID_STATUS_TRANSITION")
                    task_before_status = task.status
                    if task.status == "todo":
                        task.status = "in_progress"
                        self.db.add(task)
                    task_after_status = task.status

        before = {k: self._json_safe(getattr(route, k)) for k in patch_data.keys()}
        for key, value in patch_data.items():
            setattr(route, key, value)
        self.db.add(route)
        after = {k: self._json_safe(getattr(route, k)) for k in patch_data.keys()}
        result = {
            "status": "applied",
            "action_type": "patch_route",
            "entity": "route",
            "entity_id": route.id,
            "before": before,
            "after": after,
        }
        if task_before_status is not None and route.task_id:
            result["task_id"] = route.task_id
            result["task_before_status"] = task_before_status
            result["task_after_status"] = task_after_status
        return result

    def _apply_create_route_node(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        model = RouteNodeCreate.model_validate({k: v for k, v in payload.items() if k != "route_id"})
        graph = RouteGraphService(self.db)
        graph._ensure_route(route_id)
        graph._ensure_parent_node_valid(route_id=route_id, parent_node_id=model.parent_node_id, node_id=None)

        order_hint = model.order_hint
        if order_hint <= 0:
            max_hint = self.db.scalar(select(func.max(RouteNode.order_hint)).where(RouteNode.route_id == route_id))
            order_hint = int(max_hint or 0) + 1

        node = RouteNode(
            id=f"rtn_{uuid.uuid4().hex[:12]}",
            route_id=route_id,
            node_type=model.node_type,
            title=model.title,
            description=model.description,
            status=model.status,
            parent_node_id=model.parent_node_id,
            order_hint=order_hint,
            assignee_type=model.assignee_type,
            assignee_id=model.assignee_id,
        )
        self.db.add(node)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "create_route_node",
            "entity": "route_node",
            "entity_id": node.id,
            "route_id": route_id,
        }

    def _apply_patch_route_node(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        node_id = payload.get("node_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        if not node_id:
            raise ValueError("ROUTE_NODE_ID_REQUIRED")
        graph = RouteGraphService(self.db)
        node = graph._ensure_node_in_route(route_id, node_id)
        patch_model = RouteNodePatch.model_validate(
            {k: v for k, v in payload.items() if k not in {"route_id", "node_id"}}
        )
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        if "parent_node_id" in patch_data:
            graph._ensure_parent_node_valid(
                route_id=route_id,
                parent_node_id=patch_data.get("parent_node_id"),
                node_id=node.id,
            )

        before = {k: self._json_safe(getattr(node, k)) for k in patch_data.keys()}
        for key, value in patch_data.items():
            setattr(node, key, value)
        self.db.add(node)
        after = {k: self._json_safe(getattr(node, k)) for k in patch_data.keys()}
        return {
            "status": "applied",
            "action_type": "patch_route_node",
            "entity": "route_node",
            "entity_id": node.id,
            "before": before,
            "after": after,
        }

    def _apply_delete_route_node(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        node_id = payload.get("node_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        if not node_id:
            raise ValueError("ROUTE_NODE_ID_REQUIRED")
        graph = RouteGraphService(self.db)
        node = graph._ensure_node_in_route(route_id, node_id)
        has_successor = self.db.scalar(
            select(func.count()).where(RouteEdge.route_id == route_id, RouteEdge.from_node_id == node_id)
        )
        if int(has_successor or 0) > 0:
            raise ValueError("ROUTE_NODE_HAS_SUCCESSORS")
        before = {
            "id": node.id,
            "route_id": node.route_id,
            "node_type": node.node_type,
            "title": node.title,
            "description": node.description,
            "status": node.status,
            "parent_node_id": node.parent_node_id,
            "order_hint": node.order_hint,
            "assignee_type": node.assignee_type,
            "assignee_id": node.assignee_id,
            "created_at": self._json_safe(node.created_at),
            "updated_at": self._json_safe(node.updated_at),
        }
        self.db.delete(node)
        return {
            "status": "applied",
            "action_type": "delete_route_node",
            "entity": "route_node",
            "entity_id": node_id,
            "before": before,
        }

    def _apply_create_route_edge(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        model = RouteEdgeCreate.model_validate({k: v for k, v in payload.items() if k != "route_id"})
        graph = RouteGraphService(self.db)
        graph._ensure_route(route_id)
        if model.from_node_id == model.to_node_id:
            raise ValueError("ROUTE_EDGE_SELF_LOOP")
        from_node = self.db.get(RouteNode, model.from_node_id)
        to_node = self.db.get(RouteNode, model.to_node_id)
        if from_node is None or to_node is None:
            raise ValueError("ROUTE_EDGE_NODE_NOT_FOUND")
        if from_node.route_id != route_id or to_node.route_id != route_id:
            raise ValueError("ROUTE_EDGE_CROSS_ROUTE")
        existing = self.db.scalar(
            select(RouteEdge).where(
                RouteEdge.route_id == route_id,
                RouteEdge.from_node_id == model.from_node_id,
                RouteEdge.to_node_id == model.to_node_id,
            )
        )
        if existing is not None:
            raise ValueError("ROUTE_EDGE_DUPLICATE")
        expected_relation = graph._infer_edge_relation(
            from_node_type=from_node.node_type,
            to_node_type=to_node.node_type,
        )
        if model.relation != expected_relation:
            raise ValueError("ROUTE_EDGE_RELATION_MISMATCH")

        edge = RouteEdge(
            id=f"red_{uuid.uuid4().hex[:12]}",
            route_id=route_id,
            from_node_id=model.from_node_id,
            to_node_id=model.to_node_id,
            relation=model.relation,
            description=model.description or "",
        )
        self.db.add(edge)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "create_route_edge",
            "entity": "route_edge",
            "entity_id": edge.id,
            "route_id": route_id,
        }

    def _apply_patch_route_edge(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        edge_id = payload.get("edge_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        if not edge_id:
            raise ValueError("ROUTE_EDGE_ID_REQUIRED")
        edge = self.db.scalar(select(RouteEdge).where(RouteEdge.id == edge_id, RouteEdge.route_id == route_id))
        if edge is None:
            raise ValueError("ROUTE_EDGE_NOT_FOUND")
        patch_model = RouteEdgePatch.model_validate(
            {k: v for k, v in payload.items() if k not in {"route_id", "edge_id"}}
        )
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        before = {"description": self._json_safe(edge.description)}
        if "description" in patch_data:
            edge.description = patch_data["description"] or ""
        self.db.add(edge)
        after = {"description": self._json_safe(edge.description)}
        return {
            "status": "applied",
            "action_type": "patch_route_edge",
            "entity": "route_edge",
            "entity_id": edge.id,
            "before": before,
            "after": after,
        }

    def _apply_delete_route_edge(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        edge_id = payload.get("edge_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        if not edge_id:
            raise ValueError("ROUTE_EDGE_ID_REQUIRED")
        edge = self.db.scalar(select(RouteEdge).where(RouteEdge.id == edge_id, RouteEdge.route_id == route_id))
        if edge is None:
            raise ValueError("ROUTE_EDGE_NOT_FOUND")
        before = {
            "id": edge.id,
            "route_id": edge.route_id,
            "from_node_id": edge.from_node_id,
            "to_node_id": edge.to_node_id,
            "relation": edge.relation,
            "description": edge.description,
            "created_at": self._json_safe(edge.created_at),
        }
        self.db.delete(edge)
        return {
            "status": "applied",
            "action_type": "delete_route_edge",
            "entity": "route_edge",
            "entity_id": edge_id,
            "before": before,
        }

    def _apply_append_route_node_log(self, payload: dict) -> dict:
        route_id = payload.get("route_id")
        node_id = payload.get("node_id")
        if not route_id:
            raise ValueError("ROUTE_ID_REQUIRED")
        if not node_id:
            raise ValueError("ROUTE_NODE_ID_REQUIRED")
        RouteGraphService(self.db)._ensure_node_in_route(route_id, node_id)
        model = NodeLogCreate.model_validate({k: v for k, v in payload.items() if k not in {"route_id", "node_id"}})
        log = NodeLog(
            id=f"nlg_{uuid.uuid4().hex[:12]}",
            node_id=node_id,
            actor_type=model.actor_type,
            actor_id=model.actor_id,
            content=model.content,
            log_type=model.log_type,
            source_ref=model.source_ref,
        )
        self.db.add(log)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "append_route_node_log",
            "entity": "node_log",
            "entity_id": log.id,
            "node_id": node_id,
        }

    def _apply_create_knowledge(self, payload: dict) -> dict:
        model = KnowledgeCreate.model_validate(payload)
        note = Note(
            id=f"nte_{uuid.uuid4().hex[:12]}",
            title=model.title,
            body=model.body,
            category=model.category or infer_knowledge_category(model.title, model.body),
            topic_id=None,
            tags_json=[],
            status="active",
        )
        self.db.add(note)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "create_knowledge",
            "entity": "knowledge",
            "entity_id": note.id,
        }

    def _apply_patch_knowledge(self, payload: dict) -> dict:
        item_id = payload.get("item_id") or payload.get("note_id")
        if not item_id:
            raise ValueError("KNOWLEDGE_ID_REQUIRED")
        note = self.db.get(Note, item_id)
        if note is None:
            raise ValueError("KNOWLEDGE_NOT_FOUND")
        patch_model = KnowledgePatch.model_validate({k: v for k, v in payload.items() if k not in {"item_id", "note_id"}})
        patch_data = patch_model.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        before = {k: self._json_safe(getattr(note, k)) for k in patch_data.keys()}
        for key, value in patch_data.items():
            setattr(note, key, value)
        self.db.add(note)
        after = {k: self._json_safe(getattr(note, k)) for k in patch_data.keys()}
        return {
            "status": "applied",
            "action_type": "patch_knowledge",
            "entity": "knowledge",
            "entity_id": note.id,
            "before": before,
            "after": after,
        }

    def _apply_archive_knowledge(self, payload: dict) -> dict:
        item_id = payload.get("item_id") or payload.get("note_id")
        if not item_id:
            raise ValueError("KNOWLEDGE_ID_REQUIRED")
        note = self.db.get(Note, item_id)
        if note is None:
            raise ValueError("KNOWLEDGE_NOT_FOUND")
        before_status = note.status
        changed = note.status != "archived"
        if changed:
            note.status = "archived"
            self.db.add(note)
        return {
            "status": "applied",
            "action_type": "archive_knowledge",
            "entity": "knowledge",
            "entity_id": note.id,
            "before_status": before_status,
            "after_status": note.status,
            "changed": changed,
        }

    def _apply_delete_knowledge(self, payload: dict) -> dict:
        item_id = payload.get("item_id") or payload.get("note_id")
        if not item_id:
            raise ValueError("KNOWLEDGE_ID_REQUIRED")
        note = self.db.get(Note, item_id)
        if note is None:
            raise ValueError("KNOWLEDGE_NOT_FOUND")
        before_note = {
            "id": note.id,
            "title": note.title,
            "body": note.body,
            "category": note.category,
            "tags_json": self._json_safe(note.tags_json or []),
            "topic_id": note.topic_id,
            "status": note.status,
            "created_at": self._json_safe(note.created_at),
            "updated_at": self._json_safe(note.updated_at),
        }
        before_sources = [
            {
                "id": src.id,
                "note_id": src.note_id,
                "source_type": src.source_type,
                "source_value": src.source_value,
            }
            for src in self.db.scalars(select(NoteSource).where(NoteSource.note_id == note.id))
        ]
        before_links = [
            {
                "id": link.id,
                "from_type": link.from_type,
                "from_id": link.from_id,
                "to_type": link.to_type,
                "to_id": link.to_id,
                "relation": link.relation,
                "created_at": self._json_safe(link.created_at),
            }
            for link in self.db.scalars(
                select(Link).where(
                    or_(
                        and_(Link.from_type == "note", Link.from_id == note.id),
                        and_(Link.to_type == "note", Link.to_id == note.id),
                    )
                )
            )
        ]
        self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.from_type == "note", Link.from_id == note.id),
                    and_(Link.to_type == "note", Link.to_id == note.id),
                )
            )
        )
        self.db.delete(note)
        return {
            "status": "applied",
            "action_type": "delete_knowledge",
            "entity": "knowledge",
            "entity_id": note.id,
            "before_note": before_note,
            "before_sources": before_sources,
            "before_links": before_links,
        }

    def _apply_capture_inbox(self, payload: dict) -> dict:
        model = InboxCapture.model_validate(payload)
        item = InboxItem(
            id=f"inb_{uuid.uuid4().hex[:12]}",
            content=model.content,
            source=model.source,
            status="open",
        )
        self.db.add(item)
        self.db.flush()
        return {
            "status": "applied",
            "action_type": "capture_inbox",
            "entity": "inbox",
            "entity_id": item.id,
            "source": model.source,
        }

    def _rollback_action(self, action: ChangeAction) -> None:
        result = action.apply_result_json or {}
        action_type = (result.get("action_type") or action.action_type or "").strip()
        if not action_type:
            raise ValueError("CHANGE_ACTION_TYPE_UNSUPPORTED")
        if action_type == "create_task":
            self._rollback_create_task(result)
            return
        if action_type == "update_task":
            self._rollback_update_task(result)
            return
        if action_type == "append_note":
            self._rollback_append_note(result)
            return
        if action_type == "patch_note":
            self._rollback_patch_note(result)
            return
        if action_type == "upsert_journal_append":
            self._rollback_upsert_journal_append(result)
            return
        if action_type in {"link_entities", "create_link"}:
            self._rollback_link(result)
            return
        if action_type == "delete_link":
            self._rollback_delete_link(result)
            return
        if action_type == "create_idea":
            self._rollback_create_idea(result)
            return
        if action_type == "patch_idea":
            self._rollback_patch_idea(result)
            return
        if action_type == "promote_idea":
            self._rollback_promote_idea(result)
            return
        if action_type == "create_route":
            self._rollback_create_route(result)
            return
        if action_type == "patch_route":
            self._rollback_patch_route(result)
            return
        if action_type == "create_route_node":
            self._rollback_create_route_node(result)
            return
        if action_type == "patch_route_node":
            self._rollback_patch_route_node(result)
            return
        if action_type == "delete_route_node":
            self._rollback_delete_route_node(result)
            return
        if action_type == "create_route_edge":
            self._rollback_create_route_edge(result)
            return
        if action_type == "patch_route_edge":
            self._rollback_patch_route_edge(result)
            return
        if action_type == "delete_route_edge":
            self._rollback_delete_route_edge(result)
            return
        if action_type == "append_route_node_log":
            self._rollback_append_route_node_log(result)
            return
        if action_type == "create_knowledge":
            self._rollback_create_knowledge(result)
            return
        if action_type == "patch_knowledge":
            self._rollback_patch_knowledge(result)
            return
        if action_type == "archive_knowledge":
            self._rollback_archive_knowledge(result)
            return
        if action_type == "delete_knowledge":
            self._rollback_delete_knowledge(result)
            return
        if action_type == "capture_inbox":
            self._rollback_capture_inbox(result)
            return
        raise ValueError("CHANGE_ACTION_TYPE_UNSUPPORTED")

    def _rollback_create_task(self, result: dict) -> None:
        task_id = result.get("entity_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.from_type == "task", Link.from_id == task_id),
                    and_(Link.to_type == "task", Link.to_id == task_id),
                )
            )
        )
        task = self.db.get(Task, task_id)
        if task:
            self.db.delete(task)

    def _rollback_update_task(self, result: dict) -> None:
        task_id = result.get("entity_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError("TASK_NOT_FOUND")

        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(task, key, self._task_value_from_json(key, value))
        self.db.add(task)

        source_entry_id = result.get("source_entry_id")
        if isinstance(source_entry_id, str) and source_entry_id:
            src = self.db.get(TaskSource, source_entry_id)
            if src:
                self.db.delete(src)

    def _rollback_append_note(self, result: dict) -> None:
        note_id = result.get("entity_id")
        if not isinstance(note_id, str) or not note_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.from_type == "note", Link.from_id == note_id),
                    and_(Link.to_type == "note", Link.to_id == note_id),
                )
            )
        )
        note = self.db.get(Note, note_id)
        if note:
            self.db.delete(note)

    def _rollback_patch_note(self, result: dict) -> None:
        note_id = result.get("entity_id")
        if not isinstance(note_id, str) or not note_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        note = self.db.get(Note, note_id)
        if note is None:
            raise ValueError("NOTE_NOT_FOUND")

        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(note, key, value)
        self.db.add(note)

        source_entry_id = result.get("source_entry_id")
        if isinstance(source_entry_id, str) and source_entry_id:
            src = self.db.get(NoteSource, source_entry_id)
            if src:
                self.db.delete(src)

    def _rollback_upsert_journal_append(self, result: dict) -> None:
        journal_id = result.get("entity_id")
        if not isinstance(journal_id, str) or not journal_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        created = bool(result.get("created"))
        journal = self.db.get(Journal, journal_id)
        if journal is None:
            if created:
                return
            raise ValueError("JOURNAL_NOT_FOUND")

        if created:
            self.db.delete(journal)
            return

        before_raw = result.get("before_raw_content")
        if not isinstance(before_raw, str):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        journal.raw_content = before_raw
        self.db.add(journal)

    def _rollback_link(self, result: dict) -> None:
        link_id = result.get("entity_id")
        if not isinstance(link_id, str) or not link_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        link = self.db.get(Link, link_id)
        if link:
            self.db.delete(link)

    def _rollback_delete_link(self, result: dict) -> None:
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        link_id = before.get("id")
        if not isinstance(link_id, str) or not link_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        if self.db.get(Link, link_id) is not None:
            return
        link = Link(
            id=link_id,
            from_type=str(before.get("from_type") or ""),
            from_id=str(before.get("from_id") or ""),
            to_type=str(before.get("to_type") or ""),
            to_id=str(before.get("to_id") or ""),
            relation=str(before.get("relation") or ""),
            created_at=self._datetime_from_json(before.get("created_at")),
        )
        self.db.add(link)

    def _rollback_create_idea(self, result: dict) -> None:
        idea_id = result.get("entity_id")
        if not isinstance(idea_id, str) or not idea_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        idea = self.db.get(Idea, idea_id)
        if idea:
            self.db.delete(idea)

    def _rollback_patch_idea(self, result: dict) -> None:
        idea_id = result.get("entity_id")
        if not isinstance(idea_id, str) or not idea_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        idea = self.db.get(Idea, idea_id)
        if idea is None:
            raise ValueError("IDEA_NOT_FOUND")
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(idea, key, value)
        self.db.add(idea)

    def _rollback_promote_idea(self, result: dict) -> None:
        node_id = result.get("entity_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        node = self.db.get(RouteNode, node_id)
        if node:
            self.db.delete(node)

    def _rollback_create_route(self, result: dict) -> None:
        route_id = result.get("entity_id")
        if not isinstance(route_id, str) or not route_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        route = self.db.get(Route, route_id)
        if route:
            self.db.delete(route)
        task_id = result.get("task_id")
        before_status = result.get("task_before_status")
        if isinstance(task_id, str) and task_id and isinstance(before_status, str):
            task = self.db.get(Task, task_id)
            if task:
                task.status = before_status
                self.db.add(task)

    def _rollback_patch_route(self, result: dict) -> None:
        route_id = result.get("entity_id")
        if not isinstance(route_id, str) or not route_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        route = self.db.get(Route, route_id)
        if route is None:
            raise ValueError("ROUTE_NOT_FOUND")
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(route, key, value)
        self.db.add(route)
        task_id = result.get("task_id")
        before_status = result.get("task_before_status")
        if isinstance(task_id, str) and task_id and isinstance(before_status, str):
            task = self.db.get(Task, task_id)
            if task:
                task.status = before_status
                self.db.add(task)

    def _rollback_create_route_node(self, result: dict) -> None:
        node_id = result.get("entity_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        node = self.db.get(RouteNode, node_id)
        if node:
            self.db.delete(node)

    def _rollback_patch_route_node(self, result: dict) -> None:
        node_id = result.get("entity_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        node = self.db.get(RouteNode, node_id)
        if node is None:
            raise ValueError("ROUTE_NODE_NOT_FOUND")
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(node, key, value)
        self.db.add(node)

    def _rollback_delete_route_node(self, result: dict) -> None:
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        node_id = before.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        if self.db.get(RouteNode, node_id):
            return
        node = RouteNode(
            id=node_id,
            route_id=str(before.get("route_id") or ""),
            node_type=str(before.get("node_type") or ""),
            title=str(before.get("title") or ""),
            description=str(before.get("description") or ""),
            status=str(before.get("status") or "waiting"),
            parent_node_id=before.get("parent_node_id"),
            order_hint=int(before.get("order_hint") or 0),
            assignee_type=str(before.get("assignee_type") or "human"),
            assignee_id=before.get("assignee_id"),
            created_at=self._datetime_from_json(before.get("created_at")),
            updated_at=self._datetime_from_json(before.get("updated_at")),
        )
        self.db.add(node)

    def _rollback_create_route_edge(self, result: dict) -> None:
        edge_id = result.get("entity_id")
        if not isinstance(edge_id, str) or not edge_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        edge = self.db.get(RouteEdge, edge_id)
        if edge:
            self.db.delete(edge)

    def _rollback_patch_route_edge(self, result: dict) -> None:
        edge_id = result.get("entity_id")
        if not isinstance(edge_id, str) or not edge_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        edge = self.db.get(RouteEdge, edge_id)
        if edge is None:
            raise ValueError("ROUTE_EDGE_NOT_FOUND")
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        edge.description = str(before.get("description") or "")
        self.db.add(edge)

    def _rollback_delete_route_edge(self, result: dict) -> None:
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        edge_id = before.get("id")
        if not isinstance(edge_id, str) or not edge_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        if self.db.get(RouteEdge, edge_id):
            return
        edge = RouteEdge(
            id=edge_id,
            route_id=str(before.get("route_id") or ""),
            from_node_id=str(before.get("from_node_id") or ""),
            to_node_id=str(before.get("to_node_id") or ""),
            relation=str(before.get("relation") or "refine"),
            description=str(before.get("description") or ""),
            created_at=self._datetime_from_json(before.get("created_at")),
        )
        self.db.add(edge)

    def _rollback_append_route_node_log(self, result: dict) -> None:
        log_id = result.get("entity_id")
        if not isinstance(log_id, str) or not log_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        log = self.db.get(NodeLog, log_id)
        if log:
            self.db.delete(log)

    def _rollback_create_knowledge(self, result: dict) -> None:
        item_id = result.get("entity_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        note = self.db.get(Note, item_id)
        if note:
            self.db.delete(note)

    def _rollback_patch_knowledge(self, result: dict) -> None:
        item_id = result.get("entity_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        note = self.db.get(Note, item_id)
        if note is None:
            raise ValueError("KNOWLEDGE_NOT_FOUND")
        before = result.get("before")
        if not isinstance(before, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        for key, value in before.items():
            setattr(note, key, value)
        self.db.add(note)

    def _rollback_archive_knowledge(self, result: dict) -> None:
        item_id = result.get("entity_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        note = self.db.get(Note, item_id)
        if note is None:
            raise ValueError("KNOWLEDGE_NOT_FOUND")
        before_status = result.get("before_status")
        if isinstance(before_status, str):
            note.status = before_status
            self.db.add(note)

    def _rollback_delete_knowledge(self, result: dict) -> None:
        before_note = result.get("before_note")
        if not isinstance(before_note, dict):
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_BEFORE")
        item_id = before_note.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        if self.db.get(Note, item_id) is not None:
            return
        note = Note(
            id=item_id,
            title=str(before_note.get("title") or ""),
            body=str(before_note.get("body") or ""),
            category=str(before_note.get("category") or "mechanism_spec"),
            tags_json=list(before_note.get("tags_json") or []),
            topic_id=before_note.get("topic_id"),
            status=str(before_note.get("status") or "active"),
            created_at=self._datetime_from_json(before_note.get("created_at")),
            updated_at=self._datetime_from_json(before_note.get("updated_at")),
        )
        self.db.add(note)

        before_sources = result.get("before_sources")
        if isinstance(before_sources, list):
            for src in before_sources:
                if not isinstance(src, dict):
                    continue
                src_id = src.get("id")
                if not isinstance(src_id, str) or not src_id:
                    continue
                self.db.add(
                    NoteSource(
                        id=src_id,
                        note_id=item_id,
                        source_type=str(src.get("source_type") or "text"),
                        source_value=str(src.get("source_value") or ""),
                    )
                )

        before_links = result.get("before_links")
        if isinstance(before_links, list):
            for link_payload in before_links:
                if not isinstance(link_payload, dict):
                    continue
                link_id = link_payload.get("id")
                if not isinstance(link_id, str) or not link_id:
                    continue
                self.db.add(
                    Link(
                        id=link_id,
                        from_type=str(link_payload.get("from_type") or ""),
                        from_id=str(link_payload.get("from_id") or ""),
                        to_type=str(link_payload.get("to_type") or ""),
                        to_id=str(link_payload.get("to_id") or ""),
                        relation=str(link_payload.get("relation") or ""),
                        created_at=self._datetime_from_json(link_payload.get("created_at")),
                    )
                )

    def _rollback_capture_inbox(self, result: dict) -> None:
        inbox_id = result.get("entity_id")
        if not isinstance(inbox_id, str) or not inbox_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        row = self.db.get(InboxItem, inbox_id)
        if row:
            self.db.delete(row)

    def _find_undo_commit_by_client_request_id(self, client_request_id: str) -> Optional[tuple[str, str]]:
        row = self.db.execute(
            select(Commit, ChangeSet)
            .join(ChangeSet, ChangeSet.id == Commit.change_set_id)
            .where(Commit.client_request_id == client_request_id, ChangeSet.tool == "undo")
            .limit(1)
        ).first()
        if not row:
            return None
        commit, change_set = row
        summary = change_set.summary_json or {}
        undone_commit_id = summary.get("undone_commit_id")
        if not isinstance(undone_commit_id, str) or not undone_commit_id:
            raise ValueError("UNDO_IDEMPOTENT_SUMMARY_INVALID")
        return undone_commit_id, commit.id

    def _task_value_from_json(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        if key in TASK_DATE_FIELDS:
            if isinstance(value, str):
                return date.fromisoformat(value)
            return value
        if key in TASK_DATETIME_FIELDS:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        return value

    def _datetime_from_json(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return datetime.now(timezone.utc)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        return value

    def _extract_source_refs(self, action_type: str, payload: dict) -> list[str]:
        if action_type == "create_task":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "append_note":
            srcs = payload.get("sources")
            if not isinstance(srcs, list):
                return []
            refs: list[str] = []
            for src in srcs:
                if isinstance(src, dict) and src.get("value"):
                    refs.append(str(src["value"]))
            return refs
        if action_type == "patch_note":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "upsert_journal_append":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "update_task":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "create_idea":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "patch_idea":
            source = payload.get("source")
            return [str(source)] if source else []
        if action_type == "append_route_node_log":
            source = payload.get("source_ref")
            return [str(source)] if source else []
        if action_type == "capture_inbox":
            source = payload.get("source")
            return [str(source)] if source else []
        return []

    def _append_block(self, existing: str, addition: str) -> str:
        trimmed = (existing or "").strip()
        if not trimmed:
            return addition
        return f"{trimmed}\n\n{addition}"
