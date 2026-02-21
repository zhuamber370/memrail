# MVP E2E Checklist

## 环境
- API Base: `http://localhost:8000`
- DB: `postgresql://afkms:***@192.168.50.245:5432/afkms`

## 流程验证
1. Internal Capture Inbox
- 调用 `POST /api/v1/inbox/captures`
- 预期：`201`，返回 `inb_*`；`source` 必须为 `chat://...`

2. Propose Changes
- 调用 `POST /api/v1/changes/dry-run`
- 预期：`200`，返回 `change_set_id` 与 `diff`

3. Commit Changes
- 调用 `POST /api/v1/changes/{id}/commit`
- 预期：`200`，状态 `committed`

4. Audit Query
- 调用 `GET /api/v1/audit/events`
- 预期：可见写入事件（actor/tool/action/target）

5. Undo Last
- 调用 `POST /api/v1/commits/undo-last`
- 预期：`200`，状态 `reverted`

6. Frontend Changes Flow
- 在 `/changes` 页面执行 Dry-run -> Commit -> Undo
- 预期：页面展示每步 JSON 结果，无崩溃

7. Frontend Visible Routes
- 访问 `/tasks` `/knowledge` `/changes` `/audit`
- 预期：可访问且可交互；无 Inbox 用户入口

## 判定
- 全部通过：MVP 可演示
- 任一失败：阻断发布，先修复
