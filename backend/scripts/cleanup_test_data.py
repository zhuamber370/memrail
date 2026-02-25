from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import and_, or_, select

# Make `src` importable when running `python3 scripts/cleanup_test_data.py`.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.config import settings
from src.db import build_engine, build_session_local
from src.models import (
    Idea,
    InboxItem,
    Journal,
    JournalItem,
    Link,
    NodeLog,
    Note,
    NoteSource,
    Route,
    RouteEdge,
    RouteNode,
    Task,
    Topic,
    TopicEntry,
)

NOTE_SOURCE_PATTERN = re.compile(r"^note_src_[0-9a-f]{10}$")
TOPIC_PATTERNS = [
    re.compile(r"^topic_[0-9a-f]{10}$"),
    re.compile(r"^topic_name_[0-9a-f]{10}$"),
    re.compile(r"^topic_default_name_[0-9a-f]{10}$"),
    re.compile(r"^dup_topic_[0-9a-f]{10}$"),
]


def _is_test_topic_name(name: str) -> bool:
    return any(pattern.fullmatch(name) for pattern in TOPIC_PATTERNS)


def _collect_test_note_ids(db) -> set[str]:
    rows = db.execute(
        select(NoteSource.note_id, NoteSource.source_value).where(
            or_(NoteSource.source_value.like("test://%"), NoteSource.source_value.like("note_src_%"))
        )
    ).all()
    note_ids: set[str] = set()
    for note_id, source_value in rows:
        if source_value.startswith("test://") or NOTE_SOURCE_PATTERN.fullmatch(source_value):
            note_ids.add(note_id)
    return note_ids


def _collect_cleanup_topic_ids(db) -> set[str]:
    topic_ids: set[str] = set()
    topics = list(db.scalars(select(Topic).where(Topic.id.not_like("top_fx_%"))))
    for topic in topics:
        if not _is_test_topic_name(topic.name):
            continue
        has_task = db.scalar(select(Task.id).where(Task.topic_id == topic.id).limit(1)) is not None
        has_entry = db.scalar(select(TopicEntry.id).where(TopicEntry.topic_id == topic.id).limit(1)) is not None
        has_journal_item = (
            db.scalar(select(JournalItem.id).where(JournalItem.topic_id == topic.id).limit(1)) is not None
        )
        if not has_task and not has_entry and not has_journal_item:
            topic_ids.add(topic.id)
    return topic_ids


def main():
    engine = build_engine(settings.database_url)
    session_local = build_session_local(engine)
    db = session_local()
    deleted_links = 0
    deleted_notes = 0
    deleted_tasks = 0
    deleted_topics = 0
    deleted_inbox = 0
    deleted_journals = 0
    deleted_node_logs = 0
    deleted_route_edges = 0
    deleted_route_nodes = 0
    deleted_routes = 0
    deleted_ideas = 0

    try:
        with db.begin():
            test_task_ids = set(db.scalars(select(Task.id).where(Task.source.like("test://%"))))
            test_note_ids = _collect_test_note_ids(db)
            test_route_ids = set(db.scalars(select(Route.id).where(Route.name.like("route_test_%"))))
            test_route_node_ids = set()
            if test_route_ids:
                test_route_node_ids = set(
                    db.scalars(select(RouteNode.id).where(RouteNode.route_id.in_(sorted(test_route_ids))))
                )

            link_filters = []
            if test_task_ids:
                ordered_task_ids = sorted(test_task_ids)
                link_filters.extend(
                    [
                        and_(Link.from_type == "task", Link.from_id.in_(ordered_task_ids)),
                        and_(Link.to_type == "task", Link.to_id.in_(ordered_task_ids)),
                    ]
                )
            if test_note_ids:
                ordered_note_ids = sorted(test_note_ids)
                link_filters.extend(
                    [
                        and_(Link.from_type == "note", Link.from_id.in_(ordered_note_ids)),
                        and_(Link.to_type == "note", Link.to_id.in_(ordered_note_ids)),
                    ]
                )
            if link_filters:
                deleted_links = db.query(Link).filter(or_(*link_filters)).delete(synchronize_session=False)

            if test_note_ids:
                deleted_notes = (
                    db.query(Note).filter(Note.id.in_(sorted(test_note_ids))).delete(synchronize_session=False)
                )

            if test_task_ids:
                deleted_tasks = (
                    db.query(Task).filter(Task.id.in_(sorted(test_task_ids))).delete(synchronize_session=False)
                )

            deleted_inbox = (
                db.query(InboxItem)
                .filter(or_(InboxItem.source.like("test://%"), InboxItem.source == "chat://demo"))
                .delete(synchronize_session=False)
            )

            deleted_journals = (
                db.query(Journal).filter(Journal.source.like("test://%")).delete(synchronize_session=False)
            )

            if test_route_node_ids:
                deleted_node_logs = (
                    db.query(NodeLog)
                    .filter(NodeLog.node_id.in_(sorted(test_route_node_ids)))
                    .delete(synchronize_session=False)
                )

            edge_filters = []
            if test_route_ids:
                edge_filters.append(RouteEdge.route_id.in_(sorted(test_route_ids)))
            if test_route_node_ids:
                ordered_node_ids = sorted(test_route_node_ids)
                edge_filters.extend(
                    [
                        RouteEdge.from_node_id.in_(ordered_node_ids),
                        RouteEdge.to_node_id.in_(ordered_node_ids),
                    ]
                )
            if edge_filters:
                deleted_route_edges = db.query(RouteEdge).filter(or_(*edge_filters)).delete(synchronize_session=False)

            if test_route_ids:
                deleted_route_nodes = (
                    db.query(RouteNode)
                    .filter(RouteNode.route_id.in_(sorted(test_route_ids)))
                    .delete(synchronize_session=False)
                )
                deleted_routes = (
                    db.query(Route).filter(Route.id.in_(sorted(test_route_ids))).delete(synchronize_session=False)
                )

            deleted_ideas = db.query(Idea).filter(Idea.source.like("test://%")).delete(synchronize_session=False)

            cleanup_topic_ids = _collect_cleanup_topic_ids(db)
            if cleanup_topic_ids:
                deleted_topics = (
                    db.query(Topic)
                    .filter(Topic.id.in_(sorted(cleanup_topic_ids)))
                    .delete(synchronize_session=False)
                )
    finally:
        db.close()

    print(f"deleted_links={deleted_links}")
    print(f"deleted_notes={deleted_notes}")
    print(f"deleted_tasks={deleted_tasks}")
    print(f"deleted_inbox={deleted_inbox}")
    print(f"deleted_journals={deleted_journals}")
    print(f"deleted_node_logs={deleted_node_logs}")
    print(f"deleted_route_edges={deleted_route_edges}")
    print(f"deleted_route_nodes={deleted_route_nodes}")
    print(f"deleted_routes={deleted_routes}")
    print(f"deleted_ideas={deleted_ideas}")
    print(f"deleted_topics={deleted_topics}")


if __name__ == "__main__":
    main()
