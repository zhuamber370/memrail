# Safe-to-Write Checklist for AI Agent Workflows

Use this checklist before allowing agent writes into persistent systems.

This page is implementation-agnostic. You can use it with Memrail or map it to your own control plane.

## 1) Scope and Risk Classification

- `Write classes` are defined (task updates, knowledge edits, route/graph edits, inbox captures).
- `Risk tiers` are documented (`low`, `medium`, `high`).
- Each write class has a required control path by risk tier.

Recommended minimum:

| Risk tier | Typical write class | Human approval | Rollback required |
|---|---|---|---|
| Low | Non-destructive metadata update | Optional | Optional |
| Medium | Shared context/task updates | Required (async allowed) | Required |
| High | Destructive/policy-sensitive writes | Required (explicit approver) | Required + tested |

## 2) Pre-Write Controls (Before Any Mutation)

- `Dry-run first`: write intent is represented as a proposal, not applied directly.
- `Diff preview`: approver can inspect target + before/after summary.
- `Approval owner`: approver identity and role requirements are explicit.
- `Rejection path`: rejection reason is captured for policy tuning.

## 3) Commit Controls (At Decision Time)

- `Idempotency`: commit request includes client request ID.
- `Concurrency guard`: stale proposals cannot be committed silently.
- `Approval evidence`: approver ID, timestamp, and decision metadata are persisted.

## 4) Audit and Traceability (After Commit)

Minimum fields to capture per committed action:

| Field | Why it matters |
|---|---|
| `change_set_id` | Links proposal, decision, and commit chain |
| `commit_id` | Primary recovery anchor |
| `action_index` | Disambiguates multi-action commits |
| `actor_type` / `actor_id` | Attribution and accountability |
| `approver_type` / `approver_id` | Approval ownership |
| `target_type` / `target_id` | Blast-radius analysis |
| `decision` / `timestamp` | Incident timeline reconstruction |
| `source_refs` | Upstream context and provenance |

## 5) Recovery Controls

- `Undo path`: deterministic rollback for latest bad commit.
- `Verification`: rollback result is validated and logged.
- `Drill cadence`: at least one staging rollback drill per quarter.

## 6) Operational Guardrails

- `Selective gating`: not every write needs approval; high-risk writes always do.
- `Timeout policy`: pending approvals expire with clear next action.
- `Escalation`: high-risk pending writes have an escalation owner.

## 7) Go-Live Gate

Before production rollout, confirm all items below are true:

- [ ] Dry-run and diff preview are enabled for governed writes.
- [ ] Approval ownership model is documented and enforced.
- [ ] Audit schema includes required fields above.
- [ ] Undo/rollback has been tested in staging with evidence.
- [ ] At least one incident-response drill has been run.
- [ ] Dashboard or query exists for open/pending/rejected write proposals.

## Memrail Mapping

If you are using Memrail, the default governed flow is:

`dry-run -> diff preview -> human approve/reject -> commit -> audit (+ undo)`

References:
- Product and local demo: [../../README.md](../../README.md)
- API contract: [agent-api-surface.md](agent-api-surface.md)
- Proof artifacts: [../proof/README.md](../proof/README.md)
