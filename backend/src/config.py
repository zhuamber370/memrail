from dataclasses import dataclass, field
import os
from pathlib import Path


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
    db_host: str = field(default_factory=lambda: os.getenv("AFKMS_DB_HOST", "127.0.0.1"))
    db_port: str = field(default_factory=lambda: os.getenv("AFKMS_DB_PORT", "5432"))
    db_name: str = field(default_factory=lambda: os.getenv("AFKMS_DB_NAME", "afkms"))
    db_user: str = field(default_factory=lambda: os.getenv("AFKMS_DB_USER", "afkms"))
    db_password: str = field(default_factory=lambda: os.getenv("AFKMS_DB_PASSWORD", "afkms"))

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
