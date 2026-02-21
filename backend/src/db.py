from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def build_engine(database_url: str):
    return create_engine(database_url, future=True)


def build_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(session_local) -> Generator:
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema(engine) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS cycles (
          id VARCHAR(40) PRIMARY KEY,
          name VARCHAR(120) NOT NULL,
          start_date DATE NOT NULL,
          end_date DATE NOT NULL,
          status VARCHAR(20) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS cycle_id VARCHAR(40)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS next_review_at TIMESTAMPTZ",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS blocked_by_task_id VARCHAR(40)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
