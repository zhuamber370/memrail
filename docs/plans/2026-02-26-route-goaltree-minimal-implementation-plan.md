# Route-GoalTree Minimal (Option A) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add minimal dual-track lifecycle support by extending route/node/log models for nested decomposition, route branching ancestry, and structured knowledge capture.

**Architecture:** Keep existing `Route + RouteNode + RouteEdge + NodeLog` APIs intact, extend contracts with optional fields, and enforce constraints in service layer. Preserve backward compatibility by adding nullable columns/defaults and validating only when new fields are used.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, PostgreSQL/SQLite runtime schema bootstrap, Next.js (App Router), TypeScript.

---

### Task 1: Extend Persistence and API Schemas for Optional New Fields

**Files:**
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/tests/test_routes_api.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/models.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/schemas.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/db.py`

**Step 1: Write failing API contract tests for new optional fields**

```python
def test_route_create_accepts_parent_fields():
    created = client.post("/api/v1/routes", json={
        "task_id": task_id,
        "name": "child route",
        "status": "candidate",
        "parent_route_id": parent_id,
        "spawned_from_node_id": decision_node_id,
    })
    assert created.status_code == 201
```

```python
def test_route_node_create_accepts_parent_and_refinement():
    created = client.post(f"/api/v1/routes/{route_id}/nodes", json={
        "node_type": "goal",
        "title": "Goal A",
        "parent_node_id": root_id,
        "refinement_status": "exploring",
    })
    assert created.status_code == 201
```

**Step 2: Run tests to verify failure**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py::test_route_create_accepts_parent_fields tests/test_routes_api.py::test_route_node_create_accepts_parent_and_refinement -q`  
Expected: FAIL (schema rejects unknown fields or response missing fields).

**Step 3: Implement minimal model/schema/runtime-schema support**

```python
# models.py
class Route(Base):
    parent_route_id = mapped_column(String(40), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    spawned_from_node_id = mapped_column(String(40), ForeignKey("route_nodes.id", ondelete="SET NULL"), nullable=True)

class RouteNode(Base):
    parent_node_id = mapped_column(String(40), ForeignKey("route_nodes.id", ondelete="SET NULL"), nullable=True)
    refinement_status = mapped_column(String(20), nullable=False, default="rough")

class NodeLog(Base):
    log_type = mapped_column(String(20), nullable=False, default="note")
    source_ref = mapped_column(Text, nullable=True)
```

```python
# schemas.py
RouteRefinementStatus = Literal["rough", "exploring", "decided", "decomposed"]
NodeLogType = Literal["note", "evidence", "decision", "summary"]
```

```python
# db.py sqlite + postgres runtime add-column hooks
ALTER TABLE routes ADD COLUMN IF NOT EXISTS parent_route_id VARCHAR(40);
ALTER TABLE routes ADD COLUMN IF NOT EXISTS spawned_from_node_id VARCHAR(40);
ALTER TABLE route_nodes ADD COLUMN IF NOT EXISTS parent_node_id VARCHAR(40);
ALTER TABLE route_nodes ADD COLUMN IF NOT EXISTS refinement_status VARCHAR(20);
ALTER TABLE node_logs ADD COLUMN IF NOT EXISTS log_type VARCHAR(20);
ALTER TABLE node_logs ADD COLUMN IF NOT EXISTS source_ref TEXT;
```

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py::test_route_create_accepts_parent_fields tests/test_routes_api.py::test_route_node_create_accepts_parent_and_refinement -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 add \
  backend/src/models.py \
  backend/src/schemas.py \
  backend/src/db.py \
  backend/tests/test_routes_api.py
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 commit -m "feat: extend route graph schemas for hierarchy and typed logs"
```

### Task 2: Add Route/Node Validation Rules for Hierarchy Safety

**Files:**
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/tests/test_routes_api.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/services/route_service.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/routes/routes.py`

**Step 1: Write failing behavior tests**

```python
def test_spawned_from_node_must_be_decision():
    res = client.post("/api/v1/routes", json={..., "spawned_from_node_id": task_node_id})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ROUTE_SPAWN_NODE_NOT_DECISION"
```

```python
def test_parent_node_must_be_same_route_and_acyclic():
    cross = client.post(f"/api/v1/routes/{route1}/nodes", json={..., "parent_node_id": route2_node})
    assert cross.status_code == 409
    assert cross.json()["error"]["code"] == "ROUTE_NODE_PARENT_CROSS_ROUTE"
```

```python
def test_parent_route_rewire_forbidden_when_non_candidate():
    res = client.patch(f"/api/v1/routes/{active_route}", json={"parent_route_id": other_id})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ROUTE_PARENT_REWIRE_FORBIDDEN"
```

**Step 2: Run tests to verify failure**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py -k "spawned_from_node or parent_node or parent_route_rewire" -q`  
Expected: FAIL.

**Step 3: Implement minimal validation in service layer**

```python
def _validate_spawn_node(self, route_task_id: str, spawned_from_node_id: str) -> None:
    node = self.db.get(RouteNode, spawned_from_node_id)
    if node is None:
        raise ValueError("ROUTE_SPAWN_NODE_NOT_FOUND")
    if node.node_type != "decision":
        raise ValueError("ROUTE_SPAWN_NODE_NOT_DECISION")
