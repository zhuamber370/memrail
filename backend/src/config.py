from dataclasses import dataclass, field
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value for {name}: {raw!r}")


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Existing process env has higher priority.
        os.environ.setdefault(key, value)


# Load backend/.env and project-root/.env if present.
_backend_dir = Path(__file__).resolve().parent.parent
_project_root = _backend_dir.parent
_load_env_file(_backend_dir / ".env")
_load_env_file(_project_root / ".env")


@dataclass
class Settings:
    database_url_override: str = field(default_factory=lambda: os.getenv("AFKMS_DATABASE_URL", "").strip())
    db_backend: str = field(default_factory=lambda: os.getenv("AFKMS_DB_BACKEND", "sqlite").strip().lower())
    sqlite_path: str = field(default_factory=lambda: os.getenv("AFKMS_SQLITE_PATH", "data/afkms.sqlite3"))

    db_host: str = field(default_factory=lambda: os.getenv("AFKMS_DB_HOST", "127.0.0.1"))
    db_port: str = field(default_factory=lambda: os.getenv("AFKMS_DB_PORT", "5432"))
    db_name: str = field(default_factory=lambda: os.getenv("AFKMS_DB_NAME", "afkms"))
    db_user: str = field(default_factory=lambda: os.getenv("AFKMS_DB_USER", "afkms"))
    db_password: str = field(default_factory=lambda: os.getenv("AFKMS_DB_PASSWORD", "afkms"))
    require_auth: bool = field(default_factory=lambda: _env_bool("AFKMS_REQUIRE_AUTH", False))
    kms_api_key: str = field(default_factory=lambda: os.getenv("KMS_API_KEY", "").strip())

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        if self.db_backend in {"postgres", "postgresql"}:
            return (
                f"postgresql+psycopg://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        if self.db_backend == "sqlite":
            db_file = Path(self.sqlite_path).expanduser()
            if not db_file.is_absolute():
                db_file = (_project_root / db_file).resolve()
            db_file.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+pysqlite:///{db_file}"

        raise ValueError(
            "unsupported AFKMS_DB_BACKEND value: "
            f"{self.db_backend!r}; expected 'sqlite' or 'postgres'"
        )

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql+psycopg://")

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
