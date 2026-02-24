# Knowledge Topic Board Design (v1)

Date: 2026-02-24
Status: Confirmed
Scope: Knowledge module redesign (human-facing UI only)

## 1. Context

Current Knowledge page is not usable for human review:
- UI is raw input + JSON dump, no clear information architecture.
- Existing knowledge content is present, but hard to browse and maintain.
- Topic taxonomy already exists and is fixed (7 categories).

Validated baseline (2026-02-24):
- Obsidian markdown files: 46 total, 33 under `Topics/`.
- Current DB `notes`: 17.
- From cleaned migration pack: 14 notes.
- Additional noisy records: 3 notes (`title='N'`, body length=1).

## 2. Product Goal

Build a human-first Knowledge workspace that allows:
1. Fast browsing by Topic.
2. Efficient cleanup/classification of unclassified notes.
3. Readable detail view focused on note body.

Agent usage remains API/MCP-based and is not a UI design target.

## 3. Confirmed Boundaries

1. UI is for humans only.
2. Primary object remains `note` (not replacing with new terminology).
3. Default entry is Topic-based browsing.
4. Unclassified notes are visible in a dedicated group.
5. Note-task relation is optional (not required).
6. Creating note without topic is allowed.

## 4. Non-Goals

1. Knowledge graph visualization.
2. Automatic intelligent classification loop.
3. Rich-text editor overhaul.
4. Agent orchestration flows in UI.

## 5. Information Architecture

Three-column layout:
1. Left: Topic navigation
2. Middle: Note list
3. Right: Note detail

Groups in left column:
- 7 fixed topics from taxonomy
- `Unclassified` (notes with `topic_id = null`)

Default behavior:
- Open page with Topic mode.
- Auto-select first non-empty group.

## 6. UI Behavior

### 6.1 Topic Navigation (Left)
- Show each topic and note count.
- Show unclassified count.
- Click to filter middle list.

### 6.2 Note List (Middle)
- Card fields: `title + tags + source_count + updated_at`
- Search input and tag filter.
- In `Unclassified` view: enable multi-select + bulk classify action.

### 6.3 Note Detail (Right)
- Body-first presentation by default.
- Secondary sections below body:
  - sources
  - linked tasks
  - linked notes

Archived view behavior:
- read-only only (view, no edit/batch write actions).

## 7. Data Model Changes (Minimal)

Extend `notes`:
1. `topic_id` nullable FK to `topics.id`
2. `status` with values `active | archived` (default `active`)

Keep existing:
- `tags_json`
- `note_sources` (source required)
- `links`

## 8. API Changes

### 8.1 Existing endpoint extensions
- `GET /api/v1/notes/search`
  - add query: `topic_id`, `unclassified=true`, `status`, `q`, `tag`
  - default: `status=active`

- `PATCH /api/v1/notes/{note_id}`
  - editable fields: `title, body, tags, topic_id, status`

### 8.2 New endpoints
- `POST /api/v1/notes/batch-classify`
  - request: `{ note_ids: string[], topic_id: string }`
  - behavior: assign selected notes to one topic

- `GET /api/v1/notes/topic-summary`
  - returns counts by topic + unclassified

## 9. Migration Rules (From Current Data)

1. If note can map through `note -> task -> topic`, backfill `notes.topic_id`.
2. If no map exists, keep `topic_id = null` (Unclassified).
3. Noisy placeholder notes (`title='N'` and tiny body) set to `status='archived'`.
4. All migration writes produce audit events.

## 10. Governance Rules

1. Note creation requires at least one source.
2. Topic assignment for note is optional.
3. Note-task relation is optional.
4. Archived notes hidden by default and visible via archived filter.
5. Archived view is read-only in UI.

## 11. Acceptance Criteria

1. Knowledge page defaults to Topic grouped view.
2. Left column includes fixed topics and Unclassified with counts.
3. List cards show exactly: title, tags, source count, updated time.
4. Note detail is body-first.
5. New note without topic appears in Unclassified.
6. Bulk classify works in Unclassified view.
7. Archived notes are hidden by default and queryable.
8. Task module behavior remains unchanged.

## 12. Risks

1. Historical notes without links may require manual classification.
2. Noise identification is rule-based and may need manual review.
3. Without automatic classification, cleanup relies on user workflow.

## 13. Rollout

1. Deliver backend schema + note APIs first.
2. Deliver three-column Knowledge UI second.
3. Run one migration pass for current note set.
4. Validate with manual UAT on Topic browsing and Unclassified cleanup.
