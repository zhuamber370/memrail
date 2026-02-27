> Documentation Status: Current
> Last synced: 2026-02-27

# OpenClaw x Memrail Setup Guide (workspace skill flow)

## Goal

Use Memrail as the governed persistence layer for OpenClaw:
- read/write tasks, journals, notes, knowledge, and route data through Memrail
- use proposal-first governance (`dry-run -> commit/reject`)
- keep rollback available (`undo_last_commit`)

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

1. Record a todo (proposal)
```text
Record todo:
Title=Ship API docs sync
Description=Align README and backend docs
Priority=P1
Due=2026-03-02
```

2. Append a journal entry (proposal)
```text
Append journal:
Date=2026-02-27
Content=Finished doc/runtime alignment and validated tests.
```

3. Upsert note-style knowledge (proposal)
```text
Record topic:
Title=Release checklist conventions
Body increment=Always run backend tests before merge.
Tags=release,quality
```

4. Create structured knowledge record via knowledge API (proposal)
```text
Create knowledge:
Title=Dry-run governance policy
Body=All agent writes must go through dry-run first.
Category=decision_record
```

5. Capture inbox item (proposal)
```text
Capture inbox:
Content=Evaluate MCP integration timeline next sprint.
```

6. Read context
```text
Get context:
Intent=planning
Window days=14
```

7. Governance actions
```text
Commit proposal change_set_id=<id>
Reject proposal change_set_id=<id>
Undo last commit reason=<reason>
```

## Uninstall skill

```bash
cd <repo_root>
bash scripts/uninstall_openclaw_kms_skill.sh
```

## Troubleshooting

1. On write failures, inspect dry-run output and API error codes first.
2. Use `reject_changes` for explicit user rejection.
3. Use `undo_last_commit` for rollback.
4. If data seems missing, verify the corresponding read endpoint in `docs/guides/agent-api-surface.md`.
