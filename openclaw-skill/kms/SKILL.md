---
name: kms
version: 1.0.0
description: MemLineage integration for governed read/write access (tasks, journals, notes, knowledge, routes).
metadata:
  openclaw:
    emoji: "🗂️"
    requires:
      env:
        - KMS_BASE_URL
        - KMS_API_KEY
---

# MemLineage Skill

Use this skill when you need to read or write MemLineage data.

## Governance Rules

1. Single source of truth
- Tasks, journals, notes, knowledge, and route execution data are read/written in MemLineage only.

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

## Natural-Language Routing (MUST)

1. User should not need API names
- Interpret intent from natural language and choose actions automatically.
- Do not ask user to specify endpoint/action unless disambiguation is strictly required.

2. Task execution / DAG questions (highest priority)
- If user asks about "当前节点 / DAG / 节点状态 / 分支关系 / 前后置 / 执行进度", use:
  1) `get_task_execution_snapshot` first
  2) then `get_route_graph` / `list_route_node_logs` only when extra detail is needed
- Do not use `get_context_bundle` as the primary source for DAG answers.

3. Resolve task target automatically
- If user does not provide `task_id`, resolve via natural-language task query/title.
- If multiple tasks match and cannot be safely resolved, return candidates and ask for disambiguation.

4. Action priority
- Prefer dedicated read actions over generic `api_get`.
- `api_get` is last-resort fallback for uncovered read paths only.

5. Read-first safety
- For information requests, perform read actions only.
- Never trigger `propose_*` / commit / reject / undo unless user explicitly asks to write.

## Response Style (MUST)

1. Natural-language first
- Explain findings in business/task language, not database language.
- Lead with the direct answer, then give key evidence.

2. Hide technical internals by default
- Do not mention API paths, action names, table/field names, or SQL-like wording unless user explicitly asks.
- Do not dump raw JSON unless user explicitly asks for raw output.

3. Translate system terms into user language
- Convert status/enums to natural phrasing (e.g. `execute` -> "执行中", `waiting` -> "等待中", `done` -> "已完成").
- Prefer "当前在做什么/下一步是什么/有什么阻塞" over raw identifiers.

4. Structured but human
- For task execution answers, use this order:
  1) 当前进展（当前节点 + 状态）
  2) 关键路径（前置/后置关系）
  3) 风险或建议（如有）
- Keep IDs and low-level metadata in a separate "如需我可展开" part.

5. Ambiguity handling
- If task/route target is ambiguous, ask one concise disambiguation question with top candidates.
- Once clarified, continue with a natural-language summary.

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
- `api_get` (fallback generic GET for uncovered `/api/v1/*` paths only)

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
