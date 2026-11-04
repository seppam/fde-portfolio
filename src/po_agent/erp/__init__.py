"""ERP adapters. The core only knows `ERPAdapter`; each client gets its own implementation."""

from __future__ import annotations

import os
from typing import Protocol

from ..schema import ProcessedPO


class ERPError(RuntimeError):
    pass


class ERPAdapter(Protocol):
    name: str

    def create_draft_order(self, po: ProcessedPO, idempotency_key: str) -> str:
        """Create a DRAFT sales order and return its reference. Calling it again with
        the same key must return the same reference and create nothing new."""
        ...


def idempotency_key(po: ProcessedPO, po_id: int) -> str:
    # shop + PO number identifies a business order; fall back to our own id when the PO has no number
    return f"{po.shop_id}:{(po.po_number or f'noref-{po_id}').strip().lower()}"


def get_adapter(store) -> ERPAdapter:
    kind = os.getenv("ERP_ADAPTER", "mock")
    if kind == "odoo":
        from .odoo import OdooAdapter
        return OdooAdapter()
    from .mock import MockERP
    return MockERP(store)
