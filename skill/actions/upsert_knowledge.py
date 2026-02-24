from __future__ import annotations

from typing import Optional

from openclaw_skill import KmsClient


def run(
    base_url: str,
    api_key: str,
    title: str,
    body_increment: str,
    source: str,
    topic_id: Optional[str] = None,
):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.propose_upsert_knowledge(
        title=title,
        body_increment=body_increment,
        source=source,
        topic_id=topic_id,
        actor={"type": "agent", "id": "openclaw"},
    )
