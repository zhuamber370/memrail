from __future__ import annotations

from openclaw_skill import KmsClient


def run(base_url: str, api_key: str, text: str, source: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.capture_inbox(text=text, source=source)
