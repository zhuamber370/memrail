# Incident example: prevent bad writes with human review

Scenario: an agent proposes a knowledge change that should **not** be committed.

Why this matters:
- Without governance, agent writes can silently pollute memory/knowledge.
- With Memrail, every write is a proposal; humans can review the **diff** first.

## Steps
1. Create a proposal via **dry-run** (you get `change_set_id` + diff preview)
2. Open `/changes` UI and review the diff ledger
3. **Reject** the proposal (or simply do not commit it)

## What to show in UI
- change_set_id
- actor + tool
- Dry-run summary (creates/updates, fields touched)
- Diff ledger (entity/action/fields)

