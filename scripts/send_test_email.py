"""Send golden POs as emails to the local Mailpit (nothing leaves this machine).

Run: uv run python scripts/send_test_email.py po_03 po_17
The sender is the shop's address from data/shops.csv, like a real shop would send it.
"""

import json
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from po_agent.catalog import shops

MIME = {".pdf": ("application", "pdf"), ".jpg": ("image", "jpeg"),
        ".xlsx": ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

for po in sys.argv[1:] or ["po_03"]:
    lab = json.loads((ROOT / "data/golden/labels" / f"{po}.json").read_text())
    shop = shops()[lab["truth"]["shop_id"]]
    msg = EmailMessage()
    msg["From"], msg["To"] = f"{shop.name} <{shop.email}>", "order@kenari-distribusi.test"
    msg["Subject"] = f"Order {lab['truth']['po_number'] or ''}".strip()
    msg.set_content(f"Selamat siang, terlampir order dari {shop.name}. Terima kasih.")
    f = ROOT / "data/golden/files" / lab["file"]
    maintype, subtype = MIME[f.suffix]
    msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype, filename=f.name)
    with smtplib.SMTP("localhost", 1026) as s:
        s.send_message(msg)
    print(f"sent {f.name} from {shop.email}")
