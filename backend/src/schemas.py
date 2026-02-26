from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["todo", "in_progress", "done", "cancelled"]
TaskPriority = Literal["P0", "P1", "P2", "P3"]
TaskView = Literal["today", "overdue", "this_week", "backlog", "blocked", "done"]
CycleStatus = Literal["planned", "active", "closed"]
TopicKind = Literal["domain", "project", "playbook", "decision", "issue"]
TopicStatus = Literal["active", "watch", "archived"]
NoteStatus = Literal["active", "archived"]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    acceptance_criteria: str = ""
    topic_id: str = Field(min_length=1)
    status: TaskStatus
    cancelled_reason: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due: Optional[date] = None
    source: str = Field(min_length=1)
    cycle_id: Optional[str] = None


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    topic_id: Optional[str] = Field(default=None, min_length=1)
    status: Optional[TaskStatus] = None
    cancelled_reason: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due: Optional[date] = None
    source: Optional[str] = Field(default=None, min_length=1)
    cycle_id: Optional[str] = None
    archived_at: Optional[datetime] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    acceptance_criteria: str
    topic_id: str
    status: TaskStatus
    cancelled_reason: Optional[str]
    priority: Optional[TaskPriority]
    due: Optional[date]
    source: str
    cycle_id: Optional[str]
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


class TaskArchiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_ids: list[str] = Field(min_length=1)


class TaskArchiveOut(BaseModel):
    archived: int


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


class TopicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    name_en: Optional[str] = Field(default=None, min_length=1, max_length=120)
    name_zh: Optional[str] = Field(default=None, min_length=1, max_length=120)
    kind: TopicKind
    status: TopicStatus = "active"
    summary: str = ""


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_en: str
    name_zh: str
    kind: TopicKind
    status: TopicStatus
    summary: str
    created_at: datetime
    updated_at: datetime


class TopicListOut(BaseModel):
    items: list[TopicOut]


class JournalUpsertAppendIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journal_date: date
    append_text: str = Field(min_length=1)
    source: str = Field(min_length=1)


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    journal_date: date
    raw_content: str
    digest: str
    triage_status: str
    source: str
    created_at: datetime
    updated_at: datetime


class JournalListOut(BaseModel):
    items: list[JournalOut]
    page: int
    page_size: int
    total: int


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
    topic_id: Optional[str] = Field(default=None, min_length=1)
    sources: list[SourceItem] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    topic_id: Optional[str]
    status: NoteStatus
    created_at: datetime
    updated_at: datetime


class NotePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    body: Optional[str] = Field(default=None, min_length=1)
    topic_id: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[list[str]] = None
    status: Optional[NoteStatus] = None


