# PO Agent

**Shop purchase orders in, draft ERP sales orders out, with a human approving every order.**

A forward-deployed-engineering portfolio project. A (fictional) FMCG distributor gets
~120 purchase orders a day as PDFs, phone photos of handwritten notes and Excel
files, and two admins retype them into Odoo. PO Agent reads each PO, matches what the
shop wrote to the client's own product list, runs the business checks, and puts a
draft in front of the admin. Approving creates a **draft quotation** in Odoo, never a
confirmed order.

> All company names, shops, products and prices are invented. No real customer data.

![Review screen: an ambiguous size was picked by the admin and the order is ready](docs/img/04-review-fixed.jpg)

## Results on the 30-PO golden set

| | |
|---|---|
| Customer identified | **100%** |
| Lines found / qty + unit correct | **100% / 99.5%** (186 lines) |
| SKU correct | **92.5%** (82.8% without the LLM tie-break) |
| Expected business checks raised | **100%**, 0 false alarms |
| Wrong product without a warning | **0** |
| POs needing zero edits | **53%** (target 60%, not met; see why in [EVAL_REPORT](docs/EVAL_REPORT.md)) |

Numbers come from `evals/run_eval.py`; every run is saved in `experiments/`.
The first run was worse, and the report lists what was fixed in the agent and
what was a bug in the test data.

## How it works

1. **Extract**: Gemini reads PDFs and photos, Groq reads Excel, into a Pydantic schema.
   Instruction-like text in a document is copied to `notes` and never followed.
2. **Match**: aliases learned from admin fixes, then fuzzy matching, then an LLM
   tie-break between close candidates. A missing size is flagged, not guessed.
3. **Check** (plain code): price list, pack sizes, credit limit, duplicate PO
   (handwriting-tolerant), outlier quantities, discontinued items, injection text.
4. **Review**: the admin fixes what is flagged; each fix re-runs the checks and
   becomes an alias for that shop. Approve is idempotent.
5. **ERP**: `ERPAdapter` with an Odoo 19 JSON-2 implementation and a mock.

More: [architecture](docs/ARCHITECTURE.md) · [discovery notes](docs/DISCOVERY.md) ·
[statement of work](docs/SOW.md) · [runbook](docs/RUNBOOK.md) · [handover](docs/HANDOVER.md) ·
[deploy](docs/DEPLOY.md)

| Injection attempt is shown, flagged and ignored | A resent PO ("CO15" vs "C015") is blocked |
|---|---|
| ![](docs/img/07-injection.jpg) | ![](docs/img/06-duplicate-blocked.jpg) |

## Run it

Needs Python 3.12 (`uv`), Docker, and free API keys for Gemini and Groq.

```
cp .env.example .env          # add GEMINI_API_KEY and GROQ_API_KEY
make setup && make up
make dev                      # http://localhost:8088, upload data/golden/files/po_03.pdf
make test                     # offline tests, no API calls
make e2e                      # Playwright browser tests
make eval NOTE="baseline"     # score on the golden set
```

Email intake: `uv run python scripts/send_test_email.py po_03 po_17`, then
"Check email inbox". Odoo: see [runbook](docs/RUNBOOK.md).

## Tests

55 offline unit/API tests, 4 Playwright E2E tests, 1 Odoo integration test
(`RUN_ODOO_TESTS=1`), plus the golden-set evaluation.

## Stack

Python 3.12, FastAPI, Jinja2, HTMX, Pydantic, RapidFuzz, SQLAlchemy (Postgres / SQLite),
Gemini + Groq over plain HTTP, Odoo 19, Mailpit, pytest, Playwright, uv.
