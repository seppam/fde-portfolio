# Discovery notes: PT Kenari Distribusi (fictional)

> Fictional engagement for a portfolio. The company, shops, products and prices are
> invented. Numbers marked *assumption* were never measured at a real client.

## Who we talked to (role play)

| Role | What they care about |
|---|---|
| Head of Sales Admin | Same-day delivery cut-off at 15:00; two admins cannot keep up after 14:00 |
| Admin staff (2) | Retyping, guessing which product the shop meant, angry calls when the wrong pack arrives |
| Finance | Orders above a shop's credit limit slipping through |
| IT (one person) | Odoo must stay the system of record; no one wants a second place to edit orders |

## Current process

1. Shops email a PO: typed PDF, a phone photo of a handwritten note, or an Excel file.
2. Admin reads it, finds the customer in Odoo, retypes each line, picks the SKU.
3. Admin confirms the quotation in Odoo; the warehouse picks from confirmed orders.

Volume *assumption*: ~120 POs/day, 4–6 minutes each.

## What goes wrong

- **Names are written the shop's way**: "MR GRG 85", "minyak goreng surya emas"
  (which of the three sizes?), typos like "minayk".
- **Units vary**: dus / ktn / karton / dos are the same; renceng and bal are not.
- **Old prices** on the shop's own template.
- **Duplicates**: a shop resends the same PO when it gets no reply.
- **Credit**: nobody checks the remaining credit while typing.

## A constraint that shaped the design

From Application Support experience (the author's own background): typos rarely
become tickets *while a record is still editable*, because users fix them
themselves. They become expensive once a record is locked: then the fix is a
permission-gated database edit, or cancel and re-create from the start.

In Odoo a confirmed sales order is effectively locked. So **the agent only ever
creates a draft (quotation)**. The admin reviews, and confirming stays a human
action inside Odoo. Mistakes are caught while they are still cheap.

## Out of scope (agreed)

- Confirming orders, invoicing, stock reservation.
- Talking back to shops automatically (possible phase 2: ask-back email for a missing size).
- Training a custom model. Off-the-shelf LLMs plus the client's own master data are enough.