```

```python
def _ensure_parent_node_valid(self, route_id: str, parent_node_id: str, node_id: str | None = None) -> None:
    # same-route + no cycle
    ...
    raise ValueError("ROUTE_NODE_PARENT_CYCLE")
```

```python
# routes.py
if code in {"ROUTE_NODE_PARENT_CROSS_ROUTE", "ROUTE_NODE_PARENT_CYCLE", "ROUTE_PARENT_REWIRE_FORBIDDEN"}:
    status_code = 409
```

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py -k "spawned_from_node or parent_node or parent_route_rewire" -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 add \
  backend/src/services/route_service.py \
  backend/src/routes/routes.py \
  backend/tests/test_routes_api.py
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 commit -m "feat: enforce route hierarchy and node tree validation rules"
```

### Task 3: Add Typed Node Log Semantics and Response Coverage

**Files:**
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/tests/test_routes_api.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/services/route_service.py`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/src/schemas.py`

**Step 1: Write failing tests for `log_type` and `source_ref`**

```python
def test_append_typed_node_log():
    appended = client.post(f"/api/v1/routes/{route_id}/nodes/{node_id}/logs", json={
        "content": "benchmark report",
        "log_type": "evidence",
        "source_ref": "https://example.com/report",
        "actor_type": "human",
        "actor_id": "tester",
    })
    assert appended.status_code == 201
    assert appended.json()["log_type"] == "evidence"
```

**Step 2: Run tests to verify failure**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py::test_append_typed_node_log -q`  
Expected: FAIL (`log_type`/`source_ref` not accepted or not returned).

**Step 3: Implement minimal log extension**

```python
log = NodeLog(
    ...,
    content=payload.content,
    log_type=payload.log_type,
    source_ref=payload.source_ref,
)
```

```python
class NodeLogCreate(BaseModel):
    content: str
    log_type: NodeLogType = "note"
    source_ref: Optional[str] = None
```

**Step 4: Run tests to verify pass**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest tests/test_routes_api.py::test_append_typed_node_log -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 add \
  backend/src/services/route_service.py \
  backend/src/schemas.py \
  backend/tests/test_routes_api.py
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 commit -m "feat: support typed node logs with source references"
```

### Task 4: Update Frontend Route Workspace for New Optional Fields

**Files:**
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend/app/routes/page.tsx`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend/src/components/route-graph-preview.tsx`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend/src/i18n.tsx`

**Step 1: Add failing type/build expectations**

Add TS usage for new fields so build fails until types are updated:

```tsx
type Route = { parent_route_id: string | null; spawned_from_node_id: string | null; ... };
type RouteGraphNode = { parent_node_id: string | null; refinement_status: "rough" | "exploring" | "decided" | "decomposed"; ... };
```

**Step 2: Run build to verify failure**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend && npm run build`  
Expected: FAIL until UI wiring and i18n keys are complete.

**Step 3: Implement minimal UI wiring**

```tsx
// route create payload
await apiPost("/api/v1/routes", {
  ...,
  parent_route_id: parentRouteId || null,
  spawned_from_node_id: spawnedFromNodeId || null,
});
```

```tsx
// node create payload
await apiPost(`/api/v1/routes/${selectedRoute.id}/nodes`, {
  ...,
  parent_node_id: parentNodeId || null,
  refinement_status: refinementStatus,
});
```

Show in detail/preview:
- parent/child route badges
- node `refinement_status` badge
- parent node title chip when present

**Step 4: Run build to verify pass**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend && npm run build`  
Expected: PASS.

**Step 5: Commit**

```bash
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 add \
  frontend/app/routes/page.tsx \
  frontend/src/components/route-graph-preview.tsx \
  frontend/src/i18n.tsx
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 commit -m "feat: expose route hierarchy and node refinement fields in routes UI"
```

### Task 5: End-to-End Verification and Documentation Sync

**Files:**
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend/README.md`
- Modify: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/README.md`
- Create: `/Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/docs/reports/2026-02-26-route-goaltree-minimal-smoke.md`

**Step 1: Write smoke checklist with expected behavior**

Checklist items:
- create parent route and child route
- create rough goal and decompose with child nodes
- reject cross-route parent node
- reject cycle parent relationship
- append evidence log with `source_ref`

**Step 2: Run backend test suite**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/backend && python3 -m pytest -q`  
Expected: PASS.

**Step 3: Run frontend build**

Run: `cd /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1/frontend && npm run build`  
Expected: PASS.

**Step 4: Update docs and record outputs**

Document:
- new optional API fields
- validation error codes
- smoke command outputs

**Step 5: Commit**

```bash
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 add \
  README.md \
  backend/README.md \
  docs/reports/2026-02-26-route-goaltree-minimal-smoke.md
git -C /Users/celastin/.config/superpowers/worktrees/memrail/codex-route-goaltree-v1 commit -m "docs: add route-goaltree minimal rollout and smoke report"
```
