# OpenClaw Skill JSON Schemas (v0.4, Synced 2026-02-24)

Schema dialect: `https://json-schema.org/draft/2020-12/schema`

This document covers the active read/write actions for explicit-command mode.

## 1) Common

### ActorRef

```json
{
  "$id": "kms.skill.common.actor_ref",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "id"],
  "properties": {
    "type": {"type": "string", "enum": ["agent", "user"]},
    "id": {"type": "string", "minLength": 1}
  }
}
```

### SourceItem

```json
{
  "$id": "kms.skill.common.source_item",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "value"],
  "properties": {
    "type": {"type": "string", "enum": ["text", "url", "doc_id", "message_id"]},
    "value": {"type": "string", "minLength": 1}
  }
}
```

## 2) Write-Proposal Actions

### ChangeAction.type enum

```json
{
  "enum": [
    "create_task",
    "update_task",
    "append_note",
    "patch_note",
    "upsert_journal_append",
    "link_entities"
  ]
}
```

### patch_note payload (incremental knowledge update)

```json
{
  "$id": "kms.skill.change.patch_note.payload",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["note_id"],
  "properties": {
    "note_id": {"type": "string", "pattern": "^nte_[A-Za-z0-9]+$"},
    "title": {"type": "string", "minLength": 1, "maxLength": 200},
    "body": {"type": "string", "minLength": 1},
    "body_append": {"type": "string", "minLength": 1},
    "topic_id": {"type": "string", "minLength": 1},
    "status": {"type": "string", "enum": ["active", "archived"]},
    "tags": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "source": {"type": "string", "minLength": 1}
  },
  "anyOf": [
    {"required": ["title"]},
    {"required": ["body"]},
    {"required": ["body_append"]},
    {"required": ["topic_id"]},
    {"required": ["status"]},
    {"required": ["tags"]}
  ]
}
```

### upsert_journal_append payload (same-day append)

```json
{
  "$id": "kms.skill.change.upsert_journal_append.payload",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["journal_date", "append_text", "source"],
  "properties": {
    "journal_date": {"type": "string", "format": "date"},
    "append_text": {"type": "string", "minLength": 1},
    "source": {"type": "string", "minLength": 1}
  }
}
```

## 3) Governance Requests

### propose_changes request

```json
{
  "$id": "kms.skill.propose_changes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            "enum": [
              "create_task",
              "update_task",
              "append_note",
              "patch_note",
              "upsert_journal_append",
              "link_entities"
            ]
          },
          "payload": {"type": "object"}
        }
      }
    },
    "actor": {"$ref": "kms.skill.common.actor_ref"},
    "tool": {"type": "string", "minLength": 1}
  }
}
```

### commit_changes request

```json
{
  "$id": "kms.skill.commit_changes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["approved_by"],
  "properties": {
    "approved_by": {"$ref": "kms.skill.common.actor_ref"},
    "client_request_id": {"type": "string", "minLength": 1}
  }
}
```

### reject_changes request

```json
{
  "$id": "kms.skill.reject_changes.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["change_set_id"],
  "properties": {
    "change_set_id": {"type": "string", "pattern": "^chg_[A-Za-z0-9]+$"}
  }
}
```

### undo_last_commit request

```json
{
  "$id": "kms.skill.undo_last_commit.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
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

## 4) Read Actions (Agent Context)

### get_context_bundle request

```json
{
  "$id": "kms.skill.get_context_bundle.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["intent"],
  "properties": {
    "intent": {"type": "string", "minLength": 1},
    "window_days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 14},
    "topic_id": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "include_done": {"type": "boolean", "default": false},
    "tasks_limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
    "notes_limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
    "journals_limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 14}
  }
}
```

### journals upsert/read requests

```json
{
  "$id": "kms.skill.journals.upsert_append.request",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["journal_date", "append_text", "source"],
  "properties": {
    "journal_date": {"type": "string", "format": "date"},
    "append_text": {"type": "string", "minLength": 1},
    "source": {"type": "string", "minLength": 1}
  }
}
```

## 5) Operational Notes

1. Explicit-command mode only.
2. Every write action must carry source refs.
3. Production flow uses DB as sole source of truth (no Obsidian I/O).
4. Default write flow is always `dry-run` then user decision:
   - confirm -> `commit_changes`
   - reject -> `reject_changes`
