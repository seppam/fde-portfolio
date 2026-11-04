"""Client master data: products, shops, and unit vocabulary.

Master data is the client's source of truth. Prices and pack sizes always come
from here, never from the PO text (see guard.py and rules.py).
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Raw unit words seen on shop POs -> canonical unit.
UNIT_SYNONYMS = {
    "dus": "dus", "dos": "dus", "ds": "dus", "karton": "dus", "ktn": "dus", "krt": "dus",
    "box": "dus", "kardus": "dus", "carton": "dus", "ctn": "dus",
    "pcs": "pcs", "pc": "pcs", "biji": "pcs", "bks": "pcs", "bungkus": "pcs", "sachet": "pcs",
    "sct": "pcs", "btl": "pcs", "botol": "pcs", "klg": "pcs", "kaleng": "pcs", "buah": "pcs",
    "pack": "pcs", "pak": "pcs", "cup": "pcs", "gelas": "pcs", "kotak": "pcs",
    "renceng": "renceng", "rcg": "renceng", "rc": "renceng", "rntg": "renceng", "renteng": "renceng",
    "bal": "bal", "ball": "bal",
    "sak": "sak", "karung": "sak", "krg": "sak",
}


def normalize_unit(raw: str | None) -> str | None:
    if not raw:
        return None
    key = re.sub(r"[^a-z]", "", raw.lower())
    return UNIT_SYNONYMS.get(key)


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price_pcs: int
    pack_units: dict = field(hash=False)
    active: bool

    def pcs_per(self, unit: str) -> int | None:
        if unit == "pcs":
            return 1
        return self.pack_units.get(unit)

    def sellable_units(self) -> list[str]:
        return ["pcs", *self.pack_units]


@dataclass(frozen=True)
class Shop:
    shop_id: str
    name: str
    city: str
    contact: str
    email: str
    credit_limit: int
    outstanding: int


@lru_cache
def products() -> dict[str, Product]:
    out = {}
    with (DATA_DIR / "products.csv").open() as f:
        for r in csv.DictReader(f):
            out[r["sku"]] = Product(r["sku"], r["name"], r["category"], int(r["price_pcs"]),
                                    json.loads(r["pack_units"]), r["active"] == "1")
    return out


@lru_cache
def shops() -> dict[str, Shop]:
    out = {}
    with (DATA_DIR / "shops.csv").open() as f:
        for r in csv.DictReader(f):
            out[r["shop_id"]] = Shop(r["shop_id"], r["name"], r["city"], r["contact"], r["email"],
                                     int(r["credit_limit"]), int(r["outstanding"]))
    return out
