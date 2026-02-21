from __future__ import annotations

from openclaw_skill import KmsClient


def run(base_url: str, api_key: str, title: str, source: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.create_task(title=title, status="todo", priority="P2", source=source)
