"""Step 4: business rules. Plain code on purpose: deterministic, testable, auditable.

Severity:
  block - the order cannot be approved until the problem is fixed
  warn  - a human must look at it, then may approve
  info  - shown to the reviewer, no action needed
"""

from __future__ import annotations

from .catalog import Product, Shop, products
from .schema import Flag, MatchedLine

QTY_OUTLIER_PCS = 2000      # a single line above this many pieces is unusual for a shop
PRICE_TOLERANCE = 0.02      # 2% difference between written price and price list
LOW_CONFIDENCE = 0.9

SCENARIO_CODES = {"UNKNOWN_PRODUCT", "DISCONTINUED", "UNIT_NOT_SOLD", "QTY_OUTLIER",
                  "CREDIT_LIMIT", "DUPLICATE_PO", "INJECTION_SUSPECT", "PRICE_MISMATCH",
                  "MISSING_PO_NUMBER"}


def line_flags(i: int, ln: MatchedLine, product: Product | None) -> list[Flag]:
    out = []
    if product is None and ln.method == "ambiguous":
        options = " / ".join(products()[c[0]].name for c in ln.candidates)
        out.append(Flag(code="AMBIGUOUS_VARIANT", severity="warn", line=i,
                        message=f"'{ln.raw_name}' has no size; pick one: {options}"))
        return out
    if product is None:
        out.append(Flag(code="UNKNOWN_PRODUCT", severity="warn", line=i,
                        message=f"'{ln.raw_name}' is not in the product list; pick a SKU or remove the line"))
        return out
    if not product.active:
        out.append(Flag(code="DISCONTINUED", severity="warn", line=i,
                        message=f"{product.name} is discontinued; offer a replacement"))
    if ln.unit is None:
        out.append(Flag(code="UNIT_UNKNOWN", severity="warn", line=i,
                        message=f"unit '{ln.raw_unit}' is not recognised"))
    elif product.pcs_per(ln.unit) is None:
        out.append(Flag(code="UNIT_NOT_SOLD", severity="warn", line=i,
                        message=f"{product.name} is not sold per {ln.unit} (sold per {', '.join(product.sellable_units())})"))
    if ln.qty != int(ln.qty):
        out.append(Flag(code="QTY_FRACTION", severity="warn", line=i, message=f"quantity {ln.qty} is not whole"))
    per = product.pcs_per(ln.unit) if ln.unit else None
    if per and ln.qty * per > QTY_OUTLIER_PCS:
        out.append(Flag(code="QTY_OUTLIER", severity="warn", line=i,
                        message=f"{ln.qty:g} {ln.unit} = {int(ln.qty * per)} pcs, far above a normal shop order"))
    if ln.written_price and ln.unit_price and abs(ln.written_price - ln.unit_price) > PRICE_TOLERANCE * ln.unit_price:
        out.append(Flag(code="PRICE_MISMATCH", severity="info", line=i,
                        message=f"shop wrote Rp{ln.written_price:,}, price list is Rp{ln.unit_price:,} (price list is used)"))
    if ln.method in ("fuzzy", "llm", "history") and ln.confidence < LOW_CONFIDENCE:
        out.append(Flag(code="LOW_CONFIDENCE", severity="warn", line=i,
                        message=f"'{ln.raw_name}' matched to {product.name} with confidence {ln.confidence:.2f}"))
    return out


def order_flags(shop: Shop | None, shop_conf: float, po_number: str | None, total: int,
                duplicate_of: str | None, injection_hits: list[str]) -> list[Flag]:
    out = []
    if shop is None:
        out.append(Flag(code="SHOP_UNKNOWN", severity="block", message="buyer could not be matched to a customer"))
    elif shop_conf < 0.85:
        out.append(Flag(code="SHOP_LOW_CONFIDENCE", severity="warn",
                        message=f"buyer matched to {shop.name} with confidence {shop_conf:.2f}"))
    if not po_number:
        out.append(Flag(code="MISSING_PO_NUMBER", severity="warn",
                        message="no PO number written; confirm with the shop before approving"))
    if duplicate_of:
        out.append(Flag(code="DUPLICATE_PO", severity="block",
                        message=f"same shop and PO number already received ({duplicate_of})"))
    if shop is not None:
        remaining = shop.credit_limit - shop.outstanding
        if total > remaining:
            out.append(Flag(code="CREDIT_LIMIT", severity="block",
                            message=f"order Rp{total:,} exceeds remaining credit Rp{remaining:,}"))
    if injection_hits:
        out.append(Flag(code="INJECTION_SUSPECT", severity="warn",
                        message="the document contains instruction-like text aimed at an automated system; it was ignored"))
    return out


def status_for(flags: list[Flag]) -> str:
    if any(f.severity == "block" for f in flags):
        return "blocked"
    if any(f.severity == "warn" for f in flags):
        return "needs_review"
    return "ready"
