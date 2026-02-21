# Agent-First KMS MVP PRD-lite + API 契约草案

> 日期：2026-02-21  
> 状态：Draft v0.2（Task 管理增强）

## 1. 产品定位

`Agent-First Personal OS (Cloud SaaS)`：通过默认信息架构与写入治理机制，让用户与 Agent 共建并持续维护个人信息系统。  
核心价值不是 CRUD，而是可复用的方法论与低熵长期维护能力。

## 2. 产品目标与成功标准

### 2.1 目标

- 用户不需要自行设计信息架构即可长期管理任务与知识。
- Agent 写入可控、可审计、可回滚，避免系统被“写烂”。
- 用户可直接在系统内增删改查，不依赖 Markdown/Obsidian。

### 2.2 北极星结果（MVP）

- 任意批量写入都先可提案（dry-run）并给出可读 diff。
- 每次提交均可审计；最近一次批量写入可一键回滚。
- 重复内容不会自动合并，必须先提案并经人工确认。
- 用户可直接使用预置任务治理方式（视图/周期/复盘），无需自行设计。

## 3. 用户与使用场景

### 3.1 目标用户

- 个人知识工作者（高频任务管理 + 知识沉淀）。

### 3.2 核心场景

- 用户在 Task/Knowledge 中完成管理与沉淀，输入来自 user-agent 聊天记录。
- 在 Task 中管理行动项，在 Knowledge 中沉淀结论并保留来源。
- 通过 Agent 执行批量维护，但最终由用户审阅并提交。

## 4. 信息架构（IA）

### 4.1 Inbox（内部输入流）

- 定义：系统内部 ingestion 层，不作为用户页面入口。
- 要求：来源限定为 user-agent 聊天（`chat://...`）。
- 最小字段：`id, content, source, captured_at, status`。

### 4.2 Task（强结构化任务系统）

- 定义：仅存“要做动作”。
- 字段策略：MVP 固定字段，不允许自定义字段。
- 字段：`id, title, status, priority, due, project, source, cycle_id, next_review_at, blocked_by_task_id, archived_at, created_at, updated_at`。
- 状态：`todo | in_progress | done | cancelled`。
- 预置视图：`today | overdue | this_week | backlog | blocked | done`。

### 4.3 Knowledge（结构化知识资产）

- 定义：结论/方法/踩坑/决策等长期资产。
- 要求：必须有 `source`；MVP 允许文本来源（URL 非必填）。
- 最小字段：`id, title, body, sources[], links[], created_at, updated_at`。

## 5. 写入治理与审计

### 5.1 强制流程

`dry_run -> diff -> commit -> undo_last -> audit`

- `dry_run`：校验并生成变更提案，不落库。
- `diff`：输出人可读摘要（新增/修改/合并建议/冲突提示）。
- `commit`：按 `change_set_id` 原子提交。
- `undo_last`：仅回滚最近一次批量提交。
- `audit`：记录完整写入上下文。

### 5.2 去重/合并策略（已确认）

- 模式：保守模式（仅提案，不自动合并）。
- 行为：命中重复规则后仅返回 `duplicate_candidate` 与 `merge_proposal`。

## 6. OpenClaw 接入策略

### 6.1 分阶段

- 阶段 1（MVP）：REST API + OpenClaw Skill（唯一维护入口）。
- 阶段 2（后续）：官方 MCP Server（生态标准化）。

### 6.2 统一入口原则

- AGENTS/工作流中声明：任务/知识写入只走云系统。
- AGENTS.md 不存密钥。
- Skill 只暴露高层动作，不暴露低级 CRUD。

## 7. 鉴权与安全边界

- MVP：单用户单 API Key（通过环境变量或 1Password 注入）。
- 禁止：key 硬编码到代码/skill/AGENTS.md。
- 预留：未来 per-user token/OAuth 与权限隔离接口。

## 8. MVP 功能范围（2-4 周）

### 8.1 Web UI

- Task / Knowledge / Changes / Audit 入口。
- Task 支持预置视图、状态流、批量更新、阻塞关系与复盘入口。

### 8.2 API

- Task：create/list/update/batch-update/reopen/views-summary。
- Cycle：create/list。
- Knowledge：append/search。
- Link：实体关联。
- Governance：dry-run/commit/undo/audit。

