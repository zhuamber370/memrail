from __future__ import annotations

from openclaw_skill import KmsClient


def run(base_url: str, api_key: str, title: str, body: str, source_text: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.propose_upsert_knowledge(
        title=title,
        body_increment=body,
        source=source_text,
        actor={"type": "agent", "id": "openclaw"},
    )
