"""Generate the fictional master data for PT Kenari Distribusi.

Writes data/products.csv and data/shops.csv. All brands, shops and prices are
made up. Run: uv run python scripts/gen_master.py   (deterministic, safe to rerun)
"""

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# sku, name, category, pcs price (Rp), pack units {unit: pcs per unit}, active
PRODUCTS = [
    ("MR-GRG-85", "Mie Raja Goreng 85g", "mi instan", 3200, {"dus": 40}, True),
    ("MR-SOT-75", "Mie Raja Soto 75g", "mi instan", 3000, {"dus": 40}, True),
    ("MR-AYB-70", "Mie Raja Ayam Bawang 70g", "mi instan", 3000, {"dus": 40}, True),
    ("MR-KAR-72", "Mie Raja Kari Ayam 72g", "mi instan", 3100, {"dus": 40}, True),
    ("MR-GRP-90", "Mie Raja Goreng Pedas 90g", "mi instan", 3400, {"dus": 40}, True),
    ("KS-SUS-30", "Kopi Senja Susu 30g", "kopi", 1500, {"renceng": 10, "dus": 120}, True),
    ("KS-HIT-25", "Kopi Senja Hitam 25g", "kopi", 1200, {"renceng": 10, "dus": 120}, True),
    ("KS-MOC-30", "Kopi Senja Mocca 30g", "kopi", 1600, {"renceng": 10, "dus": 120}, True),
    ("TL-KTK-200", "Teh Lestari Kotak 200ml", "minuman", 3500, {"dus": 24}, True),
    ("TL-BTL-350", "Teh Lestari Botol 350ml", "minuman", 4500, {"dus": 12}, True),
    ("TB-AIR-600", "Tirta Bening Air Mineral 600ml", "minuman", 3000, {"dus": 24}, True),
    ("TB-AIR-1500", "Tirta Bening Air Mineral 1500ml", "minuman", 5500, {"dus": 12}, True),
    ("SE-MYK-1L", "Minyak Goreng Surya Emas 1L", "sembako", 18500, {"dus": 12}, True),
    ("SE-MYK-2L", "Minyak Goreng Surya Emas 2L", "sembako", 36000, {"dus": 6}, True),
    ("GMJ-GUL-1K", "Gula Pasir Manis Jaya 1kg", "sembako", 17500, {"bal": 20}, True),
    ("BPW-BRS-5K", "Beras Pandan Wangi 5kg", "sembako", 78000, {"sak": 4}, True),
    ("SWP-SBN-75", "Sabun Mandi Wangi Pagi 75g", "perawatan", 3800, {"dus": 72}, True),
    ("BK-DTG-800", "Deterjen Bersih Kilau 800g", "rumah tangga", 22000, {"dus": 12}, True),
    ("BK-DTG-SCH", "Deterjen Bersih Kilau Sachet 45g", "rumah tangga", 1000, {"renceng": 12, "dus": 144}, True),
    ("SL-SMP-SCH", "Sampo Lembut Sachet 10ml", "perawatan", 1000, {"renceng": 12, "dus": 144}, True),
    ("SL-SMP-170", "Sampo Lembut Botol 170ml", "perawatan", 21000, {"dus": 24}, True),
    ("PGS-PGG-190", "Pasta Gigi Senyum 190g", "perawatan", 14000, {"dus": 48}, True),
    ("SM-SKM-370", "Susu Kental Manis Sapi Mas 370g", "susu", 12500, {"dus": 48}, True),
    ("SM-SKM-SCH", "Susu Kental Manis Sapi Mas Sachet 40g", "susu", 1800, {"renceng": 6, "dus": 120}, True),
    ("BR-BSK-120", "Biskuit Renyah Kelapa 120g", "makanan ringan", 7500, {"dus": 24}, True),
    ("BR-BSK-CKL", "Biskuit Renyah Cokelat 120g", "makanan ringan", 8000, {"dus": 24}, True),
    ("KCM-KCP-520", "Kecap Manis Cap Merak 520ml", "bumbu", 21500, {"dus": 12}, True),
    ("KCM-KCP-SCH", "Kecap Manis Cap Merak Sachet 25ml", "bumbu", 700, {"renceng": 12, "dus": 144}, True),
    ("SPN-SAU-340", "Saus Sambal Pedas Nusantara 340ml", "bumbu", 13000, {"dus": 24}, True),
    ("TSL-TIS-250", "Tisu Lembut 250 lembar", "rumah tangga", 11000, {"bal": 24}, True),
    ("WP-PEL-800", "Pembersih Lantai Wangi Pagi 800ml", "rumah tangga", 15500, {"dus": 12}, True),
    ("SWP-SBN-CR", "Sabun Cuci Piring Wangi Pagi Cair 780ml", "rumah tangga", 14500, {"dus": 12}, True),
    ("MR-CUP-SOT", "Mie Raja Cup Soto 65g", "mi instan", 5500, {"dus": 24}, True),
    ("KS-3IN1-OLD", "Kopi Senja 3in1 Klasik 20g", "kopi", 1100, {"renceng": 10, "dus": 120}, False),
    ("TL-GLS-180", "Teh Lestari Gelas 180ml", "minuman", 1500, {"dus": 24}, False),
    ("SE-MYK-PCH", "Minyak Goreng Surya Emas Pouch 900ml", "sembako", 16500, {"dus": 12}, True),
    ("TP-TPG-1K", "Tepung Terigu Padi Emas 1kg", "sembako", 13000, {"bal": 10}, True),
    ("GG-GRM-250", "Garam Halus Gunung 250g", "bumbu", 3000, {"bal": 50}, True),
    ("SM-UHT-200", "Susu UHT Sapi Mas Cokelat 200ml", "susu", 6000, {"dus": 24}, True),
    ("TB-GLS-220", "Tirta Bening Gelas 220ml", "minuman", 800, {"dus": 48}, True),
]

