# Agent-First KMS MVP 最终系统设计

> 日期：2026-02-21  
> 状态：Confirmed v0.2（Task 管理增强）  
> 适用范围：Cloud SaaS MVP（2-4 周）

## 0. 设计目标

构建一个 `Agent-First Personal OS`，以默认信息架构和写入治理机制解决个人信息管理熵增问题。  
用户与 Agent 共建：用户审阅与管理，Agent 持续维护。

已确认边界：

1. 不绑定 Markdown/Obsidian，系统独立可用。
2. 用户可直接在系统内增删改查。
3. Task 固定字段，MVP 不允许自定义字段。
4. Undo 仅支持最近一次批量提交。
5. Knowledge 必须有 source，允许文本来源。
6. 去重采用保守模式（仅提案，不自动合并）。
7. `priority` 固定 `P0/P1/P2/P3`。
8. Task 不包含 `project` 字段，避免孤立信息结构。
9. Inbox internal-only，仅接受 `chat://...` 来源。

## 0.1 技术架构（MVP 冻结）

1. 前端：`Next.js + TypeScript + Tailwind + TanStack Query`
2. 后端：`FastAPI + Pydantic + SQLAlchemy + Alembic`
3. 数据库：`PostgreSQL`（固定连接 `192.168.50.245:5432`）
4. 检索：`PostgreSQL Full-Text Search + pg_trgm`
5. 开发环境：本地运行（开发阶段不使用 Docker）

## 1. 前端页面设计

前置约束：UI 设计与实现必须使用 `frontend-design` skill。

### 1.1 全局布局

- 顶部：全局搜索、快速新建（Task/Knowledge）、审计入口
- 侧栏：`Tasks` / `Knowledge` / `Changes` / `Audit`
- 内容区：桌面端双栏（列表+详情），移动端单栏切换

### 1.2 页面定义

1. Tasks
- 预置视图：`Today` / `Overdue` / `This Week` / `Backlog` / `Blocked` / `Done`
- 列表字段：`title/status/priority/due/cycle/blocked_reason/updated_at`
- 交互：单条编辑、批量更新、状态推进、设置 review 时间、设置阻塞关系

2. Task Detail
- 展示：固定字段、来源、关联知识、审计摘要
- 动作：状态变更、依赖设置、加入/移出 cycle、设置 `next_review_at`

3. Knowledge
- 显示：`title/tags/source_count/updated_at`
- 支持新增、编辑、关联 Task、查看来源

4. Changes
- 展示 dry-run 变更提案与 diff 摘要
- 支持 `Commit / Reject`

5. Audit
- 展示写入事件流：who/when/tool/action/target/source
- 支持按对象回看历史

## 2. 状态流设计

### 2.1 写入治理状态机（强制）

`draft -> proposed -> approved -> reverted(optional)`

约束：

1. 无 `proposed` 不可 `commit`。
2. `undo-last` 必须生成新的审计事件。

### 2.2 Task 状态机

`todo -> in_progress -> done`，旁路 `cancelled`

约束：

1. 非法跳转（如 `done -> in_progress`）返回 `409`。
2. `done/cancelled -> todo` 通过 `reopen` 动作完成。
3. 仅固定字段可更新。

### 2.3 内部输入流

`chat_ingest -> internal_inbox -> structured_write`

约束：仅接受 user-agent 聊天来源（`chat://...`），不在 UI 暴露。

### 2.4 重复处理流（保守模式）

`detect_duplicate -> mark_candidate -> propose_merge -> human_decision`

约束：不自动合并，仅人工确认后执行。

## 3. 后端接口设计

基础路径：`/api/v1`  
鉴权：`Authorization: Bearer <API_KEY>`

### 3.1 Internal Ingestion

- `POST /inbox/captures`（internal-only）

### 3.2 Tasks

- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{task_id}`
- `POST /tasks/batch-update`
- `POST /tasks/{task_id}/reopen`
- `GET /tasks/views/summary`

### 3.3 Cycles

- `POST /cycles`
- `GET /cycles`

### 3.4 Knowledge

- `POST /notes/append`
- `GET /notes/search`
- `PATCH /notes/{note_id}`

### 3.5 Links

- `POST /links`
- `DELETE /links/{link_id}`

### 3.6 Governance

- `POST /changes/dry-run`
- `POST /changes/{change_set_id}/commit`
- `POST /commits/undo-last`

### 3.7 Audit

- `GET /audit/events`

接口约束：

1. `dry-run` 只产出提案，不落业务实体。
2. `commit` 需 `approved_by`。
3. `undo-last` 不接受历史 commit id。
4. Task 拒绝 schema 外字段。
5. Note 写入必须 `sources.length >= 1`。
6. 批量更新仅允许白名单字段。

## 4. 数据模型设计

### 4.1 主要表

1. `inbox_items`（internal-only）  
`id, content, source, status, captured_at, updated_at`

2. `tasks`  
`id, title, status, priority, due, source, cycle_id, next_review_at, blocked_by_task_id, archived_at, created_at, updated_at`

3. `cycles`  
`id, name, start_date, end_date, status, created_at, updated_at`

4. `notes`  
`id, title, body, created_at, updated_at`

5. `note_sources`  
`id, note_id, source_type, source_value`

6. `links`  
`id, from_type, from_id, to_type, to_id, relation, created_at`

7. `change_sets`  
`id, actor_type, actor_id, tool, status, summary_json, diff_json, created_at, committed_at`

8. `change_actions`  
`id, change_set_id, action_type, payload_json, apply_result_json`

9. `commits`  
`id, change_set_id, committed_by_type, committed_by_id, committed_at, client_request_id`

10. `audit_events`  
`id, occurred_at, actor_type, actor_id, tool, action, target_type, target_id, source_refs_json, before_hash, after_hash, metadata_json`

### 4.2 关系与索引

- `cycles 1:N tasks`
- `notes 1:N note_sources`
- `change_sets 1:N change_actions`
- `change_sets 1:1 commits`（MVP）

索引建议：

1. `tasks(status, priority, due, updated_at desc)`
2. `tasks(status, due)`
3. `tasks(cycle_id, status)`
4. `tasks(blocked_by_task_id) where blocked_by_task_id is not null`
5. `tasks(next_review_at) where next_review_at is not null`
6. `cycles(status, start_date, end_date)`

## 5. 错误处理、权限与安全

### 5.1 错误响应

```json
{
  "error": {
    "code": "TASK_INVALID_STATUS_TRANSITION",
    "message": "Cannot move task from done to in_progress directly.",
    "details": {"from": "done", "to": "in_progress"},
    "request_id": "req_xxx"
  }
}
```

错误码：

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`
- `403 FORBIDDEN`
- `404 TASK_NOT_FOUND|CYCLE_NOT_FOUND`
- `409 TASK_INVALID_STATUS_TRANSITION|CHANGESET_ALREADY_COMMITTED`
- `422 TASK_BLOCKED_BY_NOT_FOUND|TASK_BLOCKED_BY_SELF`
- `429 RATE_LIMITED`
- `500 INTERNAL_ERROR`

### 5.2 鉴权与安全边界

1. MVP 使用单用户 API Key。
2. 密钥仅允许环境变量或 1Password 注入。
3. 禁止在 AGENTS.md/代码/skill 中硬编码密钥。
4. 所有写操作入审计。
5. 批量写入必须经过 `dry-run -> commit`。
6. Inbox source 必须匹配 `chat://...`。

未来预留（非 MVP）：per-user token/OAuth 与资源级权限隔离。

## 6. 非目标（MVP）

1. 多人协同评论与 RBAC 全量实现。
2. 甘特图/资源排班。
3. 自定义字段系统。

## 7. 实现前检查清单

1. Task 固定字段与状态转移约束是否严格执行？
2. batch-update 是否仅白名单字段？
3. Undo 是否仅回滚最近一次提交？
4. Knowledge 是否保证写入必带 source？
5. 重复处理是否仍为“仅提案不自动合并”？
6. OpenClaw 写入是否统一走该系统入口？
