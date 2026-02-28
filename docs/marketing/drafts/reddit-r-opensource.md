# Draft: Reddit (`r/opensource`)

Title:
Memrail (Apache-2.0): PR-like review for AI agent writes

Post:
I just open-sourced Memrail (Apache-2.0), focused on a specific problem:
how to govern AI agent writes to tasks/knowledge so teams can trust automation.

Core idea:
Treat agent writes like pull requests.

Flow:
`dry-run -> diff preview -> human approve/reject -> commit -> audit (+ undo)`

Current product surface:
- `/changes`: review + commit/reject + undo
- `/tasks`: execution workspace
- `/knowledge`: knowledge CRUD workspace

Tech:
- FastAPI + SQLAlchemy
- Next.js
- SQLite default, PostgreSQL optional

GitHub:
https://github.com/zhuamber370/memrail

Would appreciate feedback on:
- API shape for governed writes
- audit/traceability expectations
- where this fits in your current agent toolchain

