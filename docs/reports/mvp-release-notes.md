# MVP Release Notes (Synced 2026-02-24)

## 已实现
- 后端：`topics/tasks/notes/links/changes/audit` API 全链路可用。
- 治理：`dry-run -> commit -> undo-last` 从占位升级为真实执行与真实回滚。
- 审计：写操作落审计，支持按 actor/tool/action/target/time 过滤查询。
- 任务：固定分类、强字段编辑、批量取消（统一原因）、终态归档、归档只读。
- 知识：Topic Board（分组浏览/未归类治理/详情审阅/归档只读）。
- 变更：Changes 页改为“提案收件箱”，支持选中提案直接提交。
- 多语言：前端默认英文，可切换中文。

## 本次验证结果
- Backend tests:
  - `python3 -m pytest backend/tests/test_changes_api.py backend/tests/test_tasks_api.py backend/tests/test_inbox_notes_api.py backend/tests/test_links_api.py backend/tests/test_audit_api.py backend/tests/test_topics_api.py -q`
  - `40 passed`
- Frontend build:
  - `npm run -s build`（`frontend/`）
  - success

## 当前边界
- Audit UI 目前是最小版（Load + JSON 显示），高级筛选 UI 待补。
- Journal 相关表已存在，但 API/UI 工作流未交付。
- 多租户鉴权（per-user token/OAuth）未交付。
- MCP server 未交付，当前统一入口仍是 REST + skill。

## 运行提醒
- 使用 `.env` 管理数据库与 API 参数，不在代码/文档写入密钥。
- 测试后请运行：`python3 backend/scripts/cleanup_test_data.py` 清理测试数据。
