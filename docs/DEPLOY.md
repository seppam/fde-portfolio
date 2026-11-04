# Deploying the live demo (Vercel + Supabase)

Status: **prepared, not deployed.** Deploying publishes a public URL and uses the
owner's accounts, so it waits for an explicit go-ahead.

## What runs where

| Piece | Local | Live demo |
|---|---|---|
| Web app | `make dev` (uvicorn) | Vercel Python Function (`app.py` at the root, Python 3.12 from `.python-version`) |
| Database | Postgres container on port 5434 | Supabase free Postgres (`DATABASE_URL`) |
| ERP | Odoo 19 in `~/Documents/odoo-lab` | mock ERP (`ERP_ADAPTER=mock`); Odoo is not hosted |
| Email intake | Mailpit | off (upload only) |
| LLM cache | `.cache/llm` | `/tmp/po-cache` (`PO_CACHE_DIR`), Vercel's file system is read-only elsewhere |

## Steps

1. Supabase: create a project, copy the **pooled** connection string (port 6543),
   change the scheme to `postgresql+psycopg://`. Tables are created on first request.
2. Vercel: `vercel link` in this folder, then add environment variables in the dashboard
   (never paste them in chat): `GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`,
   `ERP_ADAPTER=mock`, `PO_CACHE_DIR=/tmp/po-cache`.
3. `vercel deploy` (preview) → open `/health`, upload `data/golden/files/po_03.pdf`.
4. Only then `vercel deploy --prod`.

## Limits to know

- Vercel request bodies are capped at 4.5 MB; the app rejects files over 4 MB first.
- Free Gemini tiers return 503 under load; the client falls back across models and the
  UI shows "the AI service is busy" instead of a stack trace.
- A public demo needs abuse protection before sharing widely: Vercel Firewall rate limit
  on `POST /upload` and `/api/po`, and a daily cap on LLM calls.
