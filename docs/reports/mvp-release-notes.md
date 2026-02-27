> Documentation Status: Current
> Last synced: 2026-02-27

# MVP Release Notes (Synced 2026-02-27)

## Delivered
- Backend APIs for `topics/tasks/cycles/notes/knowledge/journals/inbox/links/ideas/routes/changes/context/audit`
- Governed write flow: `dry-run -> commit/reject -> undo-last`
- Audit events with chain metadata (`change_set_id`, `commit_id`, `action_index`)
- Task Command Center UI (desktop-first):
  - search + filter + grouped list + detail in one screen
  - task detail above execution graph
  - route graph relation labels on edges
  - selected-node `...` menu supports:
    - inline add step
    - set status (`waiting/execute/done`)
    - rename
    - delete (leaf node only)
- Knowledge workspace using `/api/v1/knowledge`:
  - category model: `ops_manual | mechanism_spec | decision_record`
  - status model: `active | archived`
  - create/edit/archive/delete in UI
- Changes review page for proposal commit/reject and undo-last
- OpenClaw skill support for read/write governance path
- Additional read exposure for agent retrieval:
  - `GET /api/v1/tasks/{task_id}/sources`
  - `GET /api/v1/notes/{note_id}/sources`
  - `GET /api/v1/journals/{journal_date}/items`
  - `GET /api/v1/inbox`, `GET /api/v1/inbox/{inbox_id}`
  - `GET /api/v1/links`

## Verification snapshot
- Backend:
  - `python3 -m pytest -q backend/tests`
- Frontend:
  - `cd frontend && npm run build`
- Skill:
  - `cd openclaw-skill/kms && node --test index.test.js`

## Known gaps
- No SaaS multi-tenant auth/billing/OAuth yet
- No MCP server yet (REST + skill is current entry)
- Policy-based auto-approval is not implemented
