# MVP E2E Checklist (Synced 2026-02-24)

## 环境
- API Base: `http://localhost:8000`
- DB: `postgresql://afkms:***@192.168.50.245:5432/afkms`

## 流程验证
1. Propose Changes
- 调用 `POST /api/v1/changes/dry-run`
- 预期：`200`，返回 `change_set_id` 与 `diff_items`

2. Reject Proposal (Delete)
- 调用 `DELETE /api/v1/changes/{id}`
- 预期：`200`，状态 `rejected`
- 再调用 `GET /api/v1/changes/{id}`，预期 `404`

3. Commit Changes
- 再次 dry-run 后调用 `POST /api/v1/changes/{id}/commit`
- 预期：`200`，状态 `committed`

4. Audit Query
- 调用 `GET /api/v1/audit/events`
- 预期：可见写入事件（actor/tool/action/target）

5. Undo Last
- 调用 `POST /api/v1/commits/undo-last`
- 预期：`200`，状态 `reverted`

6. Frontend Changes Flow
- 在 `/changes` 页面执行：审阅提案 -> 提交 或 拒绝 -> 回滚最近提交
- 预期：页面展示结构化摘要与 diff（非手填/手看 JSON 流程）

7. Frontend Visible Routes
- 访问 `/tasks` `/knowledge` `/changes` `/audit`
- 预期：可访问且可交互

## 判定
- 全部通过：MVP 可演示
- 任一失败：阻断发布，先修复
