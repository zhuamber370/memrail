# Memrail Integration (OpenClaw-first)

Memrail is designed to be the **governed memory & change-governance layer** for OpenClaw workflows.

It helps you prevent "agent writes" from silently polluting memory/knowledge by enforcing a PR-like loop:

**dry-run → diff preview → human approve/reject → commit → audit (+ undo)**

---

## What you integrate

Integrate Memrail at the boundary of *writes*:

Agent/Skill wants to write → Memrail **dry-run** (diff) → human review → **commit** → data applied + audit trail.

Reads are safe by default.

---

## Minimal setup

1) Run Memrail backend + frontend (see `README.md` Quickstart)

2) Install OpenClaw skill:

```bash
bash scripts/install_openclaw_kms_skill.sh
```

3) Configure env (where OpenClaw runs)

- `KMS_BASE_URL=http://127.0.0.1:8000`
- `KMS_API_KEY=...`

---

## How the control loop works (PR-like changes)

### Reads
- Safe by default (no writes).

### Writes
- Always go through: **dry-run → confirm → commit**.

### Human approval
- Use `/changes` UI to review diff and commit/reject.

### Rollback
- If a commit goes wrong, use **undo** to roll back the last commit.

---

## Integration checklist (for OpenClaw skill / UI authors)

- [ ] Every write path is routed through Memrail changes pipeline
- [ ] You can display: `change_set_id`, `summary`, `diff_items`
- [ ] You can trigger: commit (`approved_by` + `client_request_id`)
- [ ] You can audit: commit id / who approved / when
- [ ] You have a rollback story (undo)

---

## Need help integrating?

Open an **Integration Request** issue (template included) and provide:

- Your target workflow (what is writing what)
- Where you want human approval to happen
- What you want the diff to look like
- Your environment (OS / Memrail version / OpenClaw version)
