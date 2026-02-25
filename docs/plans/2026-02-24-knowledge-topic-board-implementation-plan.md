> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# Knowledge Topic Board Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a human-first Knowledge module with Topic-grouped browsing, unclassified workflow, and body-first detail view, based on current note data.

**Architecture:** Extend existing `notes` domain with `topic_id` and `status`, then expand note APIs for filtering/classification/summary. Rebuild `/knowledge` into a three-column UI (topic nav, note list, note detail), defaulting to Topic view and supporting unclassified bulk classify.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, PostgreSQL, Next.js App Router, TypeScript.

---

### Task 1: Lock backend behavior with failing API tests

**Files:**
- Modify: `backend/tests/test_inbox_notes_api.py`
- Modify: `backend/tests/helpers.py` (only if helper needed)

**Step 1: Write failing tests for new note behavior**

```python
def test_search_notes_supports_unclassified_filter():
    # create note A with topic_id, note B without topic_id
    # GET /api/v1/notes/search?unclassified=true
    # assert only note B appears

def test_patch_note_can_set_topic_and_archive():
    # PATCH /api/v1/notes/{id} with topic_id and status=archived
    # assert fields updated and hidden from default active list

def test_topic_summary_returns_unclassified_count():
    # GET /api/v1/notes/topic-summary
    # assert includes unclassified and fixed topic counters
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_inbox_notes_api.py -q`  
Expected: FAIL (missing endpoints/fields/filters)

**Step 3: Commit test-only changes**

```bash
git add backend/tests/test_inbox_notes_api.py
git commit -m "test: define knowledge topic-board backend behavior"
```

### Task 2: Add schema/model/database support for note topic + status

**Files:**
- Modify: `backend/src/models.py`
- Modify: `backend/src/schemas.py`
- Modify: `backend/src/db.py`
- Modify: `backend/db/schema.sql`
- Modify: `backend/db/migrations/002_agent_first_governance.sql`

**Step 1: Add failing migration check (manual)**

Run:
```bash
python3 backend/scripts/check_db_connection.py
```
Expected: DB reachable before altering runtime schema.

**Step 2: Implement minimal model/schema changes**

```python
# models.py (Note)
topic_id = mapped_column(String(40), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
status = mapped_column(String(20), nullable=False, default="active")

# schemas.py
class NotePatch(BaseModel): ...
class NoteTopicSummaryOut(BaseModel): ...
```

**Step 3: Add runtime SQL/migration SQL**

```sql
ALTER TABLE notes ADD COLUMN IF NOT EXISTS topic_id VARCHAR(40);
ALTER TABLE notes ADD COLUMN IF NOT EXISTS status VARCHAR(20);
UPDATE notes SET status='active' WHERE status IS NULL;
```

**Step 4: Run backend note tests**

Run: `python3 -m pytest backend/tests/test_inbox_notes_api.py -q`  
Expected: still FAIL (service/route not yet completed), but no schema/runtime crash.

**Step 5: Commit**

```bash
git add backend/src/models.py backend/src/schemas.py backend/src/db.py backend/db/schema.sql backend/db/migrations/002_agent_first_governance.sql
git commit -m "feat: add note topic and status schema foundation"
```

### Task 3: Implement note service methods for search/patch/batch classify/summary

**Files:**
- Modify: `backend/src/services/note_service.py`

**Step 1: Implement query filters in `search`**

```python
def search(..., topic_id=None, unclassified=False, status="active", q=None, tag=None):
    # status filter
    # topic filter / unclassified filter
    # q over title/body
    # tag over tags_json
```

**Step 2: Implement patch + batch classify + summary**

```python
def patch(note_id: str, payload: NotePatch): ...
def batch_classify(note_ids: list[str], topic_id: str) -> dict: ...
def topic_summary(status: str = "active") -> list[dict]: ...
```

**Step 3: Run tests**

Run: `python3 -m pytest backend/tests/test_inbox_notes_api.py -q`  
Expected: fewer failures; may still fail until routes are wired.

**Step 4: Commit**

```bash
git add backend/src/services/note_service.py
git commit -m "feat: implement knowledge note classification service"
```

### Task 4: Expose new note routes and request/response contracts

**Files:**
- Modify: `backend/src/routes/notes.py`
- Modify: `backend/src/schemas.py`

**Step 1: Add endpoints**

```python
@router.patch("/{note_id}")
@router.post("/batch-classify")
@router.get("/topic-summary")
```

**Step 2: Add request/response schemas**

```python
class NoteBatchClassifyIn(BaseModel): ...
class NoteBatchClassifyOut(BaseModel): ...
class NoteTopicSummaryItem(BaseModel): ...
```

