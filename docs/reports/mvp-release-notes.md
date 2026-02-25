# MVP Release Notes (Synced 2026-02-25)

## Delivered
- Backend APIs for `topics/tasks/notes/journals/links/changes/context/audit`
- Governed write flow: `dry-run -> commit/reject -> undo-last`
- Audit events with chain metadata (`change_set_id`, `commit_id`, `action_index`)
- Task domain with fixed topic classification, cancel-reason guard, archive semantics
- Knowledge Topic Board with unclassified handling, classify/edit/archive operations
- Changes proposal inbox for human review and direct commit/reject
- OpenClaw skill support including `reject_changes`
- Bilingual UI (English default, Chinese switch)
- Audit UI hidden from navigation; `/audit` now redirects to `/tasks`

## Verification snapshot
- Backend:
  - `python3 -m pytest backend/tests/test_changes_api.py -q`
- Frontend:
  - `cd frontend && npm run build`

## Known gaps
- No SaaS multi-tenant auth/billing/OAuth yet
- No MCP server yet (REST + skill is current entry)
- Policy-based auto-approval is not implemented
