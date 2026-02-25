# Route-Graph Task Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver V1 list-first route-graph task management with idea inbox, single-active routes, same-route dependencies, and node-level execution logs.

**Architecture:** Add new backend entities (`ideas`, `routes`, `route_nodes`, `route_edges`, `node_logs`) alongside existing tasks model, expose dedicated APIs, and provide a list-first frontend with a read-only graph preview. Keep existing task flows intact and avoid disruptive migration in V1.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL/SQLite migration via runtime schema bootstrap, Next.js app router, TypeScript.

---

### Task 1: Define Schemas and Persistence Models

**Files:**
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/src/models.py`
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/src/schemas.py`
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/src/db.py`
- Test: `/Users/celastin/Desktop/projects/memrail/backend/tests/test_db_config.py`

**Step 1: Write failing schema/model tests**

Add tests asserting:
- idea status enum values are accepted/rejected correctly
- route status enum values are accepted/rejected correctly
- route-edge rejects cross-route relation in service-level usage (placeholder assertion before service implementation)

**Step 2: Run test to verify failure**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_db_config.py -q`
Expected: FAIL due to missing new models/schemas.

**Step 3: Implement minimal models and schema types**

Add SQLAlchemy models and pydantic contracts for:
- `Idea`
- `Route`
- `RouteNode`
- `RouteEdge`
- `NodeLog`

Add runtime schema bootstrap SQL in `db.py` for both SQLite/Postgres paths.

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_db_config.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/Desktop/projects/memrail add backend/src/models.py backend/src/schemas.py backend/src/db.py backend/tests/test_db_config.py
git -C /Users/celastin/Desktop/projects/memrail commit -m "feat: add route-graph domain models and schemas"
```

### Task 2: Implement Idea and Route Services with State Rules

**Files:**
- Create: `/Users/celastin/Desktop/projects/memrail/backend/src/services/idea_service.py`
- Create: `/Users/celastin/Desktop/projects/memrail/backend/src/services/route_service.py`
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/src/services/__init__.py`
- Test: `/Users/celastin/Desktop/projects/memrail/backend/tests/test_ideas_api.py`
- Test: `/Users/celastin/Desktop/projects/memrail/backend/tests/test_routes_api.py`

**Step 1: Write failing API tests**

Test cases:
- idea state transition happy path (`captured -> triage -> discovery -> ready`)
- invalid transition returns domain error
- only one active route allowed in V1

**Step 2: Run tests to verify failure**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_ideas_api.py backend/tests/test_routes_api.py -q`
Expected: FAIL (missing services/routes).

**Step 3: Implement minimal service logic**

Implement CRUD/list/patch methods with:
- explicit transition maps
- single-active route validation
- audit event writes for mutating operations

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_ideas_api.py backend/tests/test_routes_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/Desktop/projects/memrail add backend/src/services/idea_service.py backend/src/services/route_service.py backend/src/services/__init__.py backend/tests/test_ideas_api.py backend/tests/test_routes_api.py
git -C /Users/celastin/Desktop/projects/memrail commit -m "feat: add idea and route services with lifecycle rules"
```

### Task 3: Implement Route Node, Edge, and Node Log APIs

**Files:**
- Create: `/Users/celastin/Desktop/projects/memrail/backend/src/routes/ideas.py`
- Create: `/Users/celastin/Desktop/projects/memrail/backend/src/routes/routes.py`
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/src/app.py`
- Test: `/Users/celastin/Desktop/projects/memrail/backend/tests/test_route_graph_api.py`

**Step 1: Write failing route graph tests**

Test cases:
- create node under route
- create edge same-route success
- cross-route edge rejected
- append node log and list logs
- promote ready idea to node

**Step 2: Run tests to verify failure**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_route_graph_api.py -q`
Expected: FAIL.

**Step 3: Implement route graph endpoints**

