import os

import psycopg


def connect():
    return psycopg.connect(
        host=os.getenv("AFKMS_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("AFKMS_DB_PORT", "5432")),
        dbname=os.getenv("AFKMS_DB_NAME", "afkms"),
        user=os.getenv("AFKMS_DB_USER", "afkms"),
        password=os.getenv("AFKMS_DB_PASSWORD", "afkms"),
    )


def main():
    conn = connect()
    deleted_links = 0
    deleted_notes = 0
    deleted_tasks = 0
    deleted_topics = 0
    deleted_inbox = 0
    deleted_journals = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH test_tasks AS (
                  SELECT id FROM tasks WHERE source LIKE 'test://%'
                ),
                test_notes AS (
                  SELECT DISTINCT note_id
                  FROM note_sources
                  WHERE source_value LIKE 'test://%'
                     OR source_value ~ '^note_src_[0-9a-f]{10}$'
                )
                DELETE FROM links
                WHERE (from_type = 'task' AND from_id IN (SELECT id FROM test_tasks))
                   OR (to_type = 'task' AND to_id IN (SELECT id FROM test_tasks))
                   OR (from_type = 'note' AND from_id IN (SELECT note_id FROM test_notes))
                   OR (to_type = 'note' AND to_id IN (SELECT note_id FROM test_notes))
                """
            )
            deleted_links = cur.rowcount or 0

            cur.execute(
                """
                DELETE FROM notes
                WHERE id IN (
                  SELECT DISTINCT note_id
                  FROM note_sources
                  WHERE source_value LIKE 'test://%'
                     OR source_value ~ '^note_src_[0-9a-f]{10}$'
                )
                """
            )
            deleted_notes = cur.rowcount or 0

            cur.execute("DELETE FROM tasks WHERE source LIKE 'test://%'")
            deleted_tasks = cur.rowcount or 0

            cur.execute(
                """
                DELETE FROM inbox_items
                WHERE source LIKE 'test://%'
                   OR source = 'chat://demo'
                """
            )
            deleted_inbox = cur.rowcount or 0

            cur.execute("DELETE FROM journals WHERE source LIKE 'test://%'")
            deleted_journals = cur.rowcount or 0

            cur.execute(
                """
                DELETE FROM topics t
                WHERE t.id NOT LIKE 'top_fx_%'
                  AND (
                    t.name ~ '^topic_[0-9a-f]{10}$'
                    OR t.name ~ '^topic_name_[0-9a-f]{10}$'
                    OR t.name ~ '^topic_default_name_[0-9a-f]{10}$'
                    OR t.name ~ '^dup_topic_[0-9a-f]{10}$'
                  )
                  AND NOT EXISTS (SELECT 1 FROM tasks x WHERE x.topic_id = t.id)
                  AND NOT EXISTS (SELECT 1 FROM topic_entries e WHERE e.topic_id = t.id)
                  AND NOT EXISTS (SELECT 1 FROM journal_items j WHERE j.topic_id = t.id)
                """
            )
            deleted_topics = cur.rowcount or 0

    conn.close()
    print(f"deleted_links={deleted_links}")
    print(f"deleted_notes={deleted_notes}")
    print(f"deleted_tasks={deleted_tasks}")
    print(f"deleted_inbox={deleted_inbox}")
    print(f"deleted_journals={deleted_journals}")
    print(f"deleted_topics={deleted_topics}")


if __name__ == "__main__":
    main()
