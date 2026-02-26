> Documentation Status: Proposed
> Last synced: 2026-02-26

# Memrail Route-GoalTree Minimal Design (Option A)

Date: 2026-02-26  
Status: Proposed  
Scope: Minimal extension on top of existing Route-Graph V1

## 1. Context

Current Route-Graph V1 already supports:
- `Route` as strategy line
- `RouteNode` + `RouteEdge` as executable DAG
- `NodeLog` for node-level timeline

Current gap:
- Top-level goals are often rough at creation time.
- During discovery and decision, one rough goal may split into nested goals.
- Strategy branching and execution decomposition are both needed, but they are different concepts.
- Valuable process information (evidence, decisions, summaries) needs stronger structure.

## 2. Design Decision

Adopt a **dual-track expression** with minimal schema changes:
- Strategy branching remains centered on `Route` (line-level lifecycle).
- Execution decomposition becomes a tree inside route nodes (node-level lifecycle).

Use Option A (minimal incremental path) before larger refactors.

## 3. Alternatives Considered

### Option A (recommended for now): Minimal incremental
- Add parent relations and refinement metadata to existing entities.
- Keep existing APIs and state machines mostly intact.
- Add typed node logs for knowledge capture.

Pros:
- Fastest path with low migration risk.
- Preserves current Route-Graph V1 mental model.
- Compatible with future deeper redesign.

Cons:
- Concept boundaries are improved but still shared in existing entities.

### Option B: Mid-level redesign
- Route branching + node tree + richer orchestration rules in one phase.

Pros:
- Cleaner semantics earlier.

Cons:
- Higher migration and delivery risk.

### Option C: Full model split
- Introduce first-class `Goal`, `Evidence`, `Decision` entities immediately.

Pros:
- Strong long-term model purity.

Cons:
- Too disruptive for near-term delivery.

## 4. Minimal Data Model Changes

### 4.1 Routes

Add fields:
- `parent_route_id` (nullable FK -> `routes.id`)
- `spawned_from_node_id` (nullable FK -> `route_nodes.id`)

Meaning:
- `parent_route_id`: strategy line ancestry.
- `spawned_from_node_id`: this route is spawned from a decision node.

### 4.2 Route Nodes

Add fields:
- `parent_node_id` (nullable FK -> `route_nodes.id`)
- `refinement_status` (`rough|exploring|decided|decomposed`, default `rough`)

Current `node_type` enum already includes:
- `start|goal|idea|decision|milestone|task`

Meaning:
- `goal` node captures a rough target first.
- children under `goal` represent decomposition results.

### 4.3 Node Logs

Add fields:
- `log_type` (`note|evidence|decision|summary`, default `note`)
- `source_ref` (nullable text)

Meaning:
- evidence/decision/summary are first-class log categories.
- `source_ref` records external references for traceability.

## 5. State Model (Dual Track)

### 5.1 Route lifecycle (strategy track)

Keep existing transition rules:
- `candidate -> active|parked|cancelled`
- `active -> parked|completed|cancelled`
- `parked -> active|completed|cancelled`

Single-active policy remains unchanged in this phase.

### 5.2 Node execution lifecycle (execution track)

Keep existing execution states:
- `waiting|execute|done|removed|todo|in_progress|cancelled`

### 5.3 Goal refinement lifecycle (decomposition track)

`refinement_status` transition:
- `rough -> exploring -> decided -> decomposed`

Guideline:
- `decomposed` means decomposition finished, not execution finished.
- execution completion still depends on `status`.

## 6. Core Validation Rules

1. `parent_node_id` must belong to the same `route_id`.
2. Node parent relation must be acyclic (tree constraint).
3. If `spawned_from_node_id` is set, target node must be `node_type=decision`.
4. If `parent_route_id` is set, parent route must exist.
5. Existing edge rules remain:
- no self-loop
- no duplicate edge
- no cross-route edge (V1 policy)

## 7. API Contract Changes (Minimal)

No mandatory new endpoint. Extend payloads on existing APIs.

### 7.1 Route APIs

- `POST /api/v1/routes`
  - accept optional `parent_route_id`, `spawned_from_node_id`
- `PATCH /api/v1/routes/{route_id}`
  - allow patching `parent_route_id` only when route is `candidate` (to reduce historical rewiring risk)

### 7.2 Route Node APIs

- `POST /api/v1/routes/{route_id}/nodes`
  - accept optional `parent_node_id`
  - accept `node_type=goal`
  - accept optional `refinement_status`
- `PATCH /api/v1/routes/{route_id}/nodes/{node_id}`
  - allow `parent_node_id`, `refinement_status`

### 7.3 Node Log APIs

- `POST /api/v1/routes/{route_id}/nodes/{node_id}/logs`
  - accept optional `log_type`, `source_ref`
- `GET /api/v1/routes/{route_id}/nodes/{node_id}/logs`
  - return `log_type`, `source_ref`

### 7.4 Graph response compatibility

- `GET /api/v1/routes/{route_id}/graph` keeps current shape and adds:
  - node field `parent_node_id`
  - node field `refinement_status`

## 8. UI/Interaction Impact (List-First Compatible)

Minimal UI change set:
1. Node form supports `goal` type and optional parent node selection.
2. Node list adds grouping/filter by `refinement_status`.
3. Node log input adds `log_type` and optional `source_ref`.
4. Route detail can show parent/child route links as text chips in V1.

Graph-first editing remains out of scope.

## 9. Migration and Backward Compatibility

1. Existing rows stay valid:
- `parent_route_id`, `spawned_from_node_id`, `parent_node_id`, `source_ref` default `NULL`.
- `refinement_status` default `rough`.
- `log_type` default `note`.

2. Existing clients remain valid:
- all new fields are optional on write.
- response adds fields without breaking existing required contracts.

3. No forced backfill required for V1 rollout.

## 10. Audit and Knowledge Retention

All mutating operations touching new fields must emit audit events as existing route APIs already do.

Knowledge capture convention:
- discovery notes: `log_type=note`
- external inputs: `log_type=evidence`, `source_ref` required by UI convention
- decision records: `log_type=decision`
- periodic wrap-ups: `log_type=summary`

This creates a queryable lifecycle trail from rough goal to decomposed plan.

## 11. Acceptance Criteria

1. A route can reference a parent route and optional spawn decision node.
2. A node can be created as `goal` and can have child nodes via `parent_node_id`.
3. Parent-child node relation rejects cross-route links and cycles.
4. Existing DAG edges continue to work unchanged.
5. Node logs support `log_type` + `source_ref`.
6. Existing Route-Graph workflows still function without requiring new fields.

## 12. Rollout Plan

1. Backend schema and validator updates.
2. API/schema extension + tests for new constraints.
3. Minimal frontend form/list updates.
4. Smoke flow:
- create rough goal node
- add evidence logs
- mark refinement progression
- decompose to child milestones/tasks
- spawn child route from decision node

## 13. Out of Scope (for this phase)

1. Multi-active route policy.
2. Cross-route dependency edges.
3. Full first-class `Goal/Evidence/Decision` table split.
4. Canvas-first graph editing.
