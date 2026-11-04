"""Odoo 19 adapter over the JSON-2 API.

Creates a sale.order in state 'draft' (a quotation). It never confirms the
order: in Odoo a confirmed order is locked, and fixing it means cancel and
re-create, so the human confirms inside Odoo.

Idempotency: the key is stored in `client_order_ref` ("Customer Reference"),
and we search for it before creating.
"""

from __future__ import annotations

import os

import httpx

from ..catalog import products, shops
from ..schema import ProcessedPO
from . import ERPError


class OdooAdapter:
    name = "odoo"

    def __init__(self) -> None:
        self.url = os.environ.get("ODOO_URL", "http://127.0.0.1:8069").rstrip("/")
        self.db = os.environ.get("ODOO_DB", "kenari")
        self.key = os.environ.get("ODOO_API_KEY", "")

    def call(self, model: str, method: str, **kwargs):
        try:
            r = httpx.post(f"{self.url}/json/2/{model}/{method}", json=kwargs, timeout=30,
                           headers={"Authorization": f"bearer {self.key}", "X-Odoo-Database": self.db})
        except httpx.HTTPError as e:
            raise ERPError(f"odoo unreachable: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise ERPError(f"{model}.{method} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    def _partner(self, shop_id: str) -> int:
        s = shops()[shop_id]
        found = self.call("res.partner", "search_read", domain=[["ref", "=", shop_id]], fields=["id"], limit=1)
        if found:
            return found[0]["id"]
        return self.call("res.partner", "create", vals_list=[{
            "name": s.name, "ref": shop_id, "email": s.email, "city": s.city, "is_company": True}])[0]

    def _product(self, sku: str) -> int:
        found = self.call("product.product", "search_read", domain=[["default_code", "=", sku]],
                          fields=["id"], limit=1)
        if found:
            return found[0]["id"]
        p = products()[sku]
        return self.call("product.product", "create", vals_list=[{
            "name": p.name, "default_code": sku, "list_price": p.price_pcs, "sale_ok": True,
            "type": "consu"}])[0]

    def create_draft_order(self, po: ProcessedPO, idempotency_key: str) -> str:
        ref = f"POAGENT:{idempotency_key}"
        found = self.call("sale.order", "search_read", domain=[["client_order_ref", "=", ref]],
                          fields=["name"], limit=1)
        if found:
            return found[0]["name"]
        lines = []
        for ln in po.lines:
            if not ln.sku or not ln.unit_price:
                raise ERPError(f"line '{ln.raw_name}' has no SKU or price; fix it on the review screen")
            per = products()[ln.sku].pcs_per(ln.unit) or 1
            lines.append([0, 0, {"product_id": self._product(ln.sku), "product_uom_qty": ln.qty * per,
                                 "price_unit": products()[ln.sku].price_pcs,
                                 "name": f"{products()[ln.sku].name} ({ln.qty:g} {ln.unit})"}])
        new_id = self.call("sale.order", "create", vals_list=[{
            "partner_id": self._partner(po.shop_id), "client_order_ref": ref,
            "note": f"Created by PO Agent from {po.source}. PO {po.po_number or '-'} dated {po.po_date or '-'}.",
            "order_line": lines}])[0]
        return self.call("sale.order", "read", ids=[new_id], fields=["name"])[0]["name"]
