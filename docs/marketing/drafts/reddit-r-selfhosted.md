# Draft: Reddit (`r/selfhosted`)

Title:
I open-sourced Memrail: a self-hosted governance layer for agent writes (OpenClaw)

Post:
I built and open-sourced Memrail, a self-hosted memory/task governance layer for OpenClaw workflows.

Why I built it:
- agents writing directly into memory/tasks created drift
- hard to review what changed and why
- weak rollback safety when bad writes landed

What Memrail does:
- dry-run every write first
- show diff preview
- human approve/reject in `/changes`
- commit only after approval
- keep audit trail and support undo

It's local-first:
- FastAPI + Next.js
- SQLite default
- PostgreSQL optional

Repo:
https://github.com/zhuamber370/memrail

If you're running agent workflows self-hosted, I'd love feedback:
- Is this approval model too heavy or necessary?
- What would you need before trying it in your stack?

