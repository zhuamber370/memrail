> Documentation Status: Current
> Last synced: 2026-03-01

# MVP Release Notes (Synced 2026-03-01)

## Delivered
- Backend APIs for `topics/tasks/cycles/notes/knowledge/journals/inbox/links/ideas/routes/changes/context/audit`
- Governed write flow: `dry-run -> commit/reject -> undo-last`
- Audit events with chain metadata (`change_set_id`, `commit_id`, `action_index`)
- DAG execution graph logging upgrade:
  - unified `entity_logs` model for node/edge execution logs
  - node + edge log CRUD API exposure under `/api/v1/routes/{route_id}/.../logs`
  - `/api/v1/routes/{route_id}/graph` includes node/edge `has_logs` for badge rendering
- Task Command Center UI (desktop-first):
  - search + filter + grouped list + detail in one screen
  - task detail above execution graph
  - route graph keeps pure edge connections without relation labels
  - DAG auto-layout migrated to `@dagrejs/dagre` layered engine for more stable branch alignment
  - selected-node `...` menu supports:
    - inline add step
    - set status (`waiting/execute/done`)
    - rename
    - delete (leaf node only)
  - task execution panel simplification:
    - add-step inline form now keeps only title + status
    - edge relation selection/edge inspector entry removed
    - edge line keeps pure connection display only
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
- Idea route-node creation now only emits `goal` type for execution DAG initialization.

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
