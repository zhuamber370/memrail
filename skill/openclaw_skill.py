from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass
class KmsClient:
    base_url: str
    api_key: str
    timeout_sec: float = 15.0

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any], retries_429: int = 3, retries_500: int = 2):
        last_err: Optional[Exception] = None
        for attempt in range(max(retries_429, retries_500) + 1):
            try:
                resp = httpx.post(
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout_sec,
                )
                if resp.status_code in (429, 500):
                    limit = retries_429 if resp.status_code == 429 else retries_500
                    if attempt < limit:
                        time.sleep(0.2 * (2**attempt))
                        continue
                if 400 <= resp.status_code < 500 and resp.status_code not in (409, 429):
                    raise RuntimeError(f"{resp.status_code}: {resp.text}")
                if resp.status_code == 409 and attempt < 1:
                    time.sleep(0.1)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # pragma: no cover - thin wrapper
                last_err = exc
        raise RuntimeError(f"request failed after retries: {last_err}")

    def _get(self, path: str, params: Optional[dict[str, Any]] = None):
        resp = httpx.get(
            f"{self.base_url}{path}", headers=self._headers(), params=params or {}, timeout=self.timeout_sec
        )
        resp.raise_for_status()
        return resp.json()

    def capture_inbox(self, text: str, source: str):
        return self._post("/api/v1/inbox/captures", {"content": text, "source": source})

    def create_task(self, **payload):
        return self._post("/api/v1/tasks", payload)

    def append_note(self, title: str, body: str, sources: list[dict[str, str]], tags: Optional[list[str]] = None):
        return self._post(
            "/api/v1/notes/append",
            {"title": title, "body": body, "sources": sources, "tags": tags or []},
        )

    def propose_changes(self, actions: list[dict[str, Any]], actor: dict[str, str], tool: str = "openclaw-skill"):
        return self._post("/api/v1/changes/dry-run", {"actions": actions, "actor": actor, "tool": tool})

    def commit_changes(self, change_set_id: str, approved_by: dict[str, str], client_request_id: Optional[str] = None):
        payload: dict[str, Any] = {"approved_by": approved_by}
        if client_request_id:
            payload["client_request_id"] = client_request_id
        return self._post(f"/api/v1/changes/{change_set_id}/commit", payload)

    def undo_last_commit(self, requested_by: dict[str, str], reason: str, client_request_id: Optional[str] = None):
        payload: dict[str, Any] = {"requested_by": requested_by, "reason": reason}
        if client_request_id:
            payload["client_request_id"] = client_request_id
        return self._post("/api/v1/commits/undo-last", payload)

    def search_notes(self, **params):
        return self._get("/api/v1/notes/search", params=params)

    def list_tasks(self, **params):
        return self._get("/api/v1/tasks", params=params)
