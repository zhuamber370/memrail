# OpenClaw x Memrail Setup Guide (v3, workspace skill flow)

## Goal

Use Memrail as the governed persistence layer for OpenClaw:
- write/read tasks, journals, and knowledge through Memrail
- avoid manual system-prompt paste and manual action wiring
- enforce proposal-first governance (`dry-run -> commit/reject`)

## Prerequisites

1. Start backend
```bash
cd <repo_root>/backend
python3 -m uvicorn src.app:app --reload --port 8000
```

2. Expose runtime env for OpenClaw
```bash
export KMS_BASE_URL="http://127.0.0.1:8000"
export KMS_API_KEY="<your_api_key>"
```

## Install workspace skill

```bash
cd <repo_root>
bash scripts/install_openclaw_kms_skill.sh
```

The installer auto-detects OpenClaw workspace from `~/.openclaw/openclaw.json` (`agents.defaults.workspace`) and installs to `<workspace>/skills/kms`.

Verify:

```bash
openclaw skills info kms --json
openclaw skills check --json
```

If `eligible=false`, check `KMS_BASE_URL` and `KMS_API_KEY`, then restart OpenClaw gateway.

## Natural-language usage examples

1. Record a todo
```text
Record todo:
Title=...
Description=...
Priority=P1
Due=2026-02-28
Category=top_fx_operations_delivery
```

2. Append a journal entry
```text
Append journal:
Date=2026-02-24
Content=...
```

3. Upsert knowledge
```text
Record topic:
Title=...
Body increment=...
Category=top_fx_product_strategy
Tags=tag1,tag2
```

4. Read context
```text
Get context:
Intent=planning
Window days=14
```

5. Governance actions
```text
Commit proposal change_set_id=<id>
Reject proposal change_set_id=<id>
Undo last commit reason=...
```

## Uninstall skill

```bash
cd <repo_root>
bash scripts/uninstall_openclaw_kms_skill.sh
```

## Troubleshooting

1. On write failures, inspect dry-run output and API error codes first.
2. Keep `source` stable and traceable to reduce noisy duplicates.
3. Use `undo_last_commit` for rollback.
4. On explicit user rejection, call `reject_changes` to delete the proposal.
