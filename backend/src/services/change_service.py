from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.models import ChangeSet, Commit
from src.schemas import CommitIn, DryRunIn, UndoIn


class ChangeService:
    def __init__(self, db: Session):
        self.db = db

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
        self.db.commit()
        self.db.refresh(change_set)
        return change_set

    def commit(self, change_set_id: str, payload: CommitIn) -> tuple[Optional[Commit], Optional[ChangeSet]]:
        change_set = self.db.get(ChangeSet, change_set_id)
        if not change_set:
            return None, None

        change_set.status = "committed"
        change_set.committed_at = datetime.now(timezone.utc)

        commit = Commit(
            id=f"cmt_{uuid.uuid4().hex[:12]}",
            change_set_id=change_set_id,
            committed_by_type=payload.approved_by.type,
            committed_by_id=payload.approved_by.id,
            client_request_id=payload.client_request_id,
        )
        self.db.add(change_set)
        self.db.add(commit)
        self.db.commit()
        self.db.refresh(commit)
        self.db.refresh(change_set)
        return commit, change_set

    def undo_last(self, payload: UndoIn) -> Optional[tuple[str, str]]:
        last_commit = self.db.scalars(select(Commit).order_by(desc(Commit.committed_at)).limit(1)).first()
        if not last_commit:
            return None
        revert_commit_id = f"cmt_{uuid.uuid4().hex[:12]}"
        return last_commit.id, revert_commit_id

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
