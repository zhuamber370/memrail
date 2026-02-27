from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    cycle_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("cycles.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="mechanism_spec")
    tags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class NoteSource(Base):
    __tablename__ = "note_sources"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    note_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_value: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    tags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class KnowledgeEvidence(Base):
    __tablename__ = "knowledge_evidences"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    item_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Link(Base):
    __tablename__ = "links"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    from_type: Mapped[str] = mapped_column(String(20), nullable=False)
    from_id: Mapped[str] = mapped_column(String(40), nullable=False)
    to_type: Mapped[str] = mapped_column(String(20), nullable=False)
    to_id: Mapped[str] = mapped_column(String(40), nullable=False)
    relation: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TaskSource(Base):
    __tablename__ = "task_sources"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChangeSet(Base):
    __tablename__ = "change_sets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False)
    tool: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diff_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ChangeAction(Base):
    __tablename__ = "change_actions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    change_set_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=False
    )
    action_index: Mapped[int] = mapped_column(nullable=False, default=0)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    apply_result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    change_set_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=False
    )
    committed_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
    committed_by_id: Mapped[str] = mapped_column(String(80), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    client_request_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False)
    tool: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(40), nullable=False)
    source_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    before_hash: Mapped[Optional[str]] = mapped_column(String(128))
    after_hash: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Cycle(Base):
    __tablename__ = "cycles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TopicAlias(Base):
    __tablename__ = "topic_aliases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    journal_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    digest: Mapped[str] = mapped_column(Text, nullable=False, default="")
    triage_status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class JournalItem(Base):
    __tablename__ = "journal_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    journal_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("journals.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    task_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    ignore_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TopicEntry(Base):
    __tablename__ = "topic_entries"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    topic_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    task_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="captured")
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    task_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")
    priority: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    parent_route_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RouteNode(Base):
    __tablename__ = "route_nodes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    route_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")
    parent_node_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("route_nodes.id", ondelete="SET NULL"), nullable=True
    )
    order_hint: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_type: Mapped[str] = mapped_column(String(20), nullable=False, default="human")
    assignee_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RouteEdge(Base):
    __tablename__ = "route_edges"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    route_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    from_node_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("route_nodes.id", ondelete="CASCADE"), nullable=False
    )
    to_node_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("route_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(20), nullable=False, default="refine")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NodeLog(Base):
    __tablename__ = "node_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("route_nodes.id", ondelete="CASCADE"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="human")
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False, default="local")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    log_type: Mapped[str] = mapped_column(String(20), nullable=False, default="note")
    source_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
