# Architecture

```
 shop email / upload
        │
        ▼
 ┌─────────────┐   PDF, photo ─► Gemini (vision)  ┐
 │ 1 extract   │   Excel ──────► Groq (text)      ├─► ExtractedPO (Pydantic)
 └─────────────┘   PDF fallback ► text layer→Groq ┘
        ▼
 ┌─────────────┐   alias table (admin fixes) ─► fuzzy (RapidFuzz) ─► LLM tie-break
 │ 2 match     │   ─► shop history for missing sizes ─► else flag, never guess
 └─────────────┘
        ▼
 ┌─────────────┐   price list, pack sizes, credit, duplicates, outliers,
 │ 3 check     │   discontinued, injection text  →  block / warn / info
 └─────────────┘
        ▼
 ┌─────────────┐   admin edits (each edit re-runs the checks, SKU fixes become aliases)
 │ 4 review    │   approve → ERP adapter (idempotency key = shop + PO number)
 └─────────────┘
        ▼
  Odoo draft quotation (local)  |  mock ERP (live demo)
```

## Modules (`src/po_agent/`)

| File | Responsibility |
|---|---|
| `catalog.py` | Client master data, unit vocabulary (dus = ktn = karton) |
| `llm.py` | Two HTTP clients (Gemini, Groq), model fallback, disk cache by content hash |
| `extract.py` | Prompt, file-type routing, Pydantic validation |
| `match.py` | Product and customer matching, thresholds, ambiguity, history |
| `rules.py` | Business checks as plain code, severities, status |
| `guard.py` | Prompt-injection detection (the design already ignores document instructions) |
| `pipeline.py` | `build()` and `evaluate()`: the same code for the app and the eval |
| `store.py` | SQLAlchemy Core: POs, files, aliases, audit log, PO-number normalisation |
| `erp/` | `ERPAdapter` protocol, `mock.py`, `odoo.py` (JSON-2 API) |
| `intake_email.py` | Mailpit mailbox poller (swap for IMAP / Graph / Gmail at a real client) |
| `web/` | FastAPI + Jinja2 + HTMX review screen and JSON API |

## Decisions

| Decision | Why | Trade-off |
|---|---|---|
| LLM only for reading and tie-breaks | Rules must be deterministic and testable; prices never come from a model | More code than "let the LLM do it all" |
| Draft quotations only | Confirmed Odoo orders are locked; fixing them means cancel and re-create | Admin still clicks confirm in Odoo |
| Aliases per shop | The same words mean different products at different shops | Learning is slower across shops |
| No SDKs, plain HTTP | Easy to read, mock and swap providers | Write retries/fallback ourselves |
| Cache by content hash | Eval runs are repeatable and free | Cache must be cleared to measure a new model |
| SQLite for tests, Postgres for real | One code path, fast tests | Must avoid DB-specific SQL |
| Server-rendered PDF preview | Phones and headless browsers cannot show PDFs inline | One more endpoint |

## Security notes

- Document text is data. The extraction prompt says so, the guard flags instruction-like
  text, and nothing in the document can change a price or skip review.
- Uploads: extension allow-list, 4 MB cap, SHA-256 de-duplication.
- Keys only in `.env` / platform env vars. The Odoo key belongs to an integration user.
- Every edit, approval, rejection and ERP failure is in `audit_log` with who and when.
