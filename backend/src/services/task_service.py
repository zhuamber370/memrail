from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from src.models import Cycle, Task, TaskSource, Topic
from src.schemas import TopicCreate, TaskCreate, TaskPatch
from src.services.audit_service import log_audit_event

FIXED_TOPIC_ORDER = [
    "top_fx_product_strategy",
    "top_fx_engineering_arch",
    "top_fx_operations_delivery",
    "top_fx_growth_marketing",
    "top_fx_finance_legal",
    "top_fx_learning_research",
    "top_fx_other",
]


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: TaskCreate) -> Task:
        self._validate_topic(payload.topic_id)
        self._validate_blocker(payload.blocked_by_task_id)
        self._validate_cancel_reason_for_cancelled_status(payload.status, payload.cancelled_reason)
        task = Task(
            id=f"tsk_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            description=payload.description,
            acceptance_criteria=payload.acceptance_criteria,
            next_action=payload.next_action,
            task_type=payload.task_type,
            topic_id=payload.topic_id,
            status=payload.status,
            cancelled_reason=payload.cancelled_reason.strip() if payload.cancelled_reason else None,
            priority=payload.priority,
            due=payload.due,
            source=payload.source,
            cycle_id=payload.cycle_id,
            next_review_at=payload.next_review_at,
            blocked_by_task_id=payload.blocked_by_task_id,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self._append_task_source(task.id, source_kind="text", source_ref=payload.source)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_task",
            target_type="task",
            target_id=task.id,
            source_refs=[payload.source],
        )
        return task

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        archived: Optional[bool] = None,
        topic_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        blocked: Optional[bool] = None,
        stale_days: Optional[int] = None,
        due_before: Optional[date] = None,
        updated_before: Optional[datetime] = None,
        view: Optional[str] = None,
        q: Optional[str] = None,
    ) -> tuple[list[Task], int]:
        show_archived = archived is True
        archived_clause = Task.archived_at.is_not(None) if show_archived else Task.archived_at.is_(None)
        stmt = select(Task).where(archived_clause)
        count_stmt = select(func.count()).select_from(Task).where(archived_clause)
        now = datetime.now(timezone.utc)
        today = now.date()

        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
            count_stmt = count_stmt.where(Task.priority == priority)
        if topic_id:
            stmt = stmt.where(Task.topic_id == topic_id)
            count_stmt = count_stmt.where(Task.topic_id == topic_id)
        if cycle_id:
            stmt = stmt.where(Task.cycle_id == cycle_id)
            count_stmt = count_stmt.where(Task.cycle_id == cycle_id)
        if blocked is True:
            stmt = stmt.where(Task.blocked_by_task_id.is_not(None))
            count_stmt = count_stmt.where(Task.blocked_by_task_id.is_not(None))
        if blocked is False:
            stmt = stmt.where(Task.blocked_by_task_id.is_(None))
            count_stmt = count_stmt.where(Task.blocked_by_task_id.is_(None))
        if stale_days:
            stale_before = now - timedelta(days=stale_days)
            stmt = stmt.where(Task.updated_at <= stale_before)
            count_stmt = count_stmt.where(Task.updated_at <= stale_before)
        if due_before:
            stmt = stmt.where(Task.due <= due_before)
            count_stmt = count_stmt.where(Task.due <= due_before)
        if updated_before:
            stmt = stmt.where(Task.updated_at <= updated_before)
            count_stmt = count_stmt.where(Task.updated_at <= updated_before)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Task.title.ilike(like))
            count_stmt = count_stmt.where(Task.title.ilike(like))
        if view:
            clause = self._build_view_clause(view, today=today)
            if clause is not None:
                stmt = stmt.where(clause)
                count_stmt = count_stmt.where(clause)

        stmt = stmt.order_by(Task.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def patch(self, task_id: str, payload: TaskPatch) -> Optional[Task]:
        task = self.db.get(Task, task_id)
        if not task:
            return None
        patch_data = payload.model_dump(exclude_unset=True)
        if "cancelled_reason" in patch_data and patch_data["cancelled_reason"] is not None:
            trimmed = patch_data["cancelled_reason"].strip()
            patch_data["cancelled_reason"] = trimmed if trimmed else None
        if "blocked_by_task_id" in patch_data:
            self._validate_blocker(patch_data["blocked_by_task_id"], current_task_id=task.id)
        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            self._validate_topic(patch_data["topic_id"])
        if "status" in patch_data:
            self._validate_status_transition(task.status, patch_data["status"])
        self._validate_cancel_reason_patch(task=task, patch_data=patch_data)

        for key, value in patch_data.items():
            setattr(task, key, value)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        if "source" in patch_data and patch_data["source"]:
            self._append_task_source(task.id, source_kind="text", source_ref=patch_data["source"])
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="update_task",
            target_type="task",
            target_id=task.id,
            source_refs=[task.source],
        )
        return task

    def batch_update(self, task_ids: list[str], patch: TaskPatch) -> dict:
        updated = 0
        failures: list[dict[str, str]] = []
        for task_id in task_ids:
            try:
                task = self.patch(task_id, patch)
                if task is None:
                    failures.append({"task_id": task_id, "reason": "TASK_NOT_FOUND"})
                    continue
                updated += 1
            except ValueError as exc:
                failures.append({"task_id": task_id, "reason": str(exc)})
        return {"updated": updated, "failed": len(failures), "failures": failures}

    def reopen(self, task_id: str) -> Optional[Task]:
        task = self.db.get(Task, task_id)
        if not task:
            return None
        task.status = "todo"
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def archive_cancelled(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(Task).where(Task.status == "cancelled", Task.archived_at.is_(None))
        items = list(self.db.scalars(stmt))
        for task in items:
            task.archived_at = now
            self.db.add(task)
        self.db.commit()
        if items:
            log_audit_event(
                self.db,
                actor_type="user",
                actor_id="local",
                tool="api",
                action="archive_cancelled_tasks",
                target_type="task_batch",
                target_id=f"cancelled:{len(items)}",
                source_refs=["ui://tasks/archive-cancelled"],
            )
        return len(items)

    def archive_selected(self, task_ids: list[str]) -> int:
        now = datetime.now(timezone.utc)
        unique_ids = list(dict.fromkeys(task_ids))
        if not unique_ids:
            return 0
        stmt = select(Task).where(
            Task.id.in_(unique_ids),
            Task.status.in_(["done", "cancelled"]),
            Task.archived_at.is_(None),
        )
        items = list(self.db.scalars(stmt))
        for task in items:
            task.archived_at = now
            self.db.add(task)
        self.db.commit()
        if items:
            log_audit_event(
                self.db,
                actor_type="user",
                actor_id="local",
                tool="api",
                action="archive_selected_tasks",
                target_type="task_batch",
                target_id=f"selected:{len(items)}",
                source_refs=["ui://tasks/archive-selected"],
            )
        return len(items)

    def delete(self, task_id: str) -> bool:
        task = self.db.get(Task, task_id)
        if not task:
            return False
        source = task.source
        self.db.delete(task)
        self.db.commit()
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="delete_task",
            target_type="task",
            target_id=task_id,
            source_refs=[source] if source else [],
        )
        return True

    def views_summary(self) -> dict[str, int]:
        today = datetime.now(timezone.utc).date()
        views = ["today", "overdue", "this_week", "backlog", "blocked", "done"]
        summary: dict[str, int] = {}
        for view in views:
            clause = self._build_view_clause(view, today=today)
            count_stmt = select(func.count()).select_from(Task).where(Task.archived_at.is_(None))
            if clause is not None:
                count_stmt = count_stmt.where(clause)
            summary[view] = int(self.db.scalar(count_stmt) or 0)
        return summary

    def _validate_blocker(self, blocked_by_task_id: Optional[str], current_task_id: Optional[str] = None) -> None:
        if blocked_by_task_id is None:
            return
        if current_task_id and blocked_by_task_id == current_task_id:
            raise ValueError("TASK_BLOCKED_BY_SELF")
        blocker = self.db.get(Task, blocked_by_task_id)
        if blocker is None:
            raise ValueError("TASK_BLOCKED_BY_NOT_FOUND")

    def _validate_topic(self, topic_id: str) -> None:
        if self.db.get(Topic, topic_id) is None:
            raise ValueError("TOPIC_NOT_FOUND")

    def _append_task_source(
        self,
        task_id: str,
        *,
        source_kind: str,
        source_ref: str,
        excerpt: Optional[str] = None,
    ) -> None:
        source = TaskSource(
            id=f"tsrc_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            source_kind=source_kind,
            source_ref=source_ref,
            excerpt=excerpt,
        )
        self.db.add(source)
        self.db.commit()

    def _validate_status_transition(self, old_status: str, new_status: str) -> None:
        if old_status in {"done", "cancelled"} and new_status == "in_progress":
            raise ValueError("TASK_INVALID_STATUS_TRANSITION")

    def _validate_cancel_reason_for_cancelled_status(
        self,
        status: str,
        cancelled_reason: Optional[str],
    ) -> None:
        if status != "cancelled":
            return
        if not cancelled_reason or not cancelled_reason.strip():
            raise ValueError("TASK_CANCEL_REASON_REQUIRED")

    def _validate_cancel_reason_patch(self, *, task: Task, patch_data: dict) -> None:
        if "status" not in patch_data:
            return
        next_status = patch_data["status"]
        if next_status != "cancelled":
            return
        old_status = task.status
        if old_status == "cancelled":
            reason = patch_data.get("cancelled_reason", task.cancelled_reason)
            if reason and str(reason).strip():
                return
            raise ValueError("TASK_CANCEL_REASON_REQUIRED")
        reason = patch_data.get("cancelled_reason")
        if not reason or not str(reason).strip():
            raise ValueError("TASK_CANCEL_REASON_REQUIRED")

    def _build_view_clause(self, view: str, *, today: date):
        active = Task.status.notin_(["done", "cancelled"])
        if view == "today":
            return and_(Task.due == today, active)
        if view == "overdue":
            return and_(Task.due.is_not(None), Task.due < today, active)
        if view == "this_week":
            week_end = today + timedelta(days=6)
            return and_(Task.due.is_not(None), Task.due >= today, Task.due <= week_end, active)
        if view == "backlog":
            return and_(Task.status == "todo", Task.due.is_(None))
        if view == "blocked":
            return and_(Task.blocked_by_task_id.is_not(None), active)
        if view == "done":
            return Task.status == "done"
        return None


class CycleService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, start_date: date, end_date: date, status: str) -> Cycle:
        cycle = Cycle(
            id=f"cyc_{uuid.uuid4().hex[:12]}",
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def list(self) -> list[Cycle]:
        stmt = select(Cycle).order_by(Cycle.start_date.desc())
        return list(self.db.scalars(stmt))


class TopicService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: TopicCreate) -> Topic:
        raise ValueError("TOPIC_TAXONOMY_LOCKED")

    def list(self) -> list[Topic]:
        ordering = case(
            *[(Topic.id == topic_id, idx) for idx, topic_id in enumerate(FIXED_TOPIC_ORDER, start=1)],
            else_=999,
        )
        stmt = (
            select(Topic)
            .where(Topic.status == "active")
            .order_by(ordering, Topic.name_en.asc())
        )
        return list(self.db.scalars(stmt))
