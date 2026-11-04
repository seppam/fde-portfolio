# Runbook

## Start / stop (local)

```
make up        # Postgres :5434, Mailpit :8026 (web) / :1026 (smtp)
make dev       # review app on http://localhost:8088
make down
```

Odoo: `cd ~/Documents/odoo-lab && docker compose up -d odoo` (database `kenari`).
Set `ERP_ADAPTER=odoo` and `ODOO_*` in `.env` to approve into Odoo instead of the mock.

## Health checks

| Check | Expected |
|---|---|
| `GET /health` | `{"ok": true, "erp": "mock" or "odoo"}` |
| Inbox counts | "Blocked" not growing all day without someone looking |
| `audit_log` action `erp_failed` | 0 per day |

## Common problems

| Symptom | Likely cause | What to do |
|---|---|---|
| "The AI service is busy" on upload | Gemini free tier returned 503 on every model | Retry in a minute; check `GEMINI_MODELS`; move to a paid tier for production |
| Many `AMBIGUOUS_VARIANT` warnings | Shops not writing sizes | Expected at first; history fixes repeat shops. Ask shops to use the template with sizes |
| A PO is blocked as `DUPLICATE_PO` but the shop says it is new | Shop reused a PO number | Change the PO number on the review screen (the check reruns) |
| `ERP error, nothing was created` | Odoo down or API key expired (keys last 90 days) | Start Odoo / create a new key for the integration user; then click Approve again (safe to retry) |
| Approve clicked twice | — | Nothing to do: the second click returns the same order reference |
| Wrong product picked by the agent | Weak match | Pick the right one on the review screen; it becomes an alias for that shop |

## Re-running the evaluation after a change

```
make test
make eval NOTE="what changed"
```
Compare with the previous row in `experiments/history.csv`. Do not ship if
`silent_errors` is above 0 or `flag_recall` drops.