**Step 3: Run backend suite**

Run:
```bash
python3 -m pytest backend/tests/test_inbox_notes_api.py backend/tests/test_links_api.py backend/tests/test_audit_api.py -q
```
Expected: PASS

**Step 4: Commit**

```bash
git add backend/src/routes/notes.py backend/src/schemas.py
git commit -m "feat: add knowledge note patch/classify/summary APIs"
```

### Task 5: Rebuild Knowledge page into three-column Topic Board

**Files:**
- Modify: `frontend/app/knowledge/page.tsx`
- Modify: `frontend/src/i18n.tsx`
- Modify: `frontend/app/globals.css`

**Step 1: Add page state/data contract**

```ts
type TopicSummaryItem = { topic_id: string | null; topic_name: string; count: number };
type NoteItem = { id: string; title: string; tags: string[]; source_count: number; updated_at: string; topic_id?: string | null; status: "active" | "archived" };
```

**Step 2: Implement three-column layout**
- Left: topic list + unclassified
- Middle: note cards (title/tags/source_count/updated_at)
- Right: body-first detail

**Step 3: Implement behaviors**
- default Topic-grouped load
- unclassified view bulk-select + batch classify
- archived view read-only

**Step 4: Add i18n keys**
- knowledge topic labels, unclassified, archived, batch classify, read-only hints

**Step 5: Run frontend build**

Run: `npm run -s build` (in `frontend`)  
Expected: PASS

**Step 6: Commit**

```bash
git add frontend/app/knowledge/page.tsx frontend/src/i18n.tsx frontend/app/globals.css
git commit -m "feat: redesign knowledge page as topic board"
```

### Task 6: Migration pass for current notes (safe and auditable)

**Files:**
- Create: `backend/scripts/migrate_notes_topic_status.py`

**Step 1: Implement dry-safe script**
- map notes via `note-task link -> task.topic_id`
- set unresolved to `topic_id = null`
- archive noisy placeholders (`title='N'` and tiny body)
- print counts only; no secret output

**Step 2: Run script**

Run: `python3 backend/scripts/migrate_notes_topic_status.py`  
Expected: printed counters for mapped/unclassified/archived_noise

**Step 3: Verify with read-only SQL check**

Run:
```bash
python3 - <<'PY'
import os
import psycopg
conn=psycopg.connect(
    host=os.getenv("AFKMS_DB_HOST", "127.0.0.1"),
    port=int(os.getenv("AFKMS_DB_PORT", "5432")),
    user=os.getenv("AFKMS_DB_USER", "afkms"),
    password=os.getenv("AFKMS_DB_PASSWORD", ""),
    dbname=os.getenv("AFKMS_DB_NAME", "afkms"),
)
cur=conn.cursor()
cur.execute("select status,count(*) from notes group by status order by status")
print(cur.fetchall())
cur.close(); conn.close()
PY
```

Expected: `active` + optional `archived` counts align with script output.

**Step 4: Commit**

```bash
git add backend/scripts/migrate_notes_topic_status.py
git commit -m "chore: add note topic/status migration utility"
```

### Task 7: Regression verification + docs sync

**Files:**
- Modify: `docs/plans/2026-02-21-agent-first-kms-prd-api.md`
- Modify: `docs/plans/2026-02-21-agent-first-kms-final-system-design.md`
- Modify: `docs/plans/2026-02-21-agent-first-kms-implementation-input-pack.md`

**Step 1: Run backend regression**

Run:
```bash
python3 -m pytest backend/tests/test_tasks_api.py backend/tests/test_inbox_notes_api.py backend/tests/test_links_api.py backend/tests/test_audit_api.py -q
```
Expected: PASS

**Step 2: Run frontend regression**

Run: `npm run -s build` (in `frontend`)  
Expected: PASS

**Step 3: Sync docs to final behavior**
- note topic/status model
- new knowledge endpoints
- human-first UI and unclassified flow

**Step 4: Commit**

```bash
git add docs/plans/2026-02-21-agent-first-kms-prd-api.md docs/plans/2026-02-21-agent-first-kms-final-system-design.md docs/plans/2026-02-21-agent-first-kms-implementation-input-pack.md
git commit -m "docs: sync knowledge topic-board behavior"
```

## Implementation Notes

1. Use `@test-driven-development` for backend behavior changes.
2. Use `@frontend-design` for knowledge page visual/interaction quality.
3. Run `@verification-before-completion` before claiming done.
4. Keep diffs small and reviewable; do not refactor unrelated modules.
5. Clean test data after verification using existing cleanup script if needed.
