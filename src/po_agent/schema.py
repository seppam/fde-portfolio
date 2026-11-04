"""Data shapes that flow through the pipeline.

The LLM fills ExtractedPO. Everything after that (matching, rules, review)
works on typed objects, so a malformed LLM answer fails here, early.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedLine(BaseModel):
    raw_name: str = Field(description="Product name exactly as written on the PO, not corrected")
    qty: float = Field(gt=0, description="Quantity as a number; words like 'dua' become 2")
    raw_unit: str | None = Field(default=None, description="Unit word as written, e.g. dus, ktn, pcs")
    unit_price: int | None = Field(default=None, description="Unit price in Rupiah if written, else null")


class ExtractedPO(BaseModel):
    shop_name: str | None = Field(default=None, description="Buyer / shop name as written")
    po_number: str | None = Field(default=None, description="PO number as written, null if absent")
    po_date: str | None = Field(default=None, description="PO date as ISO YYYY-MM-DD, null if absent")
    lines: list[ExtractedLine]
    notes: str | None = Field(default=None, description="Any other free text or instructions, verbatim")


class Usage(BaseModel):
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cached: bool = False


class Extraction(BaseModel):
    po: ExtractedPO
    usage: Usage


class MatchedLine(BaseModel):
    raw_name: str
    qty: float
    raw_unit: str | None
    unit: str | None = None          # canonical unit
    sku: str | None = None
    product_name: str | None = None
    confidence: float = 0.0
    method: str = "none"             # alias | fuzzy | llm | none
    candidates: list[tuple[str, float]] = []
    unit_price: int | None = None    # from master price list, never from the PO
    written_price: int | None = None
    line_total: int | None = None
    flags: list[str] = []


class Flag(BaseModel):
    code: str
    severity: str  # block | warn | info
    message: str
    line: int | None = None


class ProcessedPO(BaseModel):
    source: str
    shop_id: str | None
    shop_name: str | None
    shop_confidence: float
    po_number: str | None
    po_date: str | None
    lines: list[MatchedLine]
    flags: list[Flag]
    total: int
    status: str  # ready | needs_review | blocked
    usage: Usage
    notes: str | None = None
