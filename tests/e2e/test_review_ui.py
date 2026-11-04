"""Browser smoke tests for the PO review flow, driven through the real upload form.

Run only these with: uv run pytest tests/e2e -q
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


def upload_po(page: Page, base_url: str, filename: str, test_name: str) -> None:
    """Upload through the inbox form and wait until the review page opens."""
    page.goto(f"{base_url}/")
    # Unique bytes per test: identical files are de-duplicated by SHA-256.
    payload = {"name": filename, "mimeType": "application/pdf",
               "buffer": f"%PDF-1.4 fake {filename} {test_name}".encode()}
    page.get_by_test_id("file-input").set_input_files(payload)
    page.get_by_test_id("upload-button").click()
    expect(page).to_have_url(re.compile(r"/po/\d+$"))


@pytest.mark.e2e
def test_clean_po_is_ready_and_approves_into_erp(page: Page, live_url: str, request: pytest.FixtureRequest):
    upload_po(page, live_url, "clean.pdf", request.node.name)

    expect(page.get_by_test_id("status")).to_have_text("ready")
    expect(page.get_by_test_id("total")).to_have_text("Rp256.000")

    page.get_by_test_id("approve").click()

    expect(page.get_by_test_id("message")).to_contain_text("SO-MOCK-")
    expect(page.get_by_test_id("erp-ref")).to_be_visible()
    expect(page.get_by_test_id("approve")).to_have_count(0)


@pytest.mark.e2e
def test_unknown_product_is_fixed_by_choosing_sku(page: Page, live_url: str, request: pytest.FixtureRequest):
    upload_po(page, live_url, "unknown.pdf", request.node.name)

    expect(page.get_by_test_id("flag-UNKNOWN_PRODUCT")).to_be_visible()
    expect(page.get_by_test_id("status")).to_have_text("needs review")

    page.get_by_test_id("sku-1").select_option("MR-GRG-85")

    # htmx swaps the review panel: the flag goes away and the PO becomes ready.
    expect(page.get_by_test_id("flag-UNKNOWN_PRODUCT")).to_have_count(0)
    expect(page.get_by_test_id("status")).to_have_text("ready")


@pytest.mark.e2e
def test_credit_limit_blocks_approval(page: Page, live_url: str, request: pytest.FixtureRequest):
    upload_po(page, live_url, "credit.pdf", request.node.name)

    expect(page.get_by_test_id("flag-CREDIT_LIMIT")).to_be_visible()
    expect(page.get_by_test_id("status")).to_have_text("blocked")
    expect(page.get_by_test_id("approve")).to_be_disabled()


@pytest.mark.e2e
def test_inbox_lists_uploaded_pos(page: Page, live_url: str, request: pytest.FixtureRequest):
    upload_po(page, live_url, "clean.pdf", request.node.name)
    upload_po(page, live_url, "credit.pdf", request.node.name)

    page.goto(f"{live_url}/")
    table = page.get_by_test_id("po-table")
    expect(table.locator("tbody tr")).to_have_count(2)
    expect(table).to_contain_text("clean.pdf")
    expect(table).to_contain_text("credit.pdf")
    expect(table).to_contain_text("PO-E1")
    expect(table).to_contain_text("PO-E3")
