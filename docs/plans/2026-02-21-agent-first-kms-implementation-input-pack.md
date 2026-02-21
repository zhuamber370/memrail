# Agent-First KMS 实现输入包（MVP）

> 日期：2026-02-21  
> 状态：Ready for Implementation v0.2（Task 管理增强）  
> 汇总来源：  
> `/Users/celastin/Desktop/projects/kms-for-agent/docs/plans/2026-02-21-agent-first-kms-prd-api.md`  
> `/Users/celastin/Desktop/projects/kms-for-agent/docs/plans/2026-02-21-openclaw-skill-contract.md`

## 1. 一句话定义

`Agent-First Personal OS (Cloud SaaS)`：内置默认 IA 与写入治理，支持用户和 Agent 共建，目标是“可复用的信息管理方式”，而非用户自行设计结构。

## 2. 已确认边界（冻结）

1. 产品不绑定 Markdown/Obsidian，可独立使用。
2. 用户可直接在系统内做完整增删改查。
3. Task 固定字段，MVP 不允许自定义字段。
4. Knowledge 必须有 source，允许文本来源。
5. Undo 仅支持“最近一次批量提交”。
6. 去重/合并采用保守模式：只提案，不自动合并。
7. `priority` 固定为 `P0|P1|P2|P3`。
8. `project` 在 MVP 保持字符串宽类型。
9. Inbox internal-only，source 仅允许 `chat://...`。

## 3. 非目标（MVP 不做）

1. 完整多租户与 RBAC。
2. 任意历史回滚。
3. Obsidian 双向实时同步。
4. 甘特图/资源排班/高级报表中心。
5. 自定义字段与工作流编辑器。

## 4. 技术架构与环境约束

1. 前端：`Next.js + TypeScript + Tailwind + TanStack Query`
2. 后端：`FastAPI + Pydantic + SQLAlchemy + Alembic`
3. 数据库：`PostgreSQL`，连接 `192.168.50.245:5432`
4. 检索：`PostgreSQL Full-Text Search + pg_trgm`
5. 开发阶段：本地运行，不使用 Docker

环境变量（凭据不写入仓库）：

- `AFKMS_DB_HOST=192.168.50.245`
- `AFKMS_DB_PORT=5432`
- `AFKMS_DB_NAME`（本地注入）
- `AFKMS_DB_USER`（本地注入）
- `AFKMS_DB_PASSWORD`（本地注入）

## 5. 任务域模型（增强）

### 5.1 Task 字段

`id, title, status, priority, due, project, source, cycle_id, next_review_at, blocked_by_task_id, archived_at, created_at, updated_at`

### 5.2 Task 视图

`today | overdue | this_week | backlog | blocked | done`

### 5.3 Task 状态机

- 主链路：`todo -> in_progress -> done`
- 旁路：`cancelled`
- 恢复：`done/cancelled -> todo` 通过 `reopen` 动作

### 5.4 Cycle 字段

`id, name, start_date, end_date, status(planned|active|closed), created_at, updated_at`

## 6. API 契约总览（实现最小集）

基础路径：`/api/v1`  
鉴权：`Authorization: Bearer <API_KEY>`

1. Task
- `POST /tasks`
- `GET /tasks`
- `PATCH /tasks/{task_id}`
- `POST /tasks/batch-update`
- `POST /tasks/{task_id}/reopen`
- `GET /tasks/views/summary`

2. Cycle
- `POST /cycles`
- `GET /cycles`

3. Internal Ingestion
- `POST /inbox/captures`（internal-only）

4. Knowledge
- `POST /notes/append`
- `GET /notes/search`

5. Link
- `POST /links`

6. Governance
- `POST /changes/dry-run`
- `POST /changes/{change_set_id}/commit`
- `POST /commits/undo-last`
- `GET /audit/events`

## 7. 错误码约束

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`
- `403 FORBIDDEN`
- `404 TASK_NOT_FOUND|CYCLE_NOT_FOUND`
- `409 TASK_INVALID_STATUS_TRANSITION|CHANGESET_ALREADY_COMMITTED`
- `422 TASK_BLOCKED_BY_NOT_FOUND|TASK_BLOCKED_BY_SELF`
- `429 RATE_LIMITED`
- `500 INTERNAL_ERROR`

## 8. OpenClaw Skill 契约总览

动作：

1. `capture_inbox(text, source)`（internal-only）
2. `create_task(title, status, priority, due, project, source, cycle_id, next_review_at, blocked_by_task_id)`
3. `append_note(title, body, sources, tags)`
4. `search_notes(query, tag, linked_task_id, page, page_size)`
5. `list_tasks(view, status, priority, project, cycle_id, blocked, stale_days, due_before, updated_before, query, page, page_size)`
6. `propose_changes(actions, actor, tool)`
7. `commit_changes(change_set_id, approved_by)`
8. `undo_last_commit(requested_by, reason)`

执行规则：

- 批量写入默认必须 `propose -> commit`。
- 允许直接写入：`capture_inbox/create_task/append_note`（仍需审计）。
- Skill 不做自动合并决策。

## 9. 前端实现约束

- 所有前端 UI 设计与实现任务必须先使用 `frontend-design` skill。
- 必须支持桌面/移动双端与键盘可访问。
- Inbox 不作为用户可见页面。

## 10. MVP 验收清单（执行版）

1. 任意批量写入支持 dry-run 并返回可读 diff。
2. commit 后可 undo 最近一次提交并生成审计记录。
3. Task 非固定字段写入被拒绝。
4. Task 非法状态跳转返回 `409`。
5. Task 预置视图和 batch-update 在 UI/API 可用。
6. Knowledge 未提供 source 时写入失败。
7. 重复内容仅生成提案，不发生自动合并。
