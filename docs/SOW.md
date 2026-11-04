# Statement of work (one page)

**Client:** PT Kenari Distribusi (fictional) · **Duration:** 2 weeks · **Team:** 1 forward deployed engineer

## Goal

Incoming shop POs become **draft** sales orders in Odoo within 30 seconds, with every
order approved by an admin before it reaches the ERP.

## Deliverables

1. PO Agent service: intake (upload, email), extraction, product matching, business checks.
2. Review screen for admins, with an audit log of every edit and approval.
3. Odoo integration that creates draft quotations only, safe to retry.
4. Evaluation harness and a 30-PO golden set with correct answers.
5. Runbook and handover notes for the client's IT person.

## Acceptance criteria (measured on the golden set)

| Criterion | Target | Result (eval v3, 4 Nov 2026) |
|---|---|---|
| Customer identified | ≥ 95% | 100% |
| Lines found | ≥ 95% | 100% (186/186) |
| Quantity + unit correct | ≥ 95% | 99.5% |
| Line matched to the right SKU | ≥ 90% | 92.5% |
| Business checks raised when expected | ≥ 95% | 100%, 0 false flags |
| Wrong SKU **without** a warning (silent error) | 0 | 0 |
| POs needing zero edits | ≥ 60% | **53% (not met)**, see EVAL_REPORT |
| Upload to draft | < 30 s | avg 20.5 s extraction (Gemini free tier under load) |

## Client responsibilities

- Product and customer master data export (SKU, pack sizes, prices, credit).
- One admin available 30 minutes a day during the pilot to review and give feedback.
- An Odoo API key for a dedicated integration user.

## Risks

| Risk | Mitigation |
|---|---|
| Free LLM tier busy (HTTP 503) | Fallback across models; clear "busy, retry" message; paid tier for production |
| Shop writes no size | Flag `AMBIGUOUS_VARIANT`, use the shop's purchase history once it exists |
| Malicious text in a PO | Treated as data, flagged, prices always from the price list, human approval |