Add endpoints for ideas/routes/nodes/edges/logs and register routers in app.

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest backend/tests/test_route_graph_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/Desktop/projects/memrail add backend/src/routes/ideas.py backend/src/routes/routes.py backend/src/app.py backend/tests/test_route_graph_api.py
git -C /Users/celastin/Desktop/projects/memrail commit -m "feat: add route graph and idea promotion APIs"
```

### Task 4: Build V1 Frontend (List-First + Read-Only Graph)

**Files:**
- Create: `/Users/celastin/Desktop/projects/memrail/frontend/app/ideas/page.tsx`
- Create: `/Users/celastin/Desktop/projects/memrail/frontend/app/routes/page.tsx`
- Create: `/Users/celastin/Desktop/projects/memrail/frontend/src/components/route-graph-preview.tsx`
- Modify: `/Users/celastin/Desktop/projects/memrail/frontend/src/lib/api.ts`
- Modify: `/Users/celastin/Desktop/projects/memrail/frontend/src/components/shell.tsx`
- Test: `/Users/celastin/Desktop/projects/memrail/frontend/app/routes/page.tsx` (basic render/state handling)

**Step 1: Write failing UI expectations**

Define minimal UI checks (manual + typed assertions):
- Ideas page renders state columns and transition actions.
- Routes page renders route list and node list.
- Graph preview reflects node-edge API payload in read-only mode.

**Step 2: Run build to verify current failure/gaps**

Run: `cd /Users/celastin/Desktop/projects/memrail/frontend && npm run build`
Expected: FAIL or missing page references before implementation.

**Step 3: Implement minimal pages/components**

- Add ideas and routes pages.
- Add API client functions for new endpoints.
- Add read-only graph preview component (no drag/drop in V1).

**Step 4: Run build to verify pass**

Run: `cd /Users/celastin/Desktop/projects/memrail/frontend && npm run build`
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/Desktop/projects/memrail add frontend/app/ideas/page.tsx frontend/app/routes/page.tsx frontend/src/components/route-graph-preview.tsx frontend/src/lib/api.ts frontend/src/components/shell.tsx
git -C /Users/celastin/Desktop/projects/memrail commit -m "feat: add list-first ideas and routes UI with graph preview"
```

### Task 5: Docs, Contract Examples, and End-to-End Verification

**Files:**
- Modify: `/Users/celastin/Desktop/projects/memrail/README.md`
- Modify: `/Users/celastin/Desktop/projects/memrail/backend/README.md`
- Create: `/Users/celastin/Desktop/projects/memrail/docs/reports/2026-02-25-route-graph-v1-smoke.md`

**Step 1: Write failing smoke checklist**

Prepare manual checklist for:
- idea capture to ready
- promote idea to route node
- route activation enforcement
- node log append and retrieval

**Step 2: Run full verification before docs claim completion**

Run:
- `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest -q`
- `cd /Users/celastin/Desktop/projects/memrail/frontend && npm run build`

Expected: all pass.

**Step 3: Update docs with new workflow**

Add quickstart instructions and API examples for ideas/routes/graph endpoints.

**Step 4: Record smoke results**

Write report to `docs/reports/2026-02-25-route-graph-v1-smoke.md` with command outputs and screenshots references.

**Step 5: Commit**

```bash
git -C /Users/celastin/Desktop/projects/memrail add README.md backend/README.md docs/reports/2026-02-25-route-graph-v1-smoke.md
git -C /Users/celastin/Desktop/projects/memrail commit -m "docs: add route-graph v1 workflow and verification report"
```

### Task 6: Final Integration Gate

**Files:**
- No new files required

**Step 1: Re-run release gate verification**

Run:
- `cd /Users/celastin/Desktop/projects/memrail/backend && python3 -m pytest -q`
- `cd /Users/celastin/Desktop/projects/memrail/frontend && npm run build`

**Step 2: Validate CI workflow coverage**

Run:
- `gh run list --repo zhuamber370/memrail --limit 5`

Expected: latest run green for `backend` and `frontend` contexts.

**Step 3: Produce rollout note**

Document V2 backlog items:
- multi-active routes
- agent executor support
- graph-first default UI
- in-canvas editing

**Step 4: Commit final integration notes (if changed)**

```bash
git -C /Users/celastin/Desktop/projects/memrail commit -m "chore: finalize route-graph v1 integration" || true
```
