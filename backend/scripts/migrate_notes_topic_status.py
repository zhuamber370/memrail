import json
import os
import uuid

import psycopg


def connect():
    return psycopg.connect(
        host=os.getenv("AFKMS_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("AFKMS_DB_PORT", "5432")),
        dbname=os.getenv("AFKMS_DB_NAME", "afkms"),
        user=os.getenv("AFKMS_DB_USER", "afkms"),
        password=os.getenv("AFKMS_DB_PASSWORD", "afkms"),
    )


def audit_event(cur, *, action: str, metadata: dict):
    cur.execute(
        """
        INSERT INTO audit_events (
          id,
          actor_type,
          actor_id,
          tool,
          action,
          target_type,
          target_id,
          source_refs_json,
          metadata_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
        """,
        (
            f"aud_{uuid.uuid4().hex[:12]}",
            "agent",
            "codex_local",
            "migration_script",
            action,
            "note_batch",
            "notes",
            json.dumps([]),
            json.dumps(metadata),
        ),
    )


def main():
    mapped_count = 0
    conflict_count = 0
    unclassified_count = 0
    archived_noise_count = 0

    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS topic_id VARCHAR(40)")
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS status VARCHAR(20)")
                cur.execute("UPDATE notes SET status = 'active' WHERE status IS NULL")

                cur.execute(
                    """
                    WITH note_task_links AS (
                      SELECT
                        CASE WHEN l.from_type = 'note' THEN l.from_id ELSE l.to_id END AS note_id,
                        CASE WHEN l.from_type = 'task' THEN l.from_id ELSE l.to_id END AS task_id
                      FROM links l
                      WHERE (l.from_type = 'note' AND l.to_type = 'task')
                         OR (l.from_type = 'task' AND l.to_type = 'note')
                    ),
                    note_topic_unique AS (
                      SELECT ntl.note_id, MIN(t.topic_id) AS topic_id
                      FROM note_task_links ntl
                      JOIN tasks t ON t.id = ntl.task_id
                      GROUP BY ntl.note_id
                      HAVING COUNT(DISTINCT t.topic_id) = 1
                    ),
                    updated AS (
                      UPDATE notes n
                      SET topic_id = ntu.topic_id,
                          updated_at = NOW()
                      FROM note_topic_unique ntu
                      WHERE n.id = ntu.note_id
                        AND n.topic_id IS NULL
                        AND n.status = 'active'
                      RETURNING n.id
                    )
                    SELECT COUNT(*) FROM updated
                    """
                )
                mapped_count = int(cur.fetchone()[0])

                cur.execute(
                    """
                    WITH note_task_links AS (
                      SELECT
                        CASE WHEN l.from_type = 'note' THEN l.from_id ELSE l.to_id END AS note_id,
                        CASE WHEN l.from_type = 'task' THEN l.from_id ELSE l.to_id END AS task_id
                      FROM links l
                      WHERE (l.from_type = 'note' AND l.to_type = 'task')
                         OR (l.from_type = 'task' AND l.to_type = 'note')
                    )
                    SELECT COUNT(*) FROM (
                      SELECT ntl.note_id
                      FROM note_task_links ntl
                      JOIN tasks t ON t.id = ntl.task_id
                      GROUP BY ntl.note_id
                      HAVING COUNT(DISTINCT t.topic_id) > 1
                    ) conflicts
                    """
                )
                conflict_count = int(cur.fetchone()[0])

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM notes
                    WHERE status = 'active'
                      AND topic_id IS NULL
                    """
                )
                unclassified_count = int(cur.fetchone()[0])

                cur.execute(
                    """
                    UPDATE notes
                    SET status = 'archived',
                        updated_at = NOW()
                    WHERE status <> 'archived'
                      AND BTRIM(title) IN ('N', 'n')
                      AND LENGTH(BTRIM(body)) <= 2
                    """
                )
                archived_noise_count = cur.rowcount or 0

                audit_event(
                    cur,
                    action="migration_backfill_note_topic",
                    metadata={
                        "mapped_count": mapped_count,
                        "conflict_count": conflict_count,
                        "unclassified_active_count": unclassified_count,
                    },
                )
                audit_event(
                    cur,
                    action="migration_archive_noise_notes",
                    metadata={"archived_noise_count": archived_noise_count},
                )
    finally:
        conn.close()

    print(f"mapped={mapped_count}")
    print(f"conflicts={conflict_count}")
    print(f"unclassified_active={unclassified_count}")
    print(f"archived_noise={archived_noise_count}")


if __name__ == "__main__":
    main()
