import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Tests never call real LLMs unless asked; an empty key makes accidental calls fail fast.
if os.getenv("RUN_LLM_TESTS") != "1":
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GROQ_API_KEY"] = ""

from po_agent.schema import ExtractedLine, ExtractedPO, Usage
from po_agent.store import Store


@pytest.fixture
def store():
    return Store("sqlite://")


@pytest.fixture
def usage():
    return Usage(provider="fake", model="fake")


def make_po(lines, shop="Toko Makmur Sumber", number="PO-1", date="2026-11-03", notes=None):
    return ExtractedPO(shop_name=shop, po_number=number, po_date=date, notes=notes,
                       lines=[ExtractedLine(raw_name=n, qty=q, raw_unit=u, unit_price=p)
                              for n, q, u, *rest in lines for p in [rest[0] if rest else None]])