CITIES = ["Karawang", "Cikampek", "Bekasi", "Cikarang", "Rengasdengklok", "Telukjambe", "Tambun"]
SHOP_WORDS = ["Berkah", "Sumber", "Makmur", "Jaya", "Sentosa", "Barokah", "Rizki", "Abadi",
              "Lancar", "Mulia", "Harapan", "Sejahtera", "Mandiri", "Amanah", "Bintang"]
OWNERS = ["Bu Siti", "Pak Darto", "Bu Ani", "Pak Udin", "Bu Wati", "Pak Joko", "Bu Yanti",
          "Pak Asep", "Bu Lilis", "Pak Rahmat", "Bu Neneng", "Pak Dedi"]


def make_shops(rng: random.Random) -> list[dict]:
    shops, used = [], set()
    while len(shops) < 40:
        kind = rng.choice(["Toko", "Toko", "Warung", "Minimarket", "TB"])
        name = f"{kind} {rng.choice(SHOP_WORDS)} {rng.choice(SHOP_WORDS)}"
        if name in used or name.split()[1] == name.split()[2]:
            continue
        used.add(name)
        i = len(shops) + 1
        limit = rng.choice([5, 10, 15, 25, 40]) * 1_000_000
        shops.append({
            "shop_id": f"C{i:03d}",
            "name": name,
            "city": rng.choice(CITIES),
            "contact": rng.choice(OWNERS),
            "email": f"order.c{i:03d}@toko-contoh.test",
            "credit_limit": limit,
            "outstanding": int(limit * rng.choice([0.1, 0.3, 0.5, 0.7])),
        })
    # One shop almost at its limit, used by the credit-limit scenario.
    shops[11]["credit_limit"] = 5_000_000
    shops[11]["outstanding"] = 4_600_000
    return shops


def main() -> None:
    rng = random.Random(20261104)
    DATA.mkdir(exist_ok=True)
    with (DATA / "products.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sku", "name", "category", "price_pcs", "pack_units", "active"])
        for sku, name, cat, price, packs, active in PRODUCTS:
            w.writerow([sku, name, cat, price, json.dumps(packs), int(active)])
    shops = make_shops(rng)
    with (DATA / "shops.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(shops[0]))
        w.writeheader()
        w.writerows(shops)
    print(f"products: {len(PRODUCTS)}  shops: {len(shops)}")


if __name__ == "__main__":
    main()
