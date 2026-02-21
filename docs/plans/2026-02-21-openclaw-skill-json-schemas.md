# OpenClaw Skill JSON Schema 草案（MVP）

> 日期：2026-02-21  
> 状态：Draft v0.2（Task 管理增强）  
> Schema 方言：`https://json-schema.org/draft/2020-12/schema`

## 1. 说明

- 目标：给 OpenClaw Skill 的每个高层动作提供可执行的请求/响应校验规范。
- 约束来源：与以下文档保持一致  
  - `/Users/celastin/Desktop/projects/kms-for-agent/docs/plans/2026-02-21-agent-first-kms-prd-api.md`  
  - `/Users/celastin/Desktop/projects/kms-for-agent/docs/plans/2026-02-21-openclaw-skill-contract.md`
- 原则：MVP 不引入未确认能力（如任意历史回滚、多租户字段）。

## 2. 通用 Schema

### 2.1 ErrorResponse

```json
{
  "$id": "kms.skill.common.error_response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ErrorResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["error"],
  "properties": {
    "error": {
      "type": "object",
      "additionalProperties": false,
      "required": ["code", "message", "request_id"],
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "INVALID_REQUEST",
            "UNAUTHORIZED",
            "FORBIDDEN",
            "NOT_FOUND",
            "CONFLICT",
            "VALIDATION_FAILED",
            "RATE_LIMITED",
            "INTERNAL_ERROR"
          ]
        },
        "message": {"type": "string", "minLength": 1},
        "request_id": {"type": "string", "minLength": 1}
      }
    }
  }
}
```

### 2.2 ActorRef

```json
{
  "$id": "kms.skill.common.actor_ref",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ActorRef",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "id"],
  "properties": {
    "type": {"type": "string", "enum": ["agent", "user"]},
    "id": {"type": "string", "minLength": 1}
  }
}
```

### 2.3 SourceItem

```json
{
  "$id": "kms.skill.common.source_item",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SourceItem",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "value"],
  "properties": {
    "type": {"type": "string", "enum": ["text", "url", "doc_id", "message_id"]},
    "value": {"type": "string", "minLength": 1}
  }
}
```

## 3. 动作 Schema

## 3.1 capture_inbox

> 说明：`capture_inbox` 为 internal-only 动作，不作为用户 UI 入口。

```json
{
  "$id": "kms.skill.capture_inbox.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CaptureInboxRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["text", "source"],
  "properties": {
    "text": {"type": "string", "minLength": 1},
    "source": {"type": "string", "pattern": "^chat://.+"}
  }
}
```

```json
{
  "$id": "kms.skill.capture_inbox.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CaptureInboxResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "status", "captured_at"],
  "properties": {
    "id": {"type": "string", "pattern": "^inb_[A-Za-z0-9]+$"},
    "status": {"type": "string", "enum": ["open", "archived"]},
    "captured_at": {"type": "string", "format": "date-time"}
  }
}
```

## 3.2 create_task

```json
{
  "$id": "kms.skill.create_task.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CreateTaskRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["title", "status", "source"],
  "properties": {
    "title": {"type": "string", "minLength": 1, "maxLength": 200},
    "status": {
      "type": "string",
      "enum": ["todo", "in_progress", "done", "cancelled"]
    },
    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
    "due": {"type": "string", "format": "date"},
    "project": {"type": "string", "minLength": 1, "maxLength": 120},
    "source": {"type": "string", "minLength": 1},
    "cycle_id": {"type": "string", "pattern": "^cyc_[A-Za-z0-9]+$"},
    "next_review_at": {"type": "string", "format": "date-time"},
    "blocked_by_task_id": {"type": "string", "pattern": "^tsk_[A-Za-z0-9]+$"}
  }
}
```

```json
{
  "$id": "kms.skill.create_task.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CreateTaskResponse",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "title",
    "status",
    "source",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "id": {"type": "string", "pattern": "^tsk_[A-Za-z0-9]+$"},
    "title": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["todo", "in_progress", "done", "cancelled"]
    },
    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
    "due": {"type": "string", "format": "date"},
    "project": {"type": "string"},
    "source": {"type": "string"},
    "cycle_id": {"type": "string"},
    "next_review_at": {"type": "string", "format": "date-time"},
    "blocked_by_task_id": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  }
}
```

## 3.3 append_note

```json
{
  "$id": "kms.skill.append_note.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AppendNoteRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["title", "body", "sources"],
  "properties": {
    "title": {"type": "string", "minLength": 1, "maxLength": 200},
    "body": {"type": "string", "minLength": 1},
    "sources": {
      "type": "array",
      "minItems": 1,
      "items": {"$ref": "kms.skill.common.source_item"}
    },
    "tags": {
      "type": "array",
      "items": {"type": "string", "minLength": 1},
      "uniqueItems": true
    }
  }
}
```

```json
{
  "$id": "kms.skill.append_note.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AppendNoteResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "title", "created_at", "updated_at"],
  "properties": {
    "id": {"type": "string", "pattern": "^nte_[A-Za-z0-9]+$"},
    "title": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  }
}
```

## 3.4 search_notes

```json
{
  "$id": "kms.skill.search_notes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SearchNotesRequest",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "query": {"type": "string"},
    "tag": {"type": "string"},
    "linked_task_id": {"type": "string", "pattern": "^tsk_[A-Za-z0-9]+$"},
    "page": {"type": "integer", "minimum": 1, "default": 1},
    "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
  }
}
```

