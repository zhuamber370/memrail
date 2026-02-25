# Agent-First KMS MVP 轻量实现计划

> 基于文档：`<repo_root>/docs/plans/2026-02-21-agent-first-kms-final-system-design.md`
> 目标：以最小任务集落地 Task 增强版 MVP。

## 技术栈与运行前提

1. 前端：`Next.js + TypeScript + Tailwind + TanStack Query`
2. 后端：`FastAPI + Pydantic + SQLAlchemy + Alembic`
3. 数据库：`PostgreSQL @ 127.0.0.1:5432`
4. 开发方式：本地运行（不使用 Docker）

## 任务 1：数据库模型增强（Task + Cycle）

**涉及文件**
- Modify: `<repo_root>/backend/db/schema.sql`
- Modify: `<repo_root>/backend/db/migrations/001_init.sql`

**验证方式**
- 运行：`rg -n "cycle_id|next_review_at|blocked_by_task_id|archived_at|cycles" <repo_root>/backend/db/schema.sql`
- 预期：Task 新字段与 cycles 表存在。

## 任务 2：Task API 扩展

**涉及文件**
- Modify: `<repo_root>/backend/src/routes/tasks.py`
- Modify: `<repo_root>/backend/src/services/task_service.py`
- Modify: `<repo_root>/backend/src/schemas.py`

**验证方式**
- 运行：`pytest -q <repo_root>/backend/tests`
- 预期：Task 创建/查询/更新测试通过并覆盖新字段。

## 任务 3：新增 Task 增强接口

**涉及文件**
- Modify: `<repo_root>/backend/src/routes/tasks.py`
- Create: `<repo_root>/backend/src/routes/cycles.py`
- Modify: `<repo_root>/backend/src/app.py`

**验证方式**
- 运行：`curl -X POST http://localhost:8000/api/v1/tasks/batch-update -H "Authorization: Bearer $KMS_API_KEY" -H "Content-Type: application/json" -d '{"task_ids":["tsk_1"],"patch":{"priority":"P1"}}'`
- 运行：`curl http://localhost:8000/api/v1/tasks/views/summary -H "Authorization: Bearer $KMS_API_KEY"`
- 预期：返回 200 且结构合法。

## 任务 4：错误处理增强

**涉及文件**
- Modify: `<repo_root>/backend/src/middleware/error_handler.py`
- Modify: `<repo_root>/backend/src/services/task_service.py`

**验证方式**
- 运行：非法状态跳转请求
- 预期：`409` + `TASK_INVALID_STATUS_TRANSITION`。

## 任务 5：OpenClaw Skill 参数对齐

**涉及文件**
- Modify: `<repo_root>/skill/openclaw_skill.py`
- Modify: `<repo_root>/skill/actions/create_task.py`
- Modify: `<repo_root>/skill/actions/propose_commit_undo.py`

**验证方式**
- 运行：skill 调用 `create_task/list_tasks`
- 预期：新参数可透传并被 API 接收。

## 任务 6：前端 Tasks 页面增强

**涉及文件**
- Modify: `<repo_root>/frontend/app/tasks/page.tsx`
- Modify: `<repo_root>/frontend/src/lib/api.ts`
- Modify: `<repo_root>/frontend/app/globals.css`

**验证方式**
- 运行：`cd <repo_root>/frontend && npm run build`
- 预期：构建通过，Tasks 页面可筛选视图并批量更新。

## 任务 7：验收回归

**涉及文件**
- Modify: `<repo_root>/docs/reports/mvp-e2e-checklist.md`

**验证方式**
- 执行闭环：`capture -> propose -> commit -> audit -> undo -> audit`
- 预期：全部通过且审计完整。
