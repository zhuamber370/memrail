# Draft: GitHub Release/Discussion Announcement

Title:
Memrail: Governed Memory + Task Infrastructure for OpenClaw

Body:
Memrail is open source and now ready for broader testing.

What Memrail focuses on:
- governance for agent writes
- human-in-the-loop approval before commit
- auditability and rollback safety

Core write flow:
`dry-run -> diff preview -> human approve/reject -> commit -> audit (+ undo)`

Current UX:
- `/changes` for review and commit/reject
- `/tasks` as command center
- `/knowledge` as governed knowledge workspace

Stack:
- FastAPI + SQLAlchemy
- Next.js
- SQLite default, PostgreSQL optional

Repository:
https://github.com/zhuamber370/memrail

If you're building with OpenClaw or similar agent systems, feedback is very welcome:
- missing governance primitives
- API ergonomics
- review/approval UX gaps

