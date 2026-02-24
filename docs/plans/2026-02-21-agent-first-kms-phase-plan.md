# Agent-First KMS Phase Plan Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 2-4 周内完成 Agent-First KMS MVP 的后端/API/Skill/验收闭环，并落地 Task 管理增强（视图/周期/阻塞/复盘）。

**Architecture:** 以云端 REST API 为唯一写入中心，Web UI 与 OpenClaw Skill 共用同一服务能力。批量写入统一经过治理链路（dry-run/diff/commit/reject/undo/audit），并以保守去重策略防止熵增。

**Tech Stack:** Next.js + TypeScript + Tailwind + TanStack Query；FastAPI + Pydantic + SQLAlchemy + Alembic；PostgreSQL。

---

## 阶段总览

1. Phase 1：任务域模型增强与基础 API
2. Phase 2：治理链路与审计闭环
3. Phase 3：OpenClaw Skill 对齐与错误语义
4. Phase 4：前端交互闭环与验收发布

## Phase 1：任务域模型增强与基础 API

**范围**

- 扩展 Task 字段：`cycle_id/next_review_at/blocked_by_task_id/archived_at`。
- 新增 Cycle 模型。
- 扩展 Task 查询视图与批量更新能力。

**任务清单**

1. 扩展 `tasks` 表与索引。
2. 新增 `cycles` 表与基础索引。
3. 扩展 `POST /tasks`、`GET /tasks`、`PATCH /tasks/{task_id}`。
4. 新增 `POST /tasks/batch-update`、`POST /tasks/{task_id}/reopen`、`GET /tasks/views/summary`。
5. 新增 `POST /cycles`、`GET /cycles`。

**DoD**

1. 预置视图 `today|overdue|this_week|backlog|blocked|done` 可查询。
2. 状态机非法转移返回 `409`。
3. `blocked_by_task_id` 不允许自引用，且必须存在。

## Phase 2：治理链路与审计闭环

**范围**

- 完成 dry-run/commit/reject/undo-last/audit 最小可用链路。
- 完成保守去重（仅提案，不自动合并）。

**任务清单**

1. 提供 `POST /changes/dry-run`。
2. 提供 `POST /changes/{change_set_id}/commit`。
3. 提供 `DELETE /changes/{change_set_id}`（拒绝并删除提案）。
4. 提供 `POST /commits/undo-last`（仅最近一次）。
5. 提供 `GET /audit/events`。
6. 在 diff 中展示 Task 增强字段变化（cycle/review/blocked）。

## Phase 3：OpenClaw Skill 对齐与错误语义

**范围**

- 按 v0.2 契约实现动作参数。
- 统一错误映射与重试策略。

**任务清单**

1. `create_task` 支持 `cycle_id/next_review_at/blocked_by_task_id`。
2. `list_tasks` 支持 `view/cycle_id/blocked/stale_days/updated_before`。
3. 完成 `429/500` 指数退避。
4. 完成 `client_request_id` 幂等透传。

## Phase 4：前端交互闭环与验收发布

**范围**

- 完成 Tasks 页面增强交互。
- 跑通完整端到端验收。

**任务清单**

1. Tasks 页面增加预置视图与批量操作。
2. Task Detail 支持 cycle/review/blocked 编辑。
3. Review 区支持 stale 与 blocked 快速处理。
4. 执行验收闭环：`capture -> propose -> commit -> audit -> undo -> audit`。

## 里程碑验收点

1. M1：Task 增强 API 可用。
2. M2：治理链路可用。
3. M3：Skill 契约对齐。
4. M4：前后端交互与验收通过。
