# MVP Release Notes (Draft)

## 已实现
- 后端：Task/Knowledge/Links/Governance/Audit API + internal Inbox ingestion API
- 安全：API Key 中间件（可开关）与统一错误响应
- 治理：dry-run -> commit -> undo-last 基础闭环
- 审计：写操作产生审计事件并可查询
- 前端：Tasks/Knowledge/Changes/Audit 四页面（Inbox 已内部化）
- Skill：OpenClaw 高层动作映射（含重试策略）

## 已验证
- Backend tests: `9 passed`
- Frontend build: success
- DB connectivity: `192.168.50.245:5432` ok

## 已知限制
- 变更去重目前是最小实现（候选输出为基础版）
- 前端页面为 MVP 壳层，交互深度待继续扩展
- 多租户/OAuth 未实现（符合非目标）
- 输入来源约束为 user-agent 聊天记录（`chat://...`），Inbox 不再作为用户可见入口

## 下一步建议
1. 将 Changes UI 接到 Task/Knowledge 页面入口
2. 增加 audit 过滤参数与前端筛选器
3. 为 Skill 增加集成测试和命令行入口
