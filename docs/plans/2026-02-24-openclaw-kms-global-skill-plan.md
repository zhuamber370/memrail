> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# MemLineage Workspace Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a generic OpenClaw integration for MemLineage that installs as a workspace skill and does not require manual system-prompt paste or manual Python action wiring.

**Architecture:** Package MemLineage integration as a native OpenClaw skill bundle (`SKILL.md` + `index.js` + REST client), install it into `<workspace>/skills/kms` via scripts, and keep auth via environment variables only. Existing backend APIs remain unchanged.

**Tech Stack:** JavaScript (Node runtime in OpenClaw), shell scripts (`bash`), existing MemLineage REST API.

---

### Task 1: Add Native OpenClaw Skill Bundle

**Files:**
- Create: `<repo_root>/openclaw-skill/kms/SKILL.md`
- Create: `<repo_root>/openclaw-skill/kms/index.js`
- Create: `<repo_root>/openclaw-skill/kms/lib/client.js`
- Create: `<repo_root>/openclaw-skill/kms/package.json`

**Step 1: Write failing check (skill is not discoverable yet)**

Run: `openclaw skills info kms --json`
Expected: command fails or reports missing skill.

**Step 2: Implement minimal skill bundle**

Implement action handlers:
- Read: `get_context_bundle`, `list_tasks`, `search_notes`, `list_journals`, `get_journal`
- Write proposal: `propose_record_todo`, `propose_append_journal`, `propose_upsert_knowledge`
- Governance: `commit_changes`, `reject_changes`, `undo_last_commit`

Use `KMS_BASE_URL` + `KMS_API_KEY`, with optional `KMS_ACTOR_ID`.

**Step 3: Verify bundle syntax**

Run: `node --check <repo_root>/openclaw-skill/kms/index.js`
Expected: no syntax errors.

**Step 4: Commit checkpoint**

Run:
```bash
git add <repo_root>/openclaw-skill/kms
git commit -m "feat(skill): add native openclaw kms skill bundle"
```

### Task 2: Add Workspace Install/Uninstall Scripts

**Files:**
- Create: `<repo_root>/scripts/install_openclaw_kms_skill.sh`
- Create: `<repo_root>/scripts/uninstall_openclaw_kms_skill.sh`

**Step 1: Write failing check**

Run: `test -d ~/.openclaw/workspace/skills/kms && echo exists || echo missing`
Expected: usually `missing` before install.

**Step 2: Implement scripts**

- Install script:
  - auto detect OpenClaw workspace path
  - backup existing `<workspace>/skills/kms` with timestamp
  - copy `openclaw-skill/kms` into `<workspace>/skills/kms`
  - run `openclaw skills info kms --json` for post-check
- Uninstall script:
  - remove `<workspace>/skills/kms`
  - run `openclaw skills info kms --json` and handle missing state

**Step 3: Verify scripts**

Run:
```bash
bash <repo_root>/scripts/install_openclaw_kms_skill.sh
openclaw skills info kms --json
bash <repo_root>/scripts/uninstall_openclaw_kms_skill.sh
```
Expected: install discoverable; uninstall removed.

**Step 4: Commit checkpoint**

Run:
```bash
git add <repo_root>/scripts/install_openclaw_kms_skill.sh <repo_root>/scripts/uninstall_openclaw_kms_skill.sh
git commit -m "feat(skill): add workspace install and uninstall scripts for kms skill"
```

### Task 3: Update Documentation to Generic Flow

**Files:**
- Modify: `<repo_root>/docs/reports/2026-02-24-openclaw-kms-setup.md`
- Modify: `<repo_root>/skill/README.md`
- Modify: `<repo_root>/README.md`

**Step 1: Replace manual process with generic process**

Document:
- one-time env setup
- one command install
- OpenClaw auto-discovery behavior
- verification and troubleshooting

Remove:
- manual system prompt paste requirement
- manual Python action wiring requirement

**Step 2: Verify docs consistency**

Run:
```bash
rg -n "system prompt|openclaw_system_prompt|actions/.*\\.py|manual" <repo_root>/docs/reports/2026-02-24-openclaw-kms-setup.md <repo_root>/skill/README.md <repo_root>/README.md -S
```
Expected: no outdated instructions for mandatory manual prompt/action wiring.

**Step 3: Commit checkpoint**

Run:
```bash
git add <repo_root>/docs/reports/2026-02-24-openclaw-kms-setup.md <repo_root>/skill/README.md <repo_root>/README.md
git commit -m "docs: switch openclaw kms setup to generic workspace skill flow"
```

### Task 4: Final Verification

**Files:**
- Verify all modified files above

**Step 1: Run fast verification commands**

Run:
```bash
node --check <repo_root>/openclaw-skill/kms/index.js
node --check <repo_root>/openclaw-skill/kms/lib/client.js
bash <repo_root>/scripts/install_openclaw_kms_skill.sh
openclaw skills info kms --json
openclaw skills check --json
bash <repo_root>/scripts/uninstall_openclaw_kms_skill.sh
```
Expected: syntax clean, skill discoverable after install, removed after uninstall.

**Step 2: Report evidence**

Include command outputs summary with pass/fail and any residual warnings.
