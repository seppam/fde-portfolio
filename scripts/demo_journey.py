"""Drive the real app through a demo journey and save screenshots + a screen recording.

Uses the real pipeline with cached LLM answers (run `make eval` once first, so no
API key is needed), an in-memory database, the mock ERP, and the local Mailpit
inbox (send POs first with scripts/send_test_email.py).

Run: uv run python scripts/demo_journey.py OUT_DIR
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("ERP_ADAPTER", "mock")
os.environ["GEMINI_API_KEY"] = os.environ["GROQ_API_KEY"] = ""  # cache only: never call an API here

from po_agent.store import Store
from po_agent.web import app as webapp

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "reports" / "demo")
OUT.mkdir(parents=True, exist_ok=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    webapp.set_store(Store("sqlite://"))
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(webapp.app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2,
                                  record_video_dir=str(OUT / "video"), record_video_size={"width": 1440, "height": 900})
        page = ctx.new_page()
        shot = lambda name: page.screenshot(path=str(OUT / f"{name}.png"))

        page.goto(base + "/")
        page.wait_for_timeout(800)
        shot("01-inbox-empty")
        page.get_by_role("button", name="Check email inbox").click()
        expect(page.locator("#mailresult")).to_contain_text("processed", timeout=60_000)
        page.reload()
        page.wait_for_timeout(800)
        shot("02-inbox-after-email")

        rows = {r.locator("td").nth(4).inner_text(): r.locator("a").first.get_attribute("href")
                for r in page.locator("[data-testid=po-table] tbody tr").all()}

        # PDF with an ambiguous size: the reviewer picks it, the order turns ready, approve
        page.goto(base + rows["po_03.pdf"])
        page.wait_for_timeout(1200)
        shot("03-review-ambiguous")
        amb = page.locator("[data-testid=flag-AMBIGUOUS_VARIANT]").first
        line_no = int(amb.inner_text().split("line ")[1].split(":")[0])
        page.locator(f"[data-testid=sku-{line_no}]").select_option("SE-MYK-1L")
        expect(page.locator("[data-testid=flag-AMBIGUOUS_VARIANT]")).to_have_count(0)
        page.wait_for_timeout(800)
        shot("04-review-fixed")
        page.get_by_test_id("approve").click()
        expect(page.get_by_test_id("erp-ref")).to_be_visible()
        page.wait_for_timeout(1000)
        shot("05-approved")

        # Same PO number again (handwritten O vs 0): blocked as a duplicate
        page.goto(base + rows["po_14.jpg"])
        page.wait_for_timeout(1500)
        shot("06-duplicate-blocked")

        # Injection attempt inside the PDF
        page.goto(base + rows["po_17.pdf"])
        page.wait_for_timeout(1500)
        shot("07-injection")

        # Handwritten photo with quantities as words
        page.goto(base + rows["po_27.jpg"])
        page.wait_for_timeout(1500)
        shot("08-handwritten")

        # Credit limit
        page.goto(base + rows["po_12.xlsx"])
        page.wait_for_timeout(1500)
        shot("09-credit-limit")
        page.goto(base + "/")
        page.wait_for_timeout(1000)
        shot("10-inbox-final")
        ctx.close()
        browser.close()
    server.should_exit = True
    print("saved to", OUT)


if __name__ == "__main__":
    main()
