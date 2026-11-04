"""Persistence: processed POs, learned aliases and the audit log.

SQLAlchemy Core keeps one code path for Postgres (local container, Supabase)
and SQLite (tests, quick demos).
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from .match import norm
from .schema import ProcessedPO

meta = MetaData()

purchase_orders = Table(
    "purchase_orders", meta,
    Column("id", Integer, primary_key=True),
    Column("source", String(200), nullable=False),
    Column("shop_id", String(20)),
    Column("po_number", String(100)),
    Column("po_key", String(100)),                     # normalised PO number for duplicate checks
    Column("status", String(20), nullable=False),     # ready | needs_review | blocked | approved | rejected
    Column("payload", JSON, nullable=False),
    Column("file_sha", String(64)),
    Column("erp_ref", String(100)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("decided_at", DateTime(timezone=True)),
    Column("decided_by", String(100)),
)

aliases = Table(
    "aliases", meta,
    Column("id", Integer, primary_key=True),
    Column("shop_id", String(20)),                     # NULL = applies to every shop
    Column("raw_norm", String(200), nullable=False),
    Column("sku", String(40), nullable=False),
    Column("source", String(40), nullable=False),      # admin | seed
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    UniqueConstraint("shop_id", "raw_norm", name="uq_alias"),
)

audit_log = Table(
    "audit_log", meta,
    Column("id", Integer, primary_key=True),
    Column("po_id", Integer),
    Column("actor", String(100), nullable=False),
    Column("action", String(40), nullable=False),
    Column("detail", Text),
    Column("at", DateTime(timezone=True), server_default=func.now()),
)


files = Table(
    "files", meta,
    Column("sha", String(64), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("mime", String(100), nullable=False),
    Column("data", LargeBinary, nullable=False),
)

erp_orders = Table(  # used by the mock ERP adapter only
    "erp_orders", meta,
    Column("id", Integer, primary_key=True),
    Column("idempotency_key", String(200), nullable=False, unique=True),
    Column("ref", String(40), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def po_key(number: str | None) -> str | None:
    """Normalise a PO number for comparison: case, spaces, a leading 'No.' label,
    and the letter O vs digit 0 that handwriting and OCR mix up ('CO15' == 'C015')."""
    if not number:
        return None
    k = re.sub(r"^\s*(no(mor)?|po\s*no)\.?\s*[:.]?\s*", "", number.strip(), flags=re.IGNORECASE)
    k = re.sub(r"[\s.]+", "", k).upper().replace("O", "0")
    return k or None


def default_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///po_agent.db")


class Store:
    def __init__(self, url: str | None = None, engine: Engine | None = None) -> None:
        url = url or default_url()
        if engine is None and url in ("sqlite://", "sqlite:///:memory:"):
            # one shared in-memory DB for every thread (tests, eval)
            engine = create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
        self.engine = engine or create_engine(url, future=True, pool_pre_ping=True)
        meta.create_all(self.engine)

    # ---- aliases (implements match.AliasStore) ----
    def get(self, shop_id: str | None, raw: str) -> str | None:
        key = norm(raw)
        with self.engine.connect() as c:
            for sid in (shop_id, None):
                q = select(aliases.c.sku).where(aliases.c.raw_norm == key)
                q = q.where(aliases.c.shop_id.is_(None) if sid is None else aliases.c.shop_id == sid)
                if (row := c.execute(q).first()) is not None:
                    return row[0]
        return None

    def put(self, shop_id: str | None, raw: str, sku: str, source: str = "admin") -> None:
        key = norm(raw)
        with self.engine.begin() as c:
            q = select(aliases.c.id).where(aliases.c.raw_norm == key)
            q = q.where(aliases.c.shop_id.is_(None) if shop_id is None else aliases.c.shop_id == shop_id)
            if (row := c.execute(q).first()) is not None:
                c.execute(update(aliases).where(aliases.c.id == row[0]).values(sku=sku, source=source))
            else:
                c.execute(insert(aliases).values(shop_id=shop_id, raw_norm=key, sku=sku, source=source))

    def alias_count(self) -> int:
        with self.engine.connect() as c:
            return c.execute(select(func.count()).select_from(aliases)).scalar_one()

    # ---- purchase orders ----
    def find_duplicate(self, shop_id: str | None, po_number: str | None, exclude_id: int | None = None) -> int | None:
        if not shop_id or not po_number:
            return None
        q = (select(purchase_orders.c.id).where(purchase_orders.c.shop_id == shop_id)
             .where(purchase_orders.c.po_key == po_key(po_number))
             .where(purchase_orders.c.status != "rejected"))
        if exclude_id:  # re-checking an existing PO: only an EARLIER one can make it a duplicate
            q = q.where(purchase_orders.c.id < exclude_id)
        with self.engine.connect() as c:
            row = c.execute(q.order_by(purchase_orders.c.id)).first()
        return row[0] if row else None

    def save(self, po: ProcessedPO, file_sha: str | None = None) -> int:
        with self.engine.begin() as c:
            res = c.execute(insert(purchase_orders).values(
                source=po.source, shop_id=po.shop_id, po_number=po.po_number, po_key=po_key(po.po_number),
                status=po.status,
                payload=json.loads(po.model_dump_json()), file_sha=file_sha))
            po_id = res.inserted_primary_key[0]
            c.execute(insert(audit_log).values(po_id=po_id, actor="agent", action="processed",
                                               detail=json.dumps({"status": po.status, "model": po.usage.model})))
        return po_id

    def update_payload(self, po_id: int, po: ProcessedPO, actor: str, action: str, detail: dict) -> None:
        with self.engine.begin() as c:
            c.execute(update(purchase_orders).where(purchase_orders.c.id == po_id).values(
                payload=json.loads(po.model_dump_json()), status=po.status, shop_id=po.shop_id,
                po_number=po.po_number, po_key=po_key(po.po_number)))
            c.execute(insert(audit_log).values(po_id=po_id, actor=actor, action=action, detail=json.dumps(detail)))

    def decide(self, po_id: int, status: str, actor: str, erp_ref: str | None = None, detail: dict | None = None) -> None:
        with self.engine.begin() as c:
            c.execute(update(purchase_orders).where(purchase_orders.c.id == po_id).values(
                status=status, decided_by=actor, decided_at=datetime.now(UTC), erp_ref=erp_ref))
            c.execute(insert(audit_log).values(po_id=po_id, actor=actor, action=status,
                                               detail=json.dumps({"erp_ref": erp_ref, **(detail or {})})))

    def get_po(self, po_id: int) -> dict | None:
        with self.engine.connect() as c:
            row = c.execute(select(purchase_orders).where(purchase_orders.c.id == po_id)).mappings().first()
        return dict(row) if row else None

    def list_pos(self, limit: int = 50) -> list[dict]:
        with self.engine.connect() as c:
            rows = c.execute(select(purchase_orders).order_by(purchase_orders.c.id.desc()).limit(limit)).mappings()
            return [dict(r) for r in rows]

    def find_by_sha(self, sha: str) -> int | None:
        with self.engine.connect() as c:
            row = c.execute(select(purchase_orders.c.id).where(purchase_orders.c.file_sha == sha)).first()
        return row[0] if row else None

    def shop_skus(self, shop_id: str | None) -> set[str]:
        """SKUs this shop bought in approved orders: used to pick a size the shop did not write."""
        if not shop_id:
            return set()
        with self.engine.connect() as c:
            rows = c.execute(select(purchase_orders.c.payload).where(purchase_orders.c.shop_id == shop_id)
                             .where(purchase_orders.c.status == "approved")).all()
        return {ln["sku"] for (payload,) in rows for ln in payload["lines"] if ln.get("sku")}

    def put_file(self, sha: str, name: str, mime: str, data: bytes) -> None:
        with self.engine.begin() as c:
            if c.execute(select(files.c.sha).where(files.c.sha == sha)).first() is None:
                c.execute(insert(files).values(sha=sha, name=name, mime=mime, data=data))

    def get_file(self, sha: str) -> dict | None:
        with self.engine.connect() as c:
            row = c.execute(select(files).where(files.c.sha == sha)).mappings().first()
        return dict(row) if row else None

    def audit(self, po_id: int) -> list[dict]:
        with self.engine.connect() as c:
            rows = c.execute(select(audit_log).where(audit_log.c.po_id == po_id).order_by(audit_log.c.id)).mappings()
            return [dict(r) for r in rows]
