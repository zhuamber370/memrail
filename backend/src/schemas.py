from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["todo", "in_progress", "done", "cancelled"]
TaskPriority = Literal["P0", "P1", "P2", "P3"]
TaskView = Literal["today", "overdue", "this_week", "backlog", "blocked", "done"]
CycleStatus = Literal["planned", "active", "closed"]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    status: TaskStatus
    priority: Optional[TaskPriority] = None
    due: Optional[date] = None
    project: Optional[str] = Field(default=None, min_length=1, max_length=120)
    source: str = Field(min_length=1)
    cycle_id: Optional[str] = None
    next_review_at: Optional[datetime] = None
    blocked_by_task_id: Optional[str] = None


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due: Optional[date] = None
    project: Optional[str] = Field(default=None, min_length=1, max_length=120)
    source: Optional[str] = Field(default=None, min_length=1)
    cycle_id: Optional[str] = None
    next_review_at: Optional[datetime] = None
    blocked_by_task_id: Optional[str] = None
    archived_at: Optional[datetime] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: TaskStatus
    priority: Optional[TaskPriority]
    due: Optional[date]
    project: Optional[str]
    source: str
    cycle_id: Optional[str]
    next_review_at: Optional[datetime]
    blocked_by_task_id: Optional[str]
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TaskListOut(BaseModel):
    items: list[TaskOut]
    page: int
    page_size: int
    total: int


class TaskBatchUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_ids: list[str] = Field(min_length=1)
    patch: TaskPatch


class TaskBatchUpdateOut(BaseModel):
    updated: int
    failed: int
    failures: list[dict[str, str]]


class TaskViewsSummaryOut(BaseModel):
    today: int
    overdue: int
    this_week: int
    backlog: int
    blocked: int
    done: int


class CycleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    status: CycleStatus


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    start_date: date
    end_date: date
    status: CycleStatus
    created_at: datetime
    updated_at: datetime


class CycleListOut(BaseModel):
    items: list[CycleOut]


SourceType = Literal["text", "url", "doc_id", "message_id"]


class InboxCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)
    source: str = Field(min_length=8, pattern=r"^chat://.+")


class InboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    captured_at: datetime


class SourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: SourceType
    value: str = Field(min_length=1)


class NoteAppend(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    sources: list[SourceItem] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class NoteListOut(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int


class LinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_type: Literal["note", "task"]
    from_id: str = Field(min_length=1)
    to_type: Literal["note", "task"]
    to_id: str = Field(min_length=1)
    relation: str = Field(min_length=1)


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    from_type: str
    from_id: str
    to_type: str
    to_id: str
    relation: str


class ActorRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["agent", "user"]
    id: str = Field(min_length=1)


class ChangeActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["create_task", "append_note", "update_task", "link_entities"]
    payload: dict[str, Any]


class DryRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actions: list[ChangeActionIn] = Field(min_length=1)
    actor: ActorRef
    tool: str = Field(min_length=1)


class DryRunOut(BaseModel):
    change_set_id: str
    summary: dict[str, int]
    diff: list[str]
    diff_items: list[dict[str, Any]]
    status: Literal["proposed"]


class CommitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved_by: ActorRef
    client_request_id: Optional[str] = None


class CommitOut(BaseModel):
    commit_id: str
    change_set_id: str
    status: Literal["committed"]
    committed_at: datetime


class UndoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_by: ActorRef
    reason: str = Field(min_length=1)
    client_request_id: Optional[str] = None


class UndoOut(BaseModel):
    undone_commit_id: str
    revert_commit_id: str
    status: Literal["reverted"]
