# Frontend

Next.js frontend for Memrail MVP.

## Env

Frontend reads env from `.env.local`:

- `NEXT_PUBLIC_API_BASE` (for example `http://localhost:8000`)
- `NEXT_PUBLIC_API_KEY`

Recommended (single source of truth from repo root):

```bash
cd frontend
cp ../.env .env.local
```

## Local Run

```bash
cd frontend
npm install
npm run dev
```
