from __future__ import annotations

from openclaw_skill import KmsClient


def propose_commit_undo(base_url: str, api_key: str):
    client = KmsClient(base_url=base_url, api_key=api_key)
    proposal = client.propose_record_todo(
        title="Ops review",
        description="Manual explicit todo from user command",
        priority="P2",
        source="chat://openclaw/demo/propose-commit-undo",
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
