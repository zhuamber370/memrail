> Documentation Status: Current
> Last synced: 2026-02-26

# MVP E2E Checklist (Synced 2026-02-26)

## Environment
- API Base: `http://localhost:8000`
- DB: configured via `.env`

## Flow validation
1. Propose changes
- Call `POST /api/v1/changes/dry-run`
- Expect `200`, with `change_set_id` and `diff_items`

2. Reject proposal
- Call `DELETE /api/v1/changes/{id}`
- Expect `200`, status `rejected`
- Re-query `GET /api/v1/changes/{id}`, expect `404`

3. Commit changes
- Dry-run again, then call `POST /api/v1/changes/{id}/commit`
- Expect `200`, status `committed`

4. Audit query
- Call `GET /api/v1/audit/events`
- Expect write events with actor/tool/action/target metadata

5. Undo last
- Call `POST /api/v1/commits/undo-last`
- Expect `200`, status `reverted`

6. Task Command Center (UI)
- Open `/tasks`
- Verify:
  - left filter/search works
  - middle list grouped by status
  - right detail loads selected task
  - execution canvas renders nodes and edges

7. Canvas node operations
- On selected task graph:
  - change node status (`waiting/execute/done`)
  - rename a node
  - delete a non-start node
- Expect graph refresh and no crash

8. Task-scoped helper pages
- Open `/ideas?task_id=<valid_task_id>`
- Expect page loads with task context

9. Frontend routes
- Visit `/tasks`, `/knowledge`, `/changes`
- Expect accessible and interactive pages
- `/audit` should redirect to `/tasks`

## Pass criteria
- All checks pass: MVP is demo-ready
- Any failure: block release until fixed
