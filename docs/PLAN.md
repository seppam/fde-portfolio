# PO Agent — FDE portfolio plan

> Status: draft, waiting for the owner's OK (2026-11-04).
> Client and data are fictional. No real company, customer, or price list is used.

## 1. The (fictional) engagement

**Client:** PT Kenari Distribusi (fictional), an FMCG distributor in Karawang/Bekasi serving ~300 small shops and minimarkets.

**Today:** shops send purchase orders (PO) as PDF attachments, phone photos of handwritten notes, or Excel files by email. Two admin staff retype every PO into the ERP (Odoo). About 120 POs a day.

**Pain (to be validated in discovery, numbers are assumptions until measured on our synthetic set):**
- Retyping takes ~4–6 minutes per PO; the queue grows after 14:00, so same-day delivery is missed.
- Shops write product names their own way ("indomie goreng dus", "IDM GRG 40"), so the admin guesses the SKU.
- Old prices and wrong units (pcs vs karton) slip through.

**Engagement goal:** a PO agent that turns an incoming PO into a *draft* sales order, with a human approving every order before it reaches the ERP.

**Success metrics (measured on the golden set):**
| Metric | Target |
|---|---|
| Header fields correct (shop, date, PO number) | ≥ 95% |
| Line items matched to the right SKU | ≥ 90% |
| Quantity + unit correct | ≥ 95% |
| POs that need zero edits at review | ≥ 60% |
| Time from upload to draft | < 30 s |
| LLM cost per PO | ≈ Rp0 on free tier, report tokens anyway |

## 2. Architecture

```
intake (upload / email via Mailpit)
  -> extract   (Gemini vision -> Pydantic schema, Groq text fallback for Excel/CSV)
  -> match     (alias table -> RapidFuzz -> LLM tie-break, with confidence)
  -> validate  (rules: unit, price list, credit limit, duplicate PO)
  -> review UI (human approves / edits; edits feed the alias table)
  -> ERP adapter (Odoo draft sale.order locally | Postgres "mock ERP" on the live demo)
  + audit log, eval harness, prompt-injection guard
```

## 3. Stack (decided from the environment check)

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.12 (pinned with `uv`) | 66% of FDE postings ask for Python; same as msp-ops-copilot and Struk Kilat. Machine has 3.14, pin 3.12 for hosting compatibility. |
| Web | FastAPI + Jinja2 + HTMX | One language, no separate frontend build; good enough for a review screen. |
| DB | Postgres (local container on port 5434, Supabase free tier when deployed) | Same SQL locally and live. |
| LLM | Gemini (vision, free tier) + Groq (text) | Free; provider-agnostic client like msp-ops-copilot. |
| Matching | RapidFuzz + alias table | Fast, explainable, no GPU. |
| PDF/photo tooling | pypdf, Pillow; tesseract/poppler only as baseline comparison | Already installed. |
| ERP | Odoo 19 in `~/Documents/odoo-lab` (local) | Real ERP integration, reused. Not hosted (no free hosting). |
| Email | Mailpit (image already pulled) | Local inbox, no real email. |
| Tests | pytest, Playwright (Python) for the review UI | Reuses SDET skills. |
| Deploy | Vercel (Python) + Supabase free | Only with the owner's explicit OK. |

Notes from the environment check: Docker is already running Simpang (kind + db) and the bekal-pt Supabase stack, so this project uses its own small Postgres container instead of a second local Supabase, and starts Odoo only in the ERP phase.

## 4. Phases

Each step: why -> small build -> owner runs it -> 2–3 check questions. Learning page gets a chapter per phase.

| # | Phase | Output | Light work for Haiku subagents |
|---|---|---|---|
| 0 | Discovery & plan | this doc, client brief, learning page ch. 1–5 | link check of references |
| 1 | Synthetic data | product master (~80 SKU), 40 shops, 30 golden POs (PDF, photo-like image, Excel) + labels | generate product/shop CSVs, render PO files |
| 2 | Extraction | Pydantic schema, Gemini vision extractor, eval harness v1 | — |
| 3 | Matching | alias + fuzzy + LLM tie-break, confidence, eval v2 | build alias seed list |
| 4 | Validation + review UI | rules engine, FastAPI/HTMX review screen, edits feed aliases | Playwright smoke tests |
| 5 | ERP adapter | Odoo draft `sale.order` + mock ERP, idempotency | — |
| 6 | Email intake + guardrails | Mailpit intake, prompt-injection tests, audit log | write injection test fixtures |
| 7 | Deploy (ask first) | Vercel + Supabase live demo with mock ERP | — |
| 8 | Client pack | discovery notes, SOW, runbook, handover, eval report, README | proofread docs |
| 9 | Showcase | learning page final + quiz, LinkedIn draft, Remotion video with English voice-over | captions, screenshots |

## 5. Rules

- Repo `fde-portfolio` becomes public only when the owner says so. Learning page, demo assets, voice-over and LinkedIn copy live in the private `fde-portfolio-kit` folder (same pattern as the SDET kit).
- Keys only in `.env` (gitignored); never pasted into chat.
- No invented metrics: every number in docs, video, and LinkedIn comes from an eval run in `experiments/`.
- Nothing is pushed, deployed, or posted without the owner's OK.
