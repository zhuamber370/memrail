> Documentation Status: Current
> Last synced: 2026-02-26

# MVP Release Notes (Synced 2026-02-26)

## Delivered
- Backend APIs for `topics/tasks/notes/journals/links/changes/context/audit/ideas/routes`
- Governed write flow: `dry-run -> commit/reject -> undo-last`
- Audit events with chain metadata (`change_set_id`, `commit_id`, `action_index`)
- Task domain with fixed topic classification, cancel-reason guard, archive semantics
- Task Command Center UI (desktop-first):
  - search + filter + grouped list + detail in one screen
  - execution canvas with idea-goal flow graph
  - node status change (`waiting/execute/done`), rename, delete
- Knowledge Topic Board with classify/edit/archive operations
- Changes proposal inbox for human review and direct commit/reject
- OpenClaw skill support including `reject_changes`
- Bilingual UI (English / Chinese)
- Audit UI hidden from navigation; `/audit` redirects to `/tasks`

## Verification snapshot
- Backend:
  - `python3 -m pytest -q`
- Frontend:
  - `cd frontend && npm run build`

## Known gaps
- No SaaS multi-tenant auth/billing/OAuth yet
- No MCP server yet (REST + skill is current entry)
- Policy-based auto-approval is not implemented
