"""Prompt-injection guard.

A PO comes from outside the company, so any text in it is untrusted. Two lines
of defence:
1. Design: the extractor copies instruction-like text into `notes` and the
   rest of the pipeline never acts on it. Prices come from the master list,
   and nothing reaches the ERP without a human approval.
2. Detection (this file): flag suspicious text so the reviewer sees a warning.
"""

from __future__ import annotations

import re

PATTERNS = [
    r"\babaikan\b.*\b(instruksi|perintah|aturan)",
    r"\bignore\b.*\b(instruction|previous|above|rules)",
    r"\b(sistem|system)\s*(otomatis|ai|prompt)\b",
    r"\b(as an ai|kamu adalah|you are now)\b",
    r"\btanpa\s+(review|pengecekan|persetujuan|approval)\b",
    r"\b(without|skip)\s+(review|approval)\b",
    r"\b(set|tetapkan|ubah|ganti)\s+(semua\s+)?harga\b",
    r"\b(langsung|auto(matis)?)\s+(konfirmasi|confirm|setujui|approve)\b",
]
_RX = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PATTERNS]


def suspicious(text: str | None) -> list[str]:
    """Return the patterns that matched (empty list = looks clean)."""
    if not text:
        return []
    return [rx.pattern for rx in _RX if rx.search(text)]
