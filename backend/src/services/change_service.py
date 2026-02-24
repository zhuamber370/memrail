from __future__ import annotations

from datetime import date, datetime, timezone
import uuid
from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import ChangeAction, ChangeSet, Commit, Link, Note, NoteSource, Task, TaskSource
from src.schemas import CommitIn, DryRunIn, LinkCreate, NoteAppend, TaskCreate, TaskPatch, UndoIn
from src.services.audit_service import log_audit_event
from src.services.task_service import TaskService

TASK_DATE_FIELDS = {"due"}
TASK_DATETIME_FIELDS = {"next_review_at", "archived_at"}


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

    def dry_run(self, payload: DryRunIn) -> ChangeSet:
        creates = sum(1 for a in payload.actions if a.type in ("create_task", "append_note"))
        updates = sum(1 for a in payload.actions if a.type == "update_task")
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
        }
        for action in payload.actions:
            if action.type == "create_task":
                summary["task_create"] += 1
            elif action.type == "update_task":
                summary["task_update"] += 1
            elif action.type == "append_note":
                summary["note_append"] += 1
            for key in action.payload.keys():
                if key in {"task_id", "id"}:
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
            .order_by(desc(Commit.committed_at), desc(Commit.id))
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
        if action_type != "create_task":
            return f"{action_type} prepared"
        parts = []
        for key in ["title", "status", "priority", "cycle_id", "next_review_at", "blocked_by_task_id"]:
            if key in payload and payload.get(key) is not None:
                parts.append(f"{key}={payload.get(key)}")
        if not parts:
            return "create_task prepared"
        return f"create_task: {', '.join(parts)}"

    def _build_diff_item(self, action_type: str, payload: dict) -> dict:
        entity_map = {
            "create_task": "task",
            "update_task": "task",
            "append_note": "note",
            "link_entities": "link",
        }
        action_map = {
            "create_task": "create",
            "update_task": "update",
            "append_note": "append",
            "link_entities": "link",
        }
        fields = [k for k in payload.keys() if k not in {"id", "task_id", "note_id"}]
        text = self._build_diff_line(action_type, payload)
        if action_type == "update_task":
            text = f"update_task: {', '.join(fields)}" if fields else "update_task prepared"
        elif action_type == "append_note":
            text = f"append_note: {', '.join(fields)}" if fields else "append_note prepared"
        elif action_type == "link_entities":
            text = f"link_entities: {', '.join(fields)}" if fields else "link_entities prepared"
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
        if action.action_type == "link_entities":
            return self._apply_link(payload)
        raise ValueError("CHANGE_ACTION_TYPE_UNSUPPORTED")

    def _apply_create_task(self, payload: dict) -> dict:
        model = TaskCreate.model_validate(payload)
        validator = TaskService(self.db)
        validator._validate_topic(model.topic_id)
        validator._validate_cancel_reason_for_cancelled_status(model.status, model.cancelled_reason)
        validator._validate_blocker(model.blocked_by_task_id)

        task = Task(
            id=f"tsk_{uuid.uuid4().hex[:12]}",
            title=model.title,
            description=model.description,
            acceptance_criteria=model.acceptance_criteria,
            next_action=model.next_action,
            task_type=model.task_type,
            topic_id=model.topic_id,
            status=model.status,
            cancelled_reason=model.cancelled_reason,
            priority=model.priority,
            due=model.due,
            source=model.source,
            cycle_id=model.cycle_id,
            next_review_at=model.next_review_at,
            blocked_by_task_id=model.blocked_by_task_id,
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
        if "blocked_by_task_id" in patch_data:
            validator._validate_blocker(patch_data["blocked_by_task_id"], current_task_id=task.id)

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
        if action_type == "link_entities":
            self._rollback_link(result)
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

    def _rollback_link(self, result: dict) -> None:
        link_id = result.get("entity_id")
        if not isinstance(link_id, str) or not link_id:
            raise ValueError("CHANGE_ACTION_RESULT_MISSING_ENTITY_ID")
        link = self.db.get(Link, link_id)
        if link:
            self.db.delete(link)

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
        if action_type == "update_task":
            source = payload.get("source")
            return [str(source)] if source else []
        return []
