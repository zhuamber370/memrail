from __future__ import annotations

from openclaw_skill import KmsClient


def run(base_url: str, api_key: str, journal_date: str, content: str, source: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.propose_append_journal(
        journal_date=journal_date,
        append_text=content,
        source=source,
        actor={"type": "agent", "id": "openclaw"},
    )
