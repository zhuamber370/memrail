# OpenClaw x KMS 接入说明（v2，通用安装版）

## 1. 目标

- OpenClaw 不再写 Obsidian，任务/日记/知识统一写入 KMS。
- 不再手动粘贴系统提示词。
- 不再手动接 `.py` 动作脚本。
- 写入仍执行 `dry-run -> 用户决策(commit/reject)`。
- 任务写入必须有分类：agent 自动分类，无法判断时回退 `top_fx_other`。

## 2. 前置条件

1. 启动 KMS 后端
```bash
cd /Users/celastin/Desktop/projects/kms-for-agent/backend
python3 -m uvicorn src.app:app --reload --port 8000
```

2. 设置 OpenClaw 进程可见的环境变量
```bash
export KMS_BASE_URL="http://127.0.0.1:8000"
export KMS_API_KEY="<your_api_key>"
```

## 3. 一次性安装 Workspace Skill

在项目根目录执行：

```bash
cd /Users/celastin/Desktop/projects/kms-for-agent
bash scripts/install_openclaw_kms_skill.sh
```

脚本会自动识别 OpenClaw workspace（读取 `~/.openclaw/openclaw.json` 的 `agents.defaults.workspace`），并安装到 `<workspace>/skills/kms`。

安装后检查：

```bash
openclaw skills info kms --json
openclaw skills check --json
```

如果 `eligible=false`，通常是环境变量未生效，确认 `KMS_BASE_URL` 和 `KMS_API_KEY` 后重启 OpenClaw 网关进程。

## 4. 使用方式（给 OpenClaw 的自然语言指令）

1. 记录 todo
```text
记录todo：
标题=...
描述=...
优先级=P1
截止=2026-02-28
分类=top_fx_operations_delivery
```

2. 追加日记
```text
追加日记：
日期=2026-02-24
内容=...
```

3. 写入 topic/知识
```text
记录topic：
标题=...
增量内容=...
分类=top_fx_product_strategy
标签=tag1,tag2
```

4. 查询上下文
```text
获取上下文：
意图=planning
窗口天数=14
```

5. 提交和回滚
```text
确认提交 change_set_id=<id>
拒绝提案 change_set_id=<id>
回滚最近一次提交，原因=...
```

## 5. 卸载 Skill

```bash
cd /Users/celastin/Desktop/projects/kms-for-agent
bash scripts/uninstall_openclaw_kms_skill.sh
```

## 6. 故障排查

1. 写入失败优先看 dry-run 响应和后端错误码，不直接重复 commit。
2. 同名重复通常和 `source` 不稳定有关，确保 `source` 可追溯且固定。
3. 异常提交可调用回滚流程（`undo_last_commit`）。
4. 用户明确拒绝提案时，调用 `reject_changes` 删除提案，不要留在收件箱。
