from __future__ import annotations

from openclaw_skill import KmsClient


def run(
    base_url: str,
    api_key: str,
    task_id: str,
    include_all_routes: bool = True,
    include_logs: bool = False,
    page_size: int = 100,
):
    client = KmsClient(base_url=base_url, api_key=api_key)
    return client.get_task_execution_snapshot(
        task_id=task_id,
        include_all_routes=include_all_routes,
        include_logs=include_logs,
        page_size=page_size,
    )
