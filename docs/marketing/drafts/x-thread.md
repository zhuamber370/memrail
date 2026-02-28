# Draft: X Thread

## Post 1

I open-sourced Memrail: a governance layer for OpenClaw agent writes.

Instead of writing directly into memory/tasks, every write goes through:
dry-run -> diff -> human approve/reject -> commit -> audit (+ undo)

Repo: https://github.com/zhuamber370/memrail

## Post 2

Why this exists:
Agent workflows break when memory writes are uncontrolled.
You lose trust because changes are hard to review and roll back.

Memrail makes writes reviewable by default.

## Post 3

Current surface:
- /changes: review inbox
- /tasks: execution workspace
- /knowledge: governed knowledge CRUD

Stack: FastAPI + Next.js, SQLite default, PostgreSQL optional.

## Post 4

If you're running OpenClaw or similar agent-heavy workflows, I'd love feedback:
- Is this governance gate useful?
- What would you need before trying it?
- What should the diff/audit UX include?

