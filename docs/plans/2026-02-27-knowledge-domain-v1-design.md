> Documentation Status: Historical Snapshot
> Last updated: 2026-02-27
> Note: Superseded by current runtime implementation (knowledge is note-backed in `/api/v1/knowledge`).

# Knowledge Domain V1 Design (Agent-First, Independent Domain)

Date: 2026-02-27  
Status: Historical (superseded design proposal)  
Scope: Knowledge module only (no cross-module orchestration in this version)

## 1. Background

Current knowledge data is mostly in `notes`, with weak structure and low retrieval precision for agent reuse scenarios.  
The product direction for this version is:

1. Move from note-centric storage to structured knowledge storage.
2. Keep human governance (`dry-run -> approve/reject`) for writes.
3. Keep UI manageable and readable while optimizing for agent retrieval.

## 2. Confirmed Decisions

1. Use an independent knowledge domain (not extending `notes` as primary object).
2. Keep exactly three knowledge types:
   - `playbook`
   - `decision`
   - `brief`
3. Search priority is scenario matching first:
   - `type` match
   - `topic`/`tag` match
   - keyword match in title/content
4. UI default is unified list with type filters.
5. Topic is agent-inferred and user-editable.
6. Each knowledge item must include at least one lightweight evidence entry.
7. `notes` data is preserved; migration into new structure will be handled later in controlled batches.
8. Version history is out of scope for V1.

## 3. Architecture Overview

### 3.1 Runtime Components

1. Frontend (Next.js):
   - `/knowledge` becomes the management console for structured knowledge.
2. Backend (FastAPI + service layer):
   - Adds dedicated knowledge routes/services.
3. Database (SQLAlchemy):
   - Adds independent tables for structured knowledge and evidence.

### 3.2 Write Governance

All agent write operations continue to follow the existing governance chain:

1. propose (`dry-run`)
2. human review
3. commit or reject
4. audit trail

V1 only changes the knowledge target domain, not the governance mechanism.

## 4. Database Strategy (Explicit)

### 4.1 Database Type Used in V1

V1 uses **relational database only**.

1. Local/dev default: SQLite (`AFKMS_DB_BACKEND=sqlite`)
2. Optional production deployment: PostgreSQL (`AFKMS_DB_BACKEND=postgres`)

### 4.2 Not Included in V1

The following are explicitly not introduced in this version:

1. Dedicated vector database
2. Dedicated graph database
3. Separate document database

All data remains in the existing relational backend.  
Structured content is represented with relational columns + JSON field (`content_json`).

## 5. Data Model

### 5.1 `knowledge_items`

Core fields:

1. `id` (pk, string)
2. `type` (`playbook|decision|brief`)
3. `title` (string)
4. `topic_id` (fk -> `topics.id`, nullable)
5. `tags_json` (json array)
6. `status` (`active|archived`)
7. `content_json` (json object, type-dependent schema)
8. `created_at`
9. `updated_at`

Type-specific minimum schema in `content_json`:

1. `playbook`:
   - `goal` (string)
   - `steps` (string[])
2. `decision`:
   - `decision` (string)
   - `rationale` (string)
3. `brief`:
   - `summary` (string)
   - `highlights` (string[])

### 5.2 `knowledge_evidences`

Core fields:

1. `id` (pk, string)
2. `item_id` (fk -> `knowledge_items.id`, cascade delete)
3. `source_ref` (string)
4. `excerpt` (text)
5. `created_at`

Hard rule:

1. A knowledge item is valid only if it has at least one evidence record.

## 6. API Design (Agent-First)

### 6.1 Read APIs

1. `GET /api/v1/knowledge`
   - filters: `type`, `topic_id`, `tag`, `q`, `status`
   - pagination supported
2. `GET /api/v1/knowledge/{id}`
3. `GET /api/v1/knowledge/migration/candidates`
   - filters candidate notes not yet migrated
   - pagination supported (`page_size <= 20`)

### 6.2 Write APIs

1. `POST /api/v1/knowledge`
2. `PATCH /api/v1/knowledge/{id}`
3. `POST /api/v1/knowledge/{id}/archive`
4. `POST /api/v1/knowledge/{id}/evidences`
5. `POST /api/v1/knowledge/migration/commit`
   - payload: `note_ids[]`
   - hard limit: max 20 note IDs per batch

Write actions are integrated into existing change governance flow where applicable.

## 7. Retrieval Logic

The retrieval rank order is fixed for V1:

1. exact/strong `type` match
2. `topic_id` + `tags` match
3. keyword match in `title + content_json`
4. recency as tie-breaker

This keeps behavior deterministic and easy to debug for agent workflows.

## 8. UI Design Scope (Knowledge Page)

1. Unified list (default)
2. Filters:
   - type
   - topic
   - tag
   - query
3. Detail panel:
   - typed content view
   - evidence list
4. Create/edit:
   - choose type first
   - dynamic form by type schema

The page is human-usable, but contract and behavior are optimized for agent retrieval.

## 9. Notes Migration Plan (Implemented in V1)

Migration is not auto-run at server startup, but migration tooling is implemented:

1. Keep all existing `notes` unchanged.
2. Generate candidates via `GET /api/v1/knowledge/migration/candidates`.
3. Commit selected candidates via `POST /api/v1/knowledge/migration/commit`.
4. Batch size is hard-limited to 20 notes per request.
5. Inference flow:
   - infer target type (`playbook|decision|brief`)
   - map note `topic_id/tags` directly
   - generate evidence from `note://<note_id>` + note sources + excerpt
6. CLI helper: `backend/scripts/migrate_notes_to_knowledge.py`
   - default: dry-run preview
   - `--apply`: execute batch migration

Goal: all meaningful historical knowledge eventually enters the new structure.

## 10. Non-goals (V1)

1. Knowledge version chain (`knowledge_versions`)
2. Automatic conflict-to-task orchestration
3. Conversation-as-workflow orchestration
4. Multi-agent permission matrix
5. Semantic vector retrieval pipeline

## 11. Risks and Mitigations

1. Risk: type classification errors during migration
   - Mitigation: candidate approval before commit
2. Risk: weak evidence quality
   - Mitigation: enforce `source_ref + excerpt` minimum
3. Risk: user confusion from dual data domains (`notes` + new knowledge)
   - Mitigation: knowledge page reads new domain only; note migration plan documented

## 12. Acceptance Criteria

1. Knowledge module stores and reads from independent knowledge tables.
2. Three knowledge types are enforced in API and UI.
3. Every saved knowledge item has at least one evidence record.
4. Unified list + type filters work in UI.
5. Agent can retrieve by scenario-first matching strategy.
6. Existing `notes` remain intact and queryable for migration.
