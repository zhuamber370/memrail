from __future__ import annotations

from openclaw_skill import KmsClient


def propose_commit_undo(base_url: str, api_key: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    proposal = client.propose_changes(
        actions=[
            {
                "type": "create_task",
                "payload": {
                    "title": "Ops review",
                    "status": "todo",
                    "priority": "P2",
                    "source": "openclaw",
                },
            }
        ],
        actor={"type": "agent", "id": "openclaw"},
    )
    committed = client.commit_changes(
        change_set_id=proposal["change_set_id"],
        approved_by={"type": "user", "id": "usr_local"},
    )
    undone = client.undo_last_commit(
        requested_by={"type": "user", "id": "usr_local"},
        reason="demo undo",
    )
    return {"proposal": proposal, "committed": committed, "undone": undone}
