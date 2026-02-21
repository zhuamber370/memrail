from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.models import Cycle, Task
from src.schemas import TaskCreate, TaskPatch
from src.services.audit_service import log_audit_event


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: TaskCreate) -> Task:
        self._validate_blocker(payload.blocked_by_task_id)
        task = Task(
            id=f"tsk_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            status=payload.status,
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
        cycle_id: Optional[str] = None,
        blocked: Optional[bool] = None,
        stale_days: Optional[int] = None,
        due_before: Optional[date] = None,
        updated_before: Optional[datetime] = None,
        view: Optional[str] = None,
        q: Optional[str] = None,
    ) -> tuple[list[Task], int]:
        stmt = select(Task)
        count_stmt = select(func.count()).select_from(Task)
        now = datetime.now(timezone.utc)
        today = now.date()

        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
            count_stmt = count_stmt.where(Task.priority == priority)
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
        if "blocked_by_task_id" in patch_data:
            self._validate_blocker(patch_data["blocked_by_task_id"], current_task_id=task.id)
        if "status" in patch_data:
            self._validate_status_transition(task.status, patch_data["status"])

        for key, value in patch_data.items():
            setattr(task, key, value)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
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
            count_stmt = select(func.count()).select_from(Task)
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

    def _validate_status_transition(self, old_status: str, new_status: str) -> None:
        if old_status in {"done", "cancelled"} and new_status == "in_progress":
            raise ValueError("TASK_INVALID_STATUS_TRANSITION")

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
