from __future__ import annotations

import re
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

    def upsert_journal_append(self, journal_date: str, append_text: str, source: str):
        return self._post(
            "/api/v1/journals/upsert-append",
            {"journal_date": journal_date, "append_text": append_text, "source": source},
        )

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

    def list_topics(self):
        return self._get("/api/v1/topics")

    def list_journals(self, **params):
        return self._get("/api/v1/journals", params=params)

    def get_journal(self, journal_date: str):
        return self._get(f"/api/v1/journals/{journal_date}")

    def get_context_bundle(self, **params):
        return self._get("/api/v1/context/bundle", params=params)

    def propose_record_todo(
        self,
        *,
        title: str,
        actor: dict[str, str],
        source: str,
        description: str = "",
        priority: Optional[str] = None,
        due: Optional[str] = None,
        topic_id: Optional[str] = None,
        task_type: str = "build",
        tool: str = "openclaw-skill",
    ):
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "status": "todo",
            "source": source,
            "task_type": task_type,
        }
        if priority:
            payload["priority"] = priority
        if due:
            payload["due"] = due
        if topic_id:
            payload["topic_id"] = topic_id
        else:
            payload["topic_id"] = self._default_topic_id()

        existing = self._find_active_task_by_title(title)
        if existing:
            action = {
                "type": "update_task",
                "payload": {
                    "task_id": existing["id"],
                    "description": description or existing.get("description", ""),
                    "priority": priority or existing.get("priority"),
                    "due": due or existing.get("due"),
                    "source": source,
                },
            }
        else:
            action = {"type": "create_task", "payload": payload}
        return self.propose_changes(actions=[action], actor=actor, tool=tool)

    def propose_append_journal(
        self,
        *,
        journal_date: str,
        append_text: str,
        source: str,
        actor: dict[str, str],
        tool: str = "openclaw-skill",
    ):
        action = {
            "type": "upsert_journal_append",
            "payload": {"journal_date": journal_date, "append_text": append_text, "source": source},
        }
        return self.propose_changes(actions=[action], actor=actor, tool=tool)

    def propose_upsert_knowledge(
        self,
        *,
        title: str,
        body_increment: str,
        source: str,
        actor: dict[str, str],
        topic_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        tool: str = "openclaw-skill",
    ):
        existing = self._find_active_note_by_title(title)
        if existing:
            action = {
                "type": "patch_note",
                "payload": {
                    "note_id": existing["id"],
                    "body_append": body_increment,
                    "source": source,
                },
            }
            if topic_id:
                action["payload"]["topic_id"] = topic_id
            if tags is not None:
                action["payload"]["tags"] = tags
        else:
            note_payload: dict[str, Any] = {
                "title": title,
                "body": body_increment,
                "sources": [{"type": "text", "value": source}],
                "tags": tags or [],
            }
            if topic_id:
                note_payload["topic_id"] = topic_id
            action = {"type": "append_note", "payload": note_payload}

        return self.propose_changes(actions=[action], actor=actor, tool=tool)

    def _default_topic_id(self) -> str:
        topics = self.list_topics()
        items = topics.get("items") or []
        for item in items:
            if item.get("id") == "top_fx_other":
                return "top_fx_other"
        if items:
            return str(items[0]["id"])
        raise RuntimeError("no active topics found")

    def _find_active_task_by_title(self, title: str) -> Optional[dict[str, Any]]:
        listed = self.list_tasks(page=1, page_size=100, q=title)
        target = self._norm_title(title)
        for item in listed.get("items", []):
            if item.get("status") in {"todo", "in_progress"} and self._norm_title(str(item.get("title", ""))) == target:
                return item
        return None

    def _find_active_note_by_title(self, title: str) -> Optional[dict[str, Any]]:
        listed = self.search_notes(page=1, page_size=100, q=title, status="active")
        target = self._norm_title(title)
        for item in listed.get("items", []):
            if self._norm_title(str(item.get("title", ""))) == target:
                return item
        return None

    def _norm_title(self, value: str) -> str:
        lowered = value.lower().strip()
        lowered = re.sub(r"[^0-9a-zA-Z\\u4e00-\\u9fff]+", " ", lowered)
        return re.sub(r"\\s+", " ", lowered).strip()
