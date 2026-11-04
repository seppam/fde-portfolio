"""Live-server fixtures for the Playwright smoke tests.

The app runs in a background uvicorn thread on a free 127.0.0.1 port. The LLM
extractor is replaced by a fake (so no network or API key is needed) and the
ERP is the mock adapter. Every test gets its own empty in-memory store, so
duplicate-PO checks from one test cannot leak into another.
"""

from __future__ import annotations

import importlib.util
import os
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

# `import conftest` would resolve to this file, so load tests/conftest.py by path.
_root_conftest = Path(__file__).resolve().parents[1] / "conftest.py"
_spec = importlib.util.spec_from_file_location("tests_root_conftest", _root_conftest)
_root = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root)
make_po = _root.make_po

from po_agent import pipeline
from po_agent.schema import Extraction, Usage
from po_agent.store import Store
from po_agent.web import app as webapp

FAKES = {
    "clean.pdf": make_po([("Mie Raja Goreng 85g", 2, "dus")], shop="Minimarket Mulia Berkah", number="PO-E1"),
    "unknown.pdf": make_po([("barang aneh sekali", 1, "dus")], shop="Minimarket Mulia Berkah", number="PO-E2"),
    "credit.pdf": make_po([("Minyak Goreng Surya Emas 1L", 5, "dus")], shop="Toko Makmur Sumber", number="PO-E3"),
}


def _fake_extract(data: bytes, filename: str) -> Extraction:
    return Extraction(po=FAKES[filename].model_copy(deep=True), usage=Usage(provider="fake", model="fake"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(base_url: str, thread: threading.Thread, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise RuntimeError("uvicorn thread exited before the app became healthy")
        try:
            if httpx.get(f"{base_url}/health", timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.05)
    raise RuntimeError(f"app did not answer GET /health within {timeout}s")


@pytest.fixture(scope="session")
def live_url():
    saved_extract = pipeline.extract
    saved_store = webapp._store
    saved_adapter = os.environ.get("ERP_ADAPTER")

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    pipeline.extract = _fake_extract
    os.environ["ERP_ADAPTER"] = "mock"
    webapp.set_store(Store("sqlite://"))

    config = uvicorn.Config(webapp.app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="uvicorn-e2e", daemon=True)
    thread.start()
    try:
        _wait_healthy(base_url, thread)
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        pipeline.extract = saved_extract
        webapp._store = saved_store  # restore whatever store was active before (None if unset)
        if saved_adapter is None:
            os.environ.pop("ERP_ADAPTER", None)
        else:
            os.environ["ERP_ADAPTER"] = saved_adapter


@pytest.fixture(autouse=True)
def fresh_store(live_url):
    """Each E2E test starts with an empty database (duplicate-PO checks stay per test)."""
    webapp.set_store(Store("sqlite://"))
