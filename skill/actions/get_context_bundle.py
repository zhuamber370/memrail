from __future__ import annotations

from typing import Optional

from openclaw_skill import KmsClient


def run(
    base_url: str,
    api_key: str,
    intent: str,
    window_days: int = 14,
    include_done: bool = False,
    topic_id: Optional[list[str]] = None,
):
    client = KmsClient(base_url=base_url, api_key=api_key)
    params: dict[str, object] = {
        "intent": intent,
        "window_days": window_days,
        "include_done": include_done,
    }
    if topic_id:
        params["topic_id"] = topic_id
    return client.get_context_bundle(**params)
