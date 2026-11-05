"""Vercel entrypoint: Vercel looks for a FastAPI `app` in app.py at the project root.
Locally use `make dev` instead."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from po_agent.web.app import app  # noqa: F401
