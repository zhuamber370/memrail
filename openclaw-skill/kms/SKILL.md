---
name: kms
version: 1.0.0
description: Memrail integration for governed read/write access (tasks, journals, notes, knowledge, routes).
metadata:
  openclaw:
    emoji: "🗂️"
    requires:
      env:
        - KMS_BASE_URL
        - KMS_API_KEY
---

# Memrail Skill

Use this skill when you need to read or write Memrail data.

## Governance Rules

1. Single source of truth
- Tasks, journals, notes, knowledge, and route execution data are read/written in Memrail only.

2. Explicit write trigger
- Write only when the user gives an explicit write command.

3. Dry-run first
- All `propose_*` actions go through `POST /api/v1/changes/dry-run`.
- Return proposal summary + `change_set_id` before any commit.

4. Commit only after confirmation
- Call `commit_changes` only after user confirmation.

5. Reject stale proposals
- If user rejects a proposal, call `reject_changes`.

6. Undo support
- Use `undo_last_commit` when user requests rollback.

7. Source traceability
- Include `source`/`source_ref` whenever the target action supports it.

8. Task topic safety
- For `propose_record_todo`, ensure `topic_id` is present (explicit or inferred/fallback).

## Read Actions

- `get_context_bundle`
- `list_tasks`
- `list_topics`
- `list_cycles`
- `list_ideas`
- `list_changes`
- `get_change`
- `list_audit_events`
- `list_task_views_summary`
- `list_note_topic_summary`
- `list_routes`
- `list_task_routes`
- `get_route_graph`
- `list_route_node_logs`
- `get_task_execution_snapshot` (includes current node + previous step)
- `search_notes`
- `list_journals`
- `get_journal`
- `list_journal_items`
- `list_task_sources`
- `list_note_sources`
- `list_links`
- `list_inbox`
- `get_inbox`
- `list_knowledge`
- `get_knowledge`
- `api_get` (generic GET for any `/api/v1/*` path using `path + params`)

## Write Actions

- `propose_record_todo`
- `propose_append_journal`
- `propose_upsert_knowledge`
- `propose_capture_inbox`
- `propose_create_idea`
- `propose_patch_idea`
- `propose_promote_idea`
- `propose_create_route`
- `propose_patch_route`
- `propose_create_route_node`
- `propose_patch_route_node`
- `propose_delete_route_node`
- `propose_create_route_edge`
- `propose_patch_route_edge`
- `propose_delete_route_edge`
- `propose_append_route_node_log`
- `propose_create_knowledge`
- `propose_patch_knowledge`
- `propose_archive_knowledge`
- `propose_delete_knowledge`
- `propose_create_link`
- `propose_delete_link`
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
