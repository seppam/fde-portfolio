"""Mock ERP for the live demo and tests: a table that behaves like an ERP order endpoint."""

from __future__ import annotations

import json

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from ..schema import ProcessedPO
from ..store import erp_orders


class MockERP:
    name = "mock"

    def __init__(self, store) -> None:
        self.store = store

    def create_draft_order(self, po: ProcessedPO, idempotency_key: str) -> str:
        with self.store.engine.begin() as c:
            row = c.execute(select(erp_orders.c.ref).where(erp_orders.c.idempotency_key == idempotency_key)).first()
            if row:
                return row[0]
            n = len(c.execute(select(erp_orders.c.id)).all()) + 1
            ref = f"SO-MOCK-{n:05d}"
            try:
                c.execute(insert(erp_orders).values(idempotency_key=idempotency_key, ref=ref,
                                                    payload=json.loads(po.model_dump_json())))
            except IntegrityError:  # a parallel request won the race; return its order
                return self.create_draft_order(po, idempotency_key)
        return ref
