# CrackMap Frontend

Next.js UI for CrackMap, replacing the Streamlit app (`app.py`). Talks to the
FastAPI backend (`backend_server.py`, repo root) through a dev-server proxy —
see `next.config.ts` / `.env.local` (`BACKEND_URL`).

## Run

Two processes, in separate terminals:

```bash
# 1. Backend (repo root)
python backend_server.py

# 2. Frontend (this directory)
npm run dev
```

Open http://localhost:3000.

## Test

```bash
npm run test    # Vitest unit tests (lib/api, lib/equalizer, hooks)
npm run e2e     # Playwright E2E (needs both servers running)
npm run build   # production build + typecheck
npm run lint    # eslint
```