```json
{
  "$id": "kms.skill.search_notes.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SearchNotesResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["items", "page", "page_size", "total"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "page": {"type": "integer", "minimum": 1},
    "page_size": {"type": "integer", "minimum": 1},
    "total": {"type": "integer", "minimum": 0}
  }
}
```

## 3.5 list_tasks

```json
{
  "$id": "kms.skill.list_tasks.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ListTasksRequest",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "view": {"type": "string", "enum": ["today", "overdue", "this_week", "backlog", "blocked", "done"]},
    "status": {"type": "string", "enum": ["todo", "in_progress", "done", "cancelled"]},
    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
    "project": {"type": "string"},
    "cycle_id": {"type": "string", "pattern": "^cyc_[A-Za-z0-9]+$"},
    "blocked": {"type": "boolean"},
    "stale_days": {"type": "integer", "minimum": 1},
    "due_before": {"type": "string", "format": "date"},
    "updated_before": {"type": "string", "format": "date-time"},
    "query": {"type": "string"},
    "page": {"type": "integer", "minimum": 1, "default": 1},
    "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
  }
}
```

```json
{
  "$id": "kms.skill.list_tasks.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ListTasksResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["items", "page", "page_size", "total"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "page": {"type": "integer", "minimum": 1},
    "page_size": {"type": "integer", "minimum": 1},
    "total": {"type": "integer", "minimum": 0}
  }
}
```

## 3.6 propose_changes

```json
{
  "$id": "kms.skill.propose_changes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ProposeChangesRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["actions", "actor", "tool"],
  "properties": {
    "actions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["type", "payload"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["create_task", "append_note", "link_entities", "update_task"]
          },
          "payload": {"type": "object"}
        }
      }
    },
    "actor": {"$ref": "kms.skill.common.actor_ref"},
    "tool": {"type": "string", "const": "openclaw-skill"}
  }
}
```

```json
{
  "$id": "kms.skill.propose_changes.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ProposeChangesResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["change_set_id", "summary", "diff", "status"],
  "properties": {
    "change_set_id": {"type": "string", "pattern": "^chg_[A-Za-z0-9]+$"},
    "summary": {
      "type": "object",
      "additionalProperties": false,
      "required": ["creates", "updates", "duplicate_candidates"],
      "properties": {
        "creates": {"type": "integer", "minimum": 0},
        "updates": {"type": "integer", "minimum": 0},
        "duplicate_candidates": {"type": "integer", "minimum": 0}
      }
    },
    "diff": {"type": "array", "items": {"type": "string"}},
    "status": {"type": "string", "const": "proposed"}
  }
}
```

## 3.7 commit_changes

```json
{
  "$id": "kms.skill.commit_changes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CommitChangesRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["change_set_id", "approved_by"],
  "properties": {
    "change_set_id": {"type": "string", "pattern": "^chg_[A-Za-z0-9]+$"},
    "approved_by": {"$ref": "kms.skill.common.actor_ref"},
    "client_request_id": {"type": "string", "minLength": 1}
  }
}
```

```json
{
  "$id": "kms.skill.commit_changes.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CommitChangesResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["commit_id", "change_set_id", "status", "committed_at"],
  "properties": {
    "commit_id": {"type": "string", "pattern": "^cmt_[A-Za-z0-9]+$"},
    "change_set_id": {"type": "string", "pattern": "^chg_[A-Za-z0-9]+$"},
    "status": {"type": "string", "const": "committed"},
    "committed_at": {"type": "string", "format": "date-time"}
  }
}
```

## 3.8 undo_last_commit

```json
{
  "$id": "kms.skill.undo_last_commit.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "UndoLastCommitRequest",
  "type": "object",
  "additionalProperties": false,
  "required": ["requested_by", "reason"],
  "properties": {
    "requested_by": {"$ref": "kms.skill.common.actor_ref"},
    "reason": {"type": "string", "minLength": 1},
    "client_request_id": {"type": "string", "minLength": 1}
  }
}
```

```json
{
  "$id": "kms.skill.undo_last_commit.response",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "UndoLastCommitResponse",
  "type": "object",
  "additionalProperties": false,
  "required": ["undone_commit_id", "revert_commit_id", "status"],
  "properties": {
    "undone_commit_id": {"type": "string", "pattern": "^cmt_[A-Za-z0-9]+$"},
    "revert_commit_id": {"type": "string", "pattern": "^cmt_[A-Za-z0-9]+$"},
    "status": {"type": "string", "const": "reverted"}
  }
}
```

## 4. 一致性约束清单

- `create_task.request` 使用 `additionalProperties: false`，保证 Task 固定字段。
- `undo_last_commit` 不提供历史 commit id 入参，保证“仅回滚最近一次”边界。
- `append_note.request.sources` `minItems=1`，保证 Knowledge 必有来源。
- 去重处理不提供自动合并动作 schema，仅通过 `propose_changes` 返回候选信息。

## 5. 已确认决策

- `priority` 锁定为 `P0-P3`。
- `project` 在 MVP 保持字符串类型。
- `search/list` 返回 `items` 在 MVP 保持宽类型（对象）。
