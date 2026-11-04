"""The whole flow for one PO: extract -> match -> price -> rules -> (save).

`build()` is pure apart from the LLM calls and the alias/duplicate lookups, so
the eval harness and the web app run exactly the same code.
"""

from __future__ import annotations

from .catalog import products
from .extract import extract
from .guard import suspicious
from .match import match_product, match_shop, match_unit
from .rules import line_flags, order_flags, status_for
from .schema import ExtractedPO, MatchedLine, ProcessedPO, Usage


class Lookups:
    """What the pipeline needs from storage. Store implements all three."""

    def get(self, shop_id, raw): ...
    def put(self, shop_id, raw, sku, source="admin"): ...
    def find_duplicate(self, shop_id, po_number, exclude_id=None): ...


def price_line(ln: MatchedLine) -> None:
    p = products().get(ln.sku) if ln.sku else None
    per = p.pcs_per(ln.unit) if (p and ln.unit) else None
    if p and per:
        ln.unit_price = p.price_pcs * per
        ln.line_total = round(ln.unit_price * ln.qty)
    else:
        ln.unit_price = ln.line_total = None


def evaluate(po: ProcessedPO, store: Lookups, exclude_id: int | None = None) -> ProcessedPO:
    """(Re)compute prices, flags and status. Used after extraction and after every human edit."""
    from .catalog import shops

    flags = []
    for i, ln in enumerate(po.lines, 1):
        price_line(ln)
        p = products().get(ln.sku) if ln.sku else None
        lf = line_flags(i, ln, p)
        ln.flags = [f.code for f in lf]
        flags += lf
    po.total = sum(ln.line_total or 0 for ln in po.lines)
    shop = shops().get(po.shop_id) if po.shop_id else None
    dup = store.find_duplicate(po.shop_id, po.po_number, exclude_id)
    hits = suspicious(po.notes) + [h for ln in po.lines for h in suspicious(ln.raw_name)]
    flags += order_flags(shop, po.shop_confidence, po.po_number, po.total,
                         f"PO #{dup}" if dup else None, hits)
    po.flags = flags
    po.status = status_for(flags)
    return po


def build(ex: ExtractedPO, usage: Usage, source: str, store: Lookups,
          sender_email: str | None = None, use_llm: bool = True) -> ProcessedPO:
    shop, shop_conf = match_shop(ex.shop_name, sender_email)
    shop_id = shop.shop_id if shop else None
    history = store.shop_skus(shop_id) if hasattr(store, "shop_skus") else set()
    lines = []
    for raw in ex.lines:
        sku, conf, method, cands, extra = match_product(raw.raw_name, shop_id, store, use_llm, history)
        if extra:
            usage.input_tokens += extra.get("input_tokens", 0)
            usage.output_tokens += extra.get("output_tokens", 0)
        p = products().get(sku) if sku else None
        lines.append(MatchedLine(raw_name=raw.raw_name, qty=raw.qty, raw_unit=raw.raw_unit,
                                 unit=match_unit(raw.raw_unit, p), sku=sku,
                                 product_name=p.name if p else None, confidence=conf, method=method,
                                 candidates=cands[:3], written_price=raw.unit_price))
    po = ProcessedPO(source=source, shop_id=shop_id, shop_name=shop.name if shop else ex.shop_name,
                     shop_confidence=shop_conf, po_number=ex.po_number, po_date=ex.po_date,
                     lines=lines, flags=[], total=0, status="needs_review", usage=usage, notes=ex.notes)
    return evaluate(po, store)


def process(data: bytes, filename: str, store: Lookups, sender_email: str | None = None,
            use_llm: bool = True) -> ProcessedPO:
    ex = extract(data, filename)
    return build(ex.po, ex.usage, filename, store, sender_email, use_llm)
