# Agent-First KMS Implementation Input Pack (v0.6, Synced 2026-02-24)

## 1. Current Build Target
以“可执行治理 + 稳定分类 + 人类可审阅 UI”为交付目标，当前稳定域：
- Topic（固定分类）
- Task（强结构动作项）
- Knowledge Note（可归类、可归档）
- Journal（同日单条 append-only）
- Change Governance（dry-run/commit/reject/undo）
- Context Bundle（Agent 聚合读取）
- Audit（可查询追溯）

## 2. Delivered in Current Baseline
1. 固定 Topic 分类（7 类）落库并由后端统一返回中英文名。
2. `POST /topics` 锁定，防止分类体系在 MVP 被写乱。
3. Task 强结构字段与状态治理落地（含取消原因强约束）。
4. Task 强制 `topic_id`，并记录 `task_sources`。
5. Task 支持批量取消、选中归档、归档只读视图。
6. Task 支持删除接口与前端删除交互。
7. Knowledge 支持 `topic_id/status`，默认按 Topic 分组展示。
8. Knowledge 支持未归类视图与批量归类。
9. Knowledge 支持编辑 topic/tags、归档、删除。
10. Change governance 的 `change_actions` 持久化并带 `action_index`。
11. Commit 从登记升级为真实执行（task/note/link）。
12. Undo 从占位升级为真实回滚（逆序撤销动作）。
13. Commit/Undo 支持 `client_request_id` 幂等。
14. Audit 查询支持 actor/tool/action/target/time 多条件过滤。
15. Changes UI 改为提案收件箱（选择提案审阅并提交或拒绝）。
16. 新增 Journals API：`upsert-append/list/by-date`（同日追加写）。
17. 新增 Context Bundle API：`/api/v1/context/bundle`（tasks+notes+journals）。
18. Changes 新增动作：`patch_note`、`upsert_journal_append`，并支持 undo 回滚。
19. OpenClaw 契约更新为“显式指令触发 + DB 真源 + 默认 dry-run”。
20. 清理脚本：`backend/scripts/cleanup_test_data.py`。
21. 知识迁移脚本：`backend/scripts/migrate_notes_topic_status.py`。

## 3. Data and Schema Baseline
核心表：
- `topics, topic_aliases`
- `tasks, task_sources, cycles`
- `notes, note_sources, links`
- `journals, journal_items`
- `change_sets, change_actions, commits`
- `audit_events`

预留域（已建表，API 待交付）：
- `topic_entries`

兼容说明：
- `tasks.project` 列仍保留在 DB，用于历史兼容；当前 API/前端不再使用。

## 4. Runtime and Environment
- Backend: FastAPI + SQLAlchemy。
- Frontend: Next.js。
- DB: PostgreSQL（MVP 单库）。
- 启动时执行 runtime schema guard（`ensure_runtime_schema`）保障兼容升级。

## 5. Verification Snapshot (2026-02-24)
已执行：
- Backend:
  - `python3 -m pytest backend/tests/test_tasks_api.py backend/tests/test_inbox_notes_api.py backend/tests/test_links_api.py backend/tests/test_audit_api.py backend/tests/test_topics_api.py backend/tests/test_changes_api.py backend/tests/test_journals_api.py backend/tests/test_context_api.py -q`
  - result: `47 passed`
- Frontend:
  - `npm run -s build`（`frontend/`）
  - result: success

## 6. Acceptance Checklist (Current)
1. Task 创建若 `topic_id` 无效，返回 `TOPIC_NOT_FOUND`。
2. Task 设为 `cancelled` 时必须提供 `cancelled_reason`。
3. 仅 `done/cancelled` 可归档；归档后默认不出现在执行列表。
4. Task 页面默认 `todo`，并支持优先级/状态/分类筛选。
5. Knowledge 可在无 topic 情况下创建（进入 unclassified）。
6. Unclassified 支持批量归类到固定 Topic。
7. Knowledge archived 视图只读。
8. Changes 可直接审阅提案并提交，不依赖手填 JSON。
9. Changes 可拒绝提案（删除 proposed 变更），避免提案堆积。
10. Commit 可真实写入，Undo 可真实回滚最近一次提交。
11. 审计能追踪 change_set/commit/action 级链路信息。
12. Journals 同日追加写不创建重复日记行。
13. Context Bundle 可为 Agent 返回任务+知识+日记聚合上下文。
14. `patch_note` 与 `upsert_journal_append` 可在 changes 流程中 commit 与 undo。

## 7. Known Gaps / Next Slice
1. Journal triage/close（`journal_items`）尚未开放。
2. Audit UI 仍是最小 JSON 读取视图（后端筛选能力未完整前端化）。
3. 风险分级自动提交策略（policy engine）未落地。
4. 多租户鉴权（per-user token/OAuth）未落地。
5. MCP server 尚未实现（当前统一入口为 REST + skill）。