### 8.3 审计

- 每次写入记录来源与变更摘要（最小可用）。

### 8.4 OpenClaw Skill

- 统一调用 REST 完成 capture/propose/commit/undo/query。

## 9. 非目标（MVP 不做）

- 完整多租户与 RBAC。
- 任意历史回滚（只支持最近一次 commit）。
- Obsidian 双向实时同步插件。
- 复杂工作流编排与审批引擎。
- 甘特图/资源排班与高级报表中心。

## 10. API 契约草案（MVP）

> 约定：JSON over HTTPS，`Authorization: Bearer <API_KEY>`  
> 基础路径：`/api/v1`

### 10.1 Task

#### `POST /tasks`

```json
{
  "title": "string",
  "status": "todo",
  "priority": "P2",
  "due": "2026-03-01",
  "project": "string",
  "source": "meeting notes 2026-02-21",
  "cycle_id": "cyc_001",
  "next_review_at": "2026-03-02T09:00:00Z",
  "blocked_by_task_id": "tsk_101"
}
```

#### `GET /tasks`

查询参数：`view, status, priority, project, cycle_id, blocked, stale_days, due_before, updated_before, q, page, page_size`

#### `PATCH /tasks/{task_id}`

允许字段：`status, priority, due, project, cycle_id, next_review_at, blocked_by_task_id, archived_at`

#### `POST /tasks/batch-update`

```json
{
  "task_ids": ["tsk_1", "tsk_2"],
  "patch": {"priority": "P1", "cycle_id": "cyc_001"}
}
```

#### `POST /tasks/{task_id}/reopen`

- 用途：`done/cancelled -> todo` 的显式恢复动作。

#### `GET /tasks/views/summary`

- 返回：`today/overdue/blocked/stale/done` 计数。

### 10.2 Cycle

- `POST /cycles`
- `GET /cycles`

### 10.3 Inbox

- `POST /inbox/captures`（仅供内部 ingestion 使用，不在用户 UI 暴露）

### 10.4 Knowledge

- `POST /notes/append`
- `GET /notes/search`

### 10.5 Link

- `POST /links`

### 10.6 Governance

- `POST /changes/dry-run`
- `POST /changes/{change_set_id}/commit`
- `POST /commits/undo-last`
- `GET /audit/events`

## 11. 错误码草案

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`
- `403 FORBIDDEN`
- `404 TASK_NOT_FOUND|CYCLE_NOT_FOUND`
- `409 TASK_INVALID_STATUS_TRANSITION|CHANGESET_ALREADY_COMMITTED`
- `422 TASK_BLOCKED_BY_NOT_FOUND|TASK_BLOCKED_BY_SELF`
- `429 RATE_LIMITED`
- `500 INTERNAL_ERROR`

统一错误响应：

```json
{
  "error": {
    "code": "TASK_INVALID_STATUS_TRANSITION",
    "message": "Cannot move task from done to in_progress directly.",
    "details": {"from": "done", "to": "in_progress"},
    "request_id": "req_123"
  }
}
```

## 12. OpenClaw Skill 动作映射（MVP）

- `capture_inbox(text, source)` -> `POST /inbox/captures`（`source` 必须为 `chat://...`）
- `create_task(...)` -> `POST /tasks`
- `append_note(..., sources)` -> `POST /notes/append`
- `propose_changes(batch)` -> `POST /changes/dry-run`
- `commit_changes(change_set_id)` -> `POST /changes/{id}/commit`
- `undo_last_commit()` -> `POST /commits/undo-last`
- `search_notes(...)` -> `GET /notes/search`
- `list_tasks(...)` -> `GET /tasks`

## 13. 验收清单（MVP）

- 所有批量写入链路可执行 dry-run，并返回可读 diff。
- commit 后可执行 undo_last 且有审计记录。
- Task 字段不可越权扩展，未知字段写入被拒绝。
- Knowledge 新增必须带至少一个 source（允许文本）。
- 重复命中仅生成 proposal，不自动合并。
- Task 预置视图与 batch-update 在前后端可用。
- OpenClaw Skill 可完成捕获、提案、提交、查询与回滚闭环。