class NoteListOut(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int


class NoteBatchClassifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_ids: list[str] = Field(min_length=1)
    topic_id: str = Field(min_length=1)


class NoteBatchClassifyOut(BaseModel):
    updated: int
    failed: int
    failures: list[dict[str, str]]


class NoteTopicSummaryItem(BaseModel):
    topic_id: Optional[str]
    topic_name: str
    count: int


class NoteTopicSummaryOut(BaseModel):
    items: list[NoteTopicSummaryItem]


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
    type: Literal[
        "create_task",
        "append_note",
        "update_task",
        "patch_note",
        "upsert_journal_append",
        "link_entities",
    ]
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


class RejectOut(BaseModel):
    change_set_id: str
    status: Literal["rejected"]


class UndoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_by: ActorRef
    reason: str = Field(min_length=1)
    client_request_id: Optional[str] = None


class UndoOut(BaseModel):
    undone_commit_id: str
    revert_commit_id: str
    status: Literal["reverted"]


class ChangeActionOut(BaseModel):
    action_id: str
    action_index: int
    action_type: str
    payload: dict[str, Any]
    apply_result: Optional[dict[str, Any]] = None


class ChangeSetListItemOut(BaseModel):
    change_set_id: str
    status: str
    actor: dict[str, str]
    tool: str
    summary: dict[str, Any]
    actions_count: int
    created_at: datetime
    committed_at: Optional[datetime]


class ChangeSetListOut(BaseModel):
    items: list[ChangeSetListItemOut]
    page: int
    page_size: int
    total: int


class ChangeSetDetailOut(BaseModel):
    change_set_id: str
    status: str
    actor: dict[str, str]
    tool: str
    summary: dict[str, Any]
    diff_items: list[dict[str, Any]]
    created_at: datetime
    committed_at: Optional[datetime]
    actions: list[ChangeActionOut]


class ContextBundleOut(BaseModel):
    intent: str
    window_days: int
    filters: dict[str, Any]
    summary: dict[str, int]
    tasks: list[dict[str, Any]]
    notes: list[dict[str, Any]]
    journals: list[dict[str, Any]]


IdeaStatus = Literal["captured", "triage", "discovery", "ready", "rejected"]
RouteStatus = Literal["candidate", "active", "parked", "completed", "cancelled"]
RouteNodeType = Literal["start", "goal", "idea"]
RouteNodeStatus = Literal["waiting", "execute", "done"]
RouteAssigneeType = Literal["human", "agent"]
RouteEdgeRelation = Literal["refine", "initiate", "handoff"]
NodeLogType = Literal["note", "evidence", "decision", "summary"]


class IdeaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    problem: str = ""
    hypothesis: str = ""
    status: IdeaStatus = "captured"
    topic_id: Optional[str] = Field(default=None, min_length=1)
    source: str = Field(min_length=1)


class IdeaPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    problem: Optional[str] = None
    hypothesis: Optional[str] = None
    status: Optional[IdeaStatus] = None
    topic_id: Optional[str] = Field(default=None, min_length=1)
    source: Optional[str] = Field(default=None, min_length=1)


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: Optional[str]
    title: str
    problem: str
    hypothesis: str
    status: IdeaStatus
    topic_id: Optional[str]
    source: str
    created_at: datetime
    updated_at: datetime


class IdeaListOut(BaseModel):
    items: list[IdeaOut]
    page: int
    page_size: int
    total: int


class RouteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=160)
    goal: str = ""
    status: RouteStatus = "candidate"
    priority: Optional[TaskPriority] = None
    owner: Optional[str] = None
    parent_route_id: Optional[str] = Field(default=None, min_length=1)


class RoutePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    goal: Optional[str] = None
    status: Optional[RouteStatus] = None
    priority: Optional[TaskPriority] = None
    owner: Optional[str] = None
    parent_route_id: Optional[str] = Field(default=None, min_length=1)


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: Optional[str]
    name: str
    goal: str
    status: RouteStatus
    priority: Optional[TaskPriority]
    owner: Optional[str]
    parent_route_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class RouteListOut(BaseModel):
    items: list[RouteOut]
    page: int
    page_size: int
    total: int


class RouteNodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_type: RouteNodeType
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: RouteNodeStatus = "waiting"
    parent_node_id: Optional[str] = Field(default=None, min_length=1)
    order_hint: int = 0
    assignee_type: RouteAssigneeType = "human"
    assignee_id: Optional[str] = None


class RouteNodePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_type: Optional[RouteNodeType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[RouteNodeStatus] = None
    parent_node_id: Optional[str] = Field(default=None, min_length=1)
    order_hint: Optional[int] = None
    assignee_type: Optional[RouteAssigneeType] = None
    assignee_id: Optional[str] = None


class RouteNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    route_id: str
    node_type: RouteNodeType
    title: str
    description: str
    status: RouteNodeStatus
    parent_node_id: Optional[str]
    order_hint: int
    assignee_type: RouteAssigneeType
    assignee_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class RouteEdgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_node_id: str = Field(min_length=1)
    to_node_id: str = Field(min_length=1)
    relation: RouteEdgeRelation = "refine"


class RouteEdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    route_id: str
    from_node_id: str
    to_node_id: str
    relation: RouteEdgeRelation
    created_at: datetime


class RouteGraphOut(BaseModel):
    route_id: str
    nodes: list[RouteNodeOut]
    edges: list[RouteEdgeOut]


class NodeLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)
    actor_type: RouteAssigneeType = "human"
    actor_id: str = Field(default="local", min_length=1)
    log_type: NodeLogType = "note"
    source_ref: Optional[str] = None


class NodeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    node_id: str
    actor_type: RouteAssigneeType
    actor_id: str
    content: str
    log_type: NodeLogType
    source_ref: Optional[str]
    created_at: datetime


class NodeLogListOut(BaseModel):
    items: list[NodeLogOut]


class IdeaPromoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route_id: str = Field(min_length=1)
    node_type: Literal["goal", "idea"] = "idea"
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
