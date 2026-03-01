> Documentation Status: Current
> Last synced: 2026-03-01

# 2026-03-01 DAG EntityLog 变更日志

## 范围
- 执行计划：`docs/plans/2026-03-01-dag-entity-log-implementation-plan.md`
- 目标：将 DAG 执行记录统一到 `entity_logs`，并完成前端执行面板的日志化改造与交互精简。

## 后端能力交付
- 新增统一日志模型：`entity_logs`（`entity_type + entity_id`）
- 节点与边统一日志 CRUD API 已落地（含 patch/delete）
- 路由图接口返回节点/边 `has_logs`，用于前端徽标判断
- 旧 `description` 保留兼容但不再作为执行日志主入口

## 前端能力交付
- 执行面板由 description 编辑器切换为日志面板（node inspector）
- 新增步骤表单简化为：`标题 + 状态`
- DAG 边线交互精简：
  - 去掉边类型判断和边关系标签展示
  - 去掉边日志入口与边选中交互
  - 仅保留节点之间的连接线展示
- idea 页面发起执行链路时，节点类型固定为 `goal`

## 本次收尾同步（2026-03-01）
- 同步 `docs/reports/mvp-release-notes.md` 到最新交付状态
- 补充本文件作为本轮实现变更日志
- 计划文档补充执行完成记录（见计划文档末尾）

## 验证记录
- 前端构建：`cd frontend && npm run build`
- 后端关键回归：`cd backend && pytest tests/test_routes_api.py -q`

## 备注
- 本地开发已按要求连接 `192.168.50.245` 数据库进行验证。
- `postgresql` 本地化配置/产物不纳入本次远程提交内容。
