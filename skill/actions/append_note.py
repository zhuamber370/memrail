from __future__ import annotations

from openclaw_skill import KmsClient


def run(base_url: str, api_key: str, title: str, body: str, source_text: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.append_note(
        title=title,
        body=body,
        sources=[{"type": "text", "value": source_text}],
    )
