"""Email intake: read unread messages from Mailpit and process their attachments.

Mailpit stands in for the client's order mailbox (order@kenari...). In a real
engagement this would be IMAP or the Microsoft Graph / Gmail API; only this
file changes. The sender address is used to identify the shop, which is more
reliable than the name written on the PO.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import httpx

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx"}


def poll_mailpit(ingest: Callable[[bytes, str, str | None], int], limit: int = 20) -> dict:
    base = os.getenv("MAILPIT_API", "http://localhost:8026").rstrip("/")
    try:
        msgs = httpx.get(f"{base}/api/v1/messages", params={"limit": limit}, timeout=10).json()["messages"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise RuntimeError(f"mailbox unreachable at {base}") from e
    processed, skipped, read_ids = [], [], []
    # Mailpit lists newest first; process oldest first so the earlier PO is the original
    # and a resend is the one flagged as a duplicate.
    for m in sorted(msgs, key=lambda m: m.get("Created", "")):
        if m.get("Read"):
            continue
        detail = httpx.get(f"{base}/api/v1/message/{m['ID']}", timeout=10).json()
        sender = (detail.get("From") or {}).get("Address")
        atts = [a for a in detail.get("Attachments", []) if Path(a["FileName"]).suffix.lower() in ALLOWED]
        if not atts:
            skipped.append({"subject": m.get("Subject"), "reason": "no PO attachment"})
        for a in atts:
            data = httpx.get(f"{base}/api/v1/message/{m['ID']}/part/{a['PartID']}", timeout=20).content
            try:
                po_id = ingest(data, a["FileName"], sender)
                processed.append({"po_id": po_id, "file": a["FileName"], "from": sender})
            except Exception as e:  # one bad attachment must not stop the others
                skipped.append({"file": a["FileName"], "reason": getattr(e, "detail", str(e))})
        read_ids.append(m["ID"])
    if read_ids:
        httpx.put(f"{base}/api/v1/messages", json={"IDs": read_ids, "Read": True}, timeout=10)
    return {"processed": processed, "skipped": skipped}
