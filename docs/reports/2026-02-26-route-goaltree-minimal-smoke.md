> Documentation Status: Current
> Last synced: 2026-02-26

# Route-GoalTree Minimal Smoke Report

Date: 2026-02-26  
Branch: `codex/route-goaltree-v1`

## Scope

Validate minimal Route-GoalTree extension:
- route hierarchy fields: `parent_route_id`, `spawned_from_node_id`
- node hierarchy fields: `parent_node_id`, `refinement_status`
- typed node logs: `log_type`, `source_ref`
- hierarchy guardrails: spawn node type check, same-route parent check, cycle prevention

## Commands and Results

1. Route/Idea targeted backend tests

Command:
```bash
cd backend
python3 -m pytest tests/test_routes_api.py tests/test_ideas_api.py -q
```

Result:
- `12 passed in 1.40s`

2. Frontend production build

Command:
```bash
cd frontend
npm run build
```

Result:
- Next.js build succeeded
- `/routes` page compiled and prerendered

3. Backend full test gate

Command:
```bash
cd backend
python3 -m pytest -q
```

Result:
- `71 passed, 4 failed`
- Failures concentrated in `tests/test_changes_api.py`:
  - SQLite-incompatible `TRUNCATE TABLE commits`
  - undo/JSON behavior assertions in change-set revert flows

Interpretation:
- Route-GoalTree changes are validated by targeted suites and frontend build.
- Full backend suite in local SQLite mode currently contains pre-existing/non-route blockers in change governance tests.

## New/Updated Error Codes Verified

- `ROUTE_SPAWN_NODE_NOT_DECISION`
- `ROUTE_NODE_PARENT_CROSS_ROUTE`
- `ROUTE_NODE_PARENT_CYCLE`
- `ROUTE_PARENT_REWIRE_FORBIDDEN`

## Conclusion

- Route-GoalTree minimal feature set is implemented and validated on targeted checks.
- Release gate for full backend suite remains blocked by non-route change-governance tests under local SQLite environment.
