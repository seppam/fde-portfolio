# Handover

For the client's IT person, at the end of the (fictional) two-week engagement.

## What you now own

- The PO Agent service (this repository) and its database.
- An Odoo integration user and its API key (expires after 90 days: calendar reminder).
- The golden set and the eval harness. Add real (anonymised) POs to it over time.

## Daily

- Admins work from the inbox: *ready* (one click), *needs review*, *blocked*.
- Nothing reaches Odoo without an approval, and orders arrive as quotations.

## Weekly (15 minutes)

1. Look at the aliases admins created (`aliases` table, `source = 'admin'`). A wrong
   alias makes the same mistake every time: delete it.
2. Look at blocked POs older than a day.
3. Run `make eval` and compare with `experiments/history.csv`.

## When the business changes

| Change | Where |
|---|---|
| New product / price / pack size | `data/products.csv` (or connect to the Odoo product list, see backlog) |
| New customer or credit limit | `data/shops.csv` (same) |
| New check (e.g. minimum order value) | `rules.py` + a unit test + a golden PO for it |
| Another ERP | new adapter in `erp/`, implement `create_draft_order` |

## Backlog (not done)

1. Read products and customers from Odoo instead of CSV.
2. Ask-back email to the shop when a size or PO number is missing (draft, human sends).
3. Rate limiting and a daily LLM budget before a public demo.
4. A multilingual embedding as a fourth matching step for long free-text names.
5. Paid LLM tier and a latency target per PO in production.
