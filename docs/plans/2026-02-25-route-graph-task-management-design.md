# Memrail Route-Graph Task Management Design (V1 List-First, V2 Graph-First)

## Goal

Support full-lifecycle product/development management for Memrail using branchable routes instead of flat tasks, while preserving governed writes and auditability.

This design addresses the current gap: ad-hoc ideas, route branching, and execution logs are hard to express in the existing single-layer task model.

## Confirmed Product Decisions

1. V1 interaction is list-first; V2 target is graph-first.
2. Idea capture must start in `Idea Inbox` and then be promoted.
3. Idea state machine:
- `captured -> triage -> discovery -> ready -> rejected`
4. Route state machine:
- `candidate -> active -> parked -> completed -> cancelled`
5. V1 route activation policy is single-active.
- only one route may be `active` at a time.
- future policy can switch to multi-active.
6. Node log is attached to node level only in V1.
7. Node types in V1:
- `decision`
- `milestone`
- `task`
8. Cross-route dependencies are disallowed in V1.

## Current Model Gap

Current `tasks` table is execution-focused and mostly flat:
- single task entity with status/priority/due/blocked-by
- no first-class idea lifecycle
- no route container with route-level status and goal
- no explicit graph edges between nodes
- no node-scoped execution timeline

This is sufficient for day-to-day TODO tracking but not for strategy branching and route comparison.

## Target Domain Model

### 1) Idea

Represents incoming ideas before commitment.

Core fields:
- `id`
- `title`
- `problem`
- `hypothesis`
- `status` (`captured|triage|discovery|ready|rejected`)
- `topic_id`
- `source`
- `created_at`, `updated_at`

### 2) Route

Represents a candidate or active strategy line.

Core fields:
- `id`
- `name`
- `goal`
- `status` (`candidate|active|parked|completed|cancelled`)
- `priority`
- `owner`
- `created_at`, `updated_at`

### 3) RouteNode

Represents executable/decision units inside a route.

Core fields:
- `id`
- `route_id`
- `node_type` (`decision|milestone|task`)
- `title`
- `description`
- `status` (`todo|in_progress|done|cancelled` initially)
- `order_hint`
- `assignee_type` (`human` now; `agent` reserved)
- `assignee_id` (optional)
- `created_at`, `updated_at`

### 4) RouteEdge

Represents directed dependency relation between nodes.

Core fields:
- `id`
- `route_id`
- `from_node_id`
- `to_node_id`
- `relation` (`blocks|depends_on`)
- `created_at`

Constraints:
- both endpoints must belong to same `route_id` in V1.
- self-loop is disallowed.
- duplicate edge pair is disallowed.

### 5) NodeLog

Represents execution timeline for each node.

Core fields:
- `id`
- `node_id`
- `actor_type` (`human`; `agent` reserved)
- `actor_id`
- `content`
- `created_at`

## Key Rules and Validation

1. Route activation policy (V1):
- when setting a route to `active`, ensure no other route is currently `active`.
- return domain error when violated.

2. Idea promotion:
- only `ready` ideas can be promoted to route nodes.
- promotion stores source link from idea to node.

3. Edge integrity:
- from/to nodes must exist.
- from/to nodes must belong to same route.
- prevent cycles in V1 optional check.
- if cycle detection is deferred, enforce manual warning in API response.

4. Governance:
- create/patch/delete of idea/route/node/edge/log should produce audit events.
- bulk operations should log batch metadata.

## UX Design

### V1 (List-First)

Primary navigation:
- `Ideas`
- `Routes`
- existing `Tasks` remains intact during migration period

`Ideas` page:
- status columns or grouped list by idea state
- quick actions: move state, reject, send to discovery, mark ready, promote to route node

`Routes` page:
- left: route list + status chips
- center: node list grouped by node type (`decision`, `milestone`, `task`)
- right: read-only auto-generated route graph preview
- quick actions: add node, add dependency, append node log, mark done/cancelled

### V2 (Graph-First)

Default route screen becomes graph canvas:
- graph as primary workspace
- list/details as side panel
- in-canvas add/relate/update nodes
- support multi-active routes and agent assignees

## API Draft (V1)

Ideas:
- `POST /api/v1/ideas`
- `GET /api/v1/ideas`
- `PATCH /api/v1/ideas/{idea_id}`
- `POST /api/v1/ideas/{idea_id}/promote`

Routes:
- `POST /api/v1/routes`
- `GET /api/v1/routes`
- `PATCH /api/v1/routes/{route_id}`

Route nodes and edges:
- `POST /api/v1/routes/{route_id}/nodes`
- `PATCH /api/v1/routes/{route_id}/nodes/{node_id}`
- `POST /api/v1/routes/{route_id}/edges`
- `DELETE /api/v1/routes/{route_id}/edges/{edge_id}`
- `GET /api/v1/routes/{route_id}/graph`

Node logs:
- `POST /api/v1/routes/{route_id}/nodes/{node_id}/logs`
- `GET /api/v1/routes/{route_id}/nodes/{node_id}/logs`

## Migration Strategy

1. Keep existing `tasks` APIs operational.
2. Introduce new entities (`ideas`, `routes`, `route_nodes`, `route_edges`, `node_logs`) without breaking task workflows.
3. Add lightweight linking from route-node task to legacy task when needed.
4. Defer full replacement of legacy tasks page until V2 graph-first UX is accepted.

## Risks and Mitigations

1. Risk: data model complexity increases too quickly.
- Mitigation: V1 only ships single-active + same-route edges + list-first editing.

2. Risk: graph editing UX becomes unstable.
- Mitigation: V1 uses read-only graph preview and form-based editing.

3. Risk: discovery inbox grows noisy.
- Mitigation: enforce weekly refinement and stale idea filters.

## Success Criteria

1. New ideas are not directly mixed into execution tasks.
2. At least one route can be represented with branchable nodes and dependencies.
3. Route progression is visible via node logs.
4. Users can understand strategy branch structure using read-only graph in V1.
5. Existing task workflows remain functional.
