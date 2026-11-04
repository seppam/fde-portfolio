"""Integration test against the real local Odoo (odoo-lab, database 'kenari').

Run: RUN_ODOO_TESTS=1 uv run pytest tests/test_odoo.py   (needs ODOO_* in .env)
"""

import os
import uuid
from pathlib import Path

import pytest
from conftest import make_po

from po_agent.pipeline import build

pytestmark = [pytest.mark.odoo,
              pytest.mark.skipif(os.getenv("RUN_ODOO_TESTS") != "1", reason="set RUN_ODOO_TESTS=1")]


@pytest.fixture
def odoo(monkeypatch):
    for line in (Path(__file__).resolve().parents[1] / ".env").read_text().splitlines():
        if line.startswith("ODOO_"):
            k, v = line.split("=", 1)
            monkeypatch.setenv(k, v)
    from po_agent.erp.odoo import OdooAdapter
    return OdooAdapter()


def test_draft_order_is_created_once_and_stays_draft(odoo, store, usage):
    number = f"PO-TEST-{uuid.uuid4().hex[:6]}"
    po = build(make_po([("Mie Raja Goreng 85g", 2, "dus"), ("Kopi Senja Mocca 30g", 1, "renceng")],
                       shop="Minimarket Mulia Berkah", number=number), usage, "test.pdf", store, use_llm=False)
    key = f"{po.shop_id}:{number.lower()}"
    ref1 = odoo.create_draft_order(po, key)
    ref2 = odoo.create_draft_order(po, key)          # retry / double click
    assert ref1 == ref2
    orders = odoo.call("sale.order", "search_read", domain=[["name", "=", ref1]],
                       fields=["state", "amount_untaxed", "partner_id", "order_line"], limit=5)
    assert len(orders) == 1
    assert orders[0]["state"] == "draft"             # never confirmed by the agent
    assert orders[0]["amount_untaxed"] == po.total   # 2 dus x 40 x 3200 + 10 x 1600
    assert len(orders[0]["order_line"]) == 2
