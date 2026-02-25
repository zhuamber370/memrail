#!/usr/bin/env python3
"""Idempotent PostgreSQL bootstrap for local Memrail setup.

This script creates or updates:
1) application role/user
2) application database
3) ownership/grants

It uses admin connection settings from AFKMS_PG_ADMIN_* env vars,
and app settings from AFKMS_DB_* env vars.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql


def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def getenv(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"missing required env: {name}")
    return value


def connect_admin() -> psycopg.Connection:
    host = getenv("AFKMS_PG_ADMIN_HOST", getenv("AFKMS_DB_HOST", "127.0.0.1"))
    port = int(getenv("AFKMS_PG_ADMIN_PORT", getenv("AFKMS_DB_PORT", "5432")))
    dbname = getenv("AFKMS_PG_ADMIN_DB", "postgres")
    user = getenv("AFKMS_PG_ADMIN_USER", "postgres")
    password = os.getenv("AFKMS_PG_ADMIN_PASSWORD", "")

    kwargs = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
    }
    if password:
        kwargs["password"] = password

    conn = psycopg.connect(**kwargs)
    conn.autocommit = True
    return conn


def ensure_role(cur: psycopg.Cursor, app_user: str, app_password: str) -> tuple[bool, bool]:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
    exists = cur.fetchone() is not None

    if not exists:
        cur.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(app_user)),
            (app_password,),
        )
        return True, True

    cur.execute(
        sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(app_user)),
        (app_password,),
    )
    return False, True


def ensure_database(cur: psycopg.Cursor, app_db: str, app_user: str) -> tuple[bool, bool]:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (app_db,))
    exists = cur.fetchone() is not None

    if not exists:
        cur.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}")
            .format(sql.Identifier(app_db), sql.Identifier(app_user))
        )
        created = True
    else:
        created = False

    cur.execute(
        sql.SQL("ALTER DATABASE {} OWNER TO {}")
        .format(sql.Identifier(app_db), sql.Identifier(app_user))
    )
    cur.execute(
        sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}")
        .format(sql.Identifier(app_db), sql.Identifier(app_user))
    )

    return created, True


def verify_app_connection(app_host: str, app_port: int, app_db: str, app_user: str, app_password: str) -> None:
    with psycopg.connect(
        host=app_host,
        port=app_port,
        dbname=app_db,
        user=app_user,
        password=app_password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database()")
            user, database = cur.fetchone()
            print(f"verify_user={user}")
            print(f"verify_database={database}")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    project_root = backend_dir.parent
    load_env_file(backend_dir / ".env")
    load_env_file(project_root / ".env")

    app_host = getenv("AFKMS_DB_HOST", "127.0.0.1")
    app_port = int(getenv("AFKMS_DB_PORT", "5432"))
    app_db = getenv("AFKMS_DB_NAME")
    app_user = getenv("AFKMS_DB_USER")
    app_password = getenv("AFKMS_DB_PASSWORD")

    if not app_password.strip():
        raise RuntimeError("AFKMS_DB_PASSWORD must not be empty")

    role_created = False
    db_created = False

    try:
        with connect_admin() as conn:
            with conn.cursor() as cur:
                role_created, _ = ensure_role(cur, app_user, app_password)
                db_created, _ = ensure_database(cur, app_db, app_user)
    except Exception as admin_exc:
        try:
            verify_app_connection(app_host, app_port, app_db, app_user, app_password)
            print("bootstrap_status=ok (admin bootstrap skipped, app connection already valid)")
            print("role_created=0")
            print("database_created=0")
            return 0
        except Exception:
            raise RuntimeError(
                "admin bootstrap failed and app connection is not valid. "
                "Set AFKMS_PG_ADMIN_* env vars for an admin account."
            ) from admin_exc

    verify_app_connection(app_host, app_port, app_db, app_user, app_password)

    print(f"role_created={int(role_created)}")
    print(f"database_created={int(db_created)}")
    print("bootstrap_status=ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"bootstrap_status=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
