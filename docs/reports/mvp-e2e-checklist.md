> Documentation Status: Current
> Last synced: 2026-02-27

# MVP E2E Checklist (Synced 2026-02-27)

## Environment
- API Base: `http://localhost:8000`
- DB: configured via `.env`

## Flow validation
1. Propose changes
- Call `POST /api/v1/changes/dry-run`
- Include at least one action, e.g. `capture_inbox` or `create_route_node`
- Expect `200` with `change_set_id`, `summary`, `diff_items`

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

6. Knowledge API smoke
- `POST /api/v1/knowledge`
- `GET /api/v1/knowledge`
- `PATCH /api/v1/knowledge/{id}`
- `POST /api/v1/knowledge/{id}/archive`
- `DELETE /api/v1/knowledge/{id}`
- Expect category/status behavior: `ops_manual|mechanism_spec|decision_record`, `active|archived`

7. Agent-read exposure smoke
- `GET /api/v1/inbox`
- `GET /api/v1/links`
- `GET /api/v1/tasks/{task_id}/sources`
- `GET /api/v1/notes/{note_id}/sources`
- `GET /api/v1/journals/{journal_date}/items`
- Expect `200` and typed list payloads

8. Task Command Center (UI)
- Open `/tasks`
- Verify:
  - left filter/search works
  - middle list grouped by status
  - task detail renders above graph
  - graph renders nodes/edges/relation labels

9. Canvas node operations
- On selected task graph:
  - click node and open `...` menu
  - use `Set Status` to `waiting/execute/done`
  - use `+ Add Step`
  - rename a node
  - verify delete only works for leaf non-start node
- Expect graph refresh and no crash

10. Frontend routes
- Visit `/tasks`, `/knowledge`, `/changes`
- Expect pages accessible and interactive
- `/audit` should redirect to `/tasks`

## Pass criteria
- All checks pass: MVP is demo-ready
- Any failure: block release until fixed
