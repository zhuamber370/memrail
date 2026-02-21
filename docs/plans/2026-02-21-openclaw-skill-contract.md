# OpenClaw Skill 接口定义草案（MVP）

> 日期：2026-02-21  
> 依赖文档：`/Users/celastin/Desktop/projects/kms-for-agent/docs/plans/2026-02-21-agent-first-kms-prd-api.md`  
> 状态：Draft v0.2（Task 管理增强）

## 1. 目标

定义 OpenClaw 与 Agent-First KMS 的统一交互契约，确保：

- 所有任务/知识写入通过统一入口完成。
- 写入过程可治理、可审计、可回滚。
- Skill 层只暴露高层动作，不暴露低级数据库语义。

## 2. 运行前置条件

- `KMS_BASE_URL`
- `KMS_API_KEY`
- 请求头：`Authorization: Bearer ${KMS_API_KEY}`

禁止：在 AGENTS.md、skill 文件、代码中硬编码密钥。

## 3. 动作总览（MVP）

1. `capture_inbox(text, source)`
2. `create_task(title, status, priority, due, source, cycle_id, next_review_at, blocked_by_task_id)`
3. `append_note(title, body, sources, tags)`
4. `search_notes(query, tag, linked_task_id, page, page_size)`
5. `list_tasks(view, status, priority, cycle_id, blocked, stale_days, due_before, updated_before, query, page, page_size)`
6. `propose_changes(actions, actor, tool)`
7. `commit_changes(change_set_id, approved_by)`
8. `undo_last_commit(requested_by, reason)`

## 4. 动作映射

- `capture_inbox` -> `POST /api/v1/inbox/captures`（`source` 必须匹配 `chat://...`）
- `create_task` -> `POST /api/v1/tasks`
- `append_note` -> `POST /api/v1/notes/append`
- `search_notes` -> `GET /api/v1/notes/search`
- `list_tasks` -> `GET /api/v1/tasks`
- `propose_changes` -> `POST /api/v1/changes/dry-run`
- `commit_changes` -> `POST /api/v1/changes/{change_set_id}/commit`
- `undo_last_commit` -> `POST /api/v1/commits/undo-last`

## 5. 执行约束

1. 批量写入默认流程：`propose_changes -> 用户审阅 diff -> commit_changes`。
2. 允许直接写入：`capture_inbox/create_task/append_note`（仍需审计）。
3. Skill 不做自动 merge，仅回传 `duplicate_candidate` 与 `merge_proposal`。
4. `commit_changes/undo_last_commit` 建议传 `client_request_id` 做幂等。

## 6. 错误语义与重试策略

- `400/401/403/404/422`：不重试
- `409`：读取冲突信息后最多重试 1 次
- `429`：指数退避，最多 3 次
- `500`：指数退避，最多 2 次

## 7. 契约验收

- 动作和后端接口一一映射。
- 参数定义与 Task 增强字段一致（cycle/review/blocked）。
- 与 PRD 一致：Task 固定字段、Undo 最近一次、保守去重。
