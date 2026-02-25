---
name: kms
version: 1.0.0
description: Memrail integration for tasks, journals, and knowledge with dry-run governance by default.
metadata:
  openclaw:
    emoji: "🗂️"
    requires:
      env:
        - KMS_BASE_URL
        - KMS_API_KEY
---

# Memrail Skill

Use this skill when you need to read or write Memrail data (tasks, journals, knowledge).

## Governance Rules

1. Single source of truth:
- Tasks, journals, and knowledge are read/written in Memrail only.

2. Explicit write trigger:
- Write only when the user gives an explicit write command.

3. Task classification is mandatory:
- Every `propose_record_todo` must include `topic_id`.
- If user does not provide topic, classify by task text/title keywords.
- If uncertain, fallback to `top_fx_other`.
- Never submit `create_task` proposal without `topic_id`.

4. Dry-run first:
- Always call proposal actions first:
  - `propose_record_todo`
  - `propose_append_journal`
  - `propose_upsert_knowledge`
- Return proposal summary + `change_set_id`.

5. Commit only after confirmation:
- Call `commit_changes` only after user confirmation.
- If user rejects a proposal, call `reject_changes` to delete it.

6. Undo support:
- Use `undo_last_commit` if user asks rollback.

7. Source and audit:
- Every write proposal must include `source`, recommended format:
  - `chat://openclaw/{thread_id}/{message_range}`

## Read Actions

- `get_context_bundle`
- `list_tasks`
- `search_notes`
- `list_journals`
- `get_journal`

## Write Actions

- `propose_record_todo`
- `propose_append_journal`
- `propose_upsert_knowledge`
- `commit_changes`
- `reject_changes`
- `undo_last_commit`

## Environment

Set before starting OpenClaw:

```bash
export KMS_BASE_URL="http://127.0.0.1:8000"
export KMS_API_KEY="your_api_key"
```

Optional:

```bash
export KMS_ACTOR_ID="openclaw"
```
