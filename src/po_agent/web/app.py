"""Review web app: upload or receive POs, review the draft, approve into the ERP.

Run: uv run uvicorn po_agent.web.app:app --reload --port 8088
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from ..catalog import products, shops
from ..erp import ERPError, get_adapter, idempotency_key
from ..extract import MIME, xlsx_to_text
from ..llm import LLMError
from ..pipeline import evaluate, process
from ..schema import ProcessedPO
from ..store import Store

MAX_BYTES = 4 * 1024 * 1024
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx"}

app = FastAPI(title="PO Agent", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["rp"] = lambda v: "-" if v is None else f"Rp{int(v):,}".replace(",", ".")
_store: Store | None = None


def store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def set_store(s: Store) -> None:  # used by tests
    global _store
    _store = s


def reviewer(request: Request) -> str:
    return request.cookies.get("reviewer") or os.getenv("DEFAULT_REVIEWER", "admin-1")


def load(po_id: int) -> tuple[dict, ProcessedPO]:
    row = store().get_po(po_id)
    if row is None:
        raise HTTPException(404, "PO not found")
    return row, ProcessedPO.model_validate(row["payload"])


def ingest(data: bytes, filename: str, sender_email: str | None = None) -> int:
    """Shared by upload, API and email intake."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"file type {ext or '?'} is not supported; send PDF, JPG/PNG or XLSX")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "file is larger than 4 MB")
    sha = hashlib.sha256(data).hexdigest()
    if (existing := store().find_by_sha(sha)) is not None:
        return existing  # the same file twice: show the first result, process nothing
    try:
        po = process(data, filename, store(), sender_email=sender_email)
    except LLMError as e:
        raise HTTPException(503, f"the AI service is busy, try again in a minute ({e})") from e
    mime = MIME.get(ext, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    store().put_file(sha, filename, mime, data)
    return store().save(po, file_sha=sha)


def render_review(request: Request, po_id: int, message: str | None = None, partial: bool = False):
    row, po = load(po_id)
    ctx = {"request": request, "row": row, "po": po, "po_id": po_id, "products": products(),
           "shops": shops(), "message": message, "audit": store().audit(po_id),
           "locked": row["status"] in ("approved", "rejected")}
    if row["file_sha"] and (f := store().get_file(row["file_sha"])) and f["name"].lower().endswith(".xlsx"):
        ctx["sheet_text"] = xlsx_to_text(f["data"])
    return templates.TemplateResponse(request, "_review_body.html" if partial else "review.html", ctx)


@app.get("/health")
def health():
    return {"ok": True, "erp": os.getenv("ERP_ADAPTER", "mock")}


@app.get("/", response_class=HTMLResponse)
def inbox(request: Request):
    rows = store().list_pos()
    counts = {s: sum(1 for r in rows if r["status"] == s)
              for s in ("ready", "needs_review", "blocked", "approved", "rejected")}
    return templates.TemplateResponse(request, "index.html", {"rows": rows, "counts": counts,
                                                              "reviewer": reviewer(request)})


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    po_id = ingest(data, file.filename or "upload.bin")
    return RedirectResponse(f"/po/{po_id}", status_code=303)


@app.post("/api/po")
async def api_upload(file: UploadFile = File(...), sender_email: str | None = Form(None)):
    po_id = ingest(await file.read(), file.filename or "upload.bin", sender_email)
    row, po = load(po_id)
    return {"id": po_id, "status": row["status"], "po": po.model_dump()}


@app.get("/api/po/{po_id}")
def api_get(po_id: int):
    row, po = load(po_id)
    return {"id": po_id, "status": row["status"], "erp_ref": row["erp_ref"], "po": po.model_dump()}


@app.get("/po/{po_id}", response_class=HTMLResponse)
def review(request: Request, po_id: int):
    return render_review(request, po_id)


@app.get("/po/{po_id}/file")
def original(po_id: int):
    row, _ = load(po_id)
    f = store().get_file(row["file_sha"]) if row["file_sha"] else None
    if not f:
        raise HTTPException(404, "no file")
    return Response(f["data"], media_type=f["mime"],
                    headers={"Content-Disposition": f'inline; filename="{f["name"]}"'})


@app.get("/po/{po_id}/preview.png")
def preview(po_id: int, page: int = 0):
    """First page of a PDF as an image: works on phones and headless browsers,
    which often cannot show PDFs inline."""
    import io

    import pypdfium2 as pdfium

    row, _ = load(po_id)
    f = store().get_file(row["file_sha"]) if row["file_sha"] else None
    if not f or not f["name"].lower().endswith(".pdf"):
        raise HTTPException(404, "no PDF")
    pdf = pdfium.PdfDocument(f["data"])
    if not 0 <= page < len(pdf):
        raise HTTPException(404, "no such page")
    img = pdf[page].render(scale=1.6).to_pil()
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


def _guard_open(row: dict) -> None:
    if row["status"] in ("approved", "rejected"):
        raise HTTPException(409, f"this PO is already {row['status']}")


@app.post("/po/{po_id}/line/{idx}", response_class=HTMLResponse)
def edit_line(request: Request, po_id: int, idx: int, sku: str = Form(""), qty: float = Form(...),
              unit: str = Form(""), remove: str = Form("")):
    row, po = load(po_id)
    _guard_open(row)
    if not 0 <= idx < len(po.lines):
        raise HTTPException(404, "line not found")
    ln = po.lines[idx]
    before = {"sku": ln.sku, "qty": ln.qty, "unit": ln.unit}
    if remove:
        po.lines.pop(idx)
        action, detail = "line_removed", {"line": idx + 1, **before, "raw": ln.raw_name}
    else:
        if qty <= 0:
            raise HTTPException(422, "quantity must be positive")
        new_sku = sku or None
        if new_sku and new_sku not in products():
            raise HTTPException(422, "unknown SKU")
        if new_sku != ln.sku and new_sku:
            # the correction becomes an alias for this shop: next time it matches by itself
            store().put(po.shop_id, ln.raw_name, new_sku, "admin")
            ln.method, ln.confidence = "admin", 1.0
        ln.sku, ln.qty, ln.unit = new_sku, qty, unit or None
        ln.product_name = products()[new_sku].name if new_sku else None
        action, detail = "line_edited", {"line": idx + 1, "before": before,
                                         "after": {"sku": ln.sku, "qty": ln.qty, "unit": ln.unit}}
    po = evaluate(po, store(), exclude_id=po_id)
    store().update_payload(po_id, po, reviewer(request), action, detail)
    return render_review(request, po_id, partial=True)


@app.post("/po/{po_id}/header", response_class=HTMLResponse)
def edit_header(request: Request, po_id: int, shop_id: str = Form(""), po_number: str = Form("")):
    row, po = load(po_id)
    _guard_open(row)
    if shop_id and shop_id not in shops():
        raise HTTPException(422, "unknown customer")
    before = {"shop_id": po.shop_id, "po_number": po.po_number}
    if shop_id and shop_id != po.shop_id:
        po.shop_id, po.shop_name, po.shop_confidence = shop_id, shops()[shop_id].name, 1.0
    po.po_number = po_number.strip() or None
    po = evaluate(po, store(), exclude_id=po_id)
    store().update_payload(po_id, po, reviewer(request), "header_edited",
                           {"before": before, "after": {"shop_id": po.shop_id, "po_number": po.po_number}})
    return render_review(request, po_id, partial=True)


@app.post("/po/{po_id}/approve", response_class=HTMLResponse)
def approve(request: Request, po_id: int):
    row, po = load(po_id)
    if row["status"] == "approved":  # double click / retry: same answer, nothing new
        return render_review(request, po_id, f"Already approved as {row['erp_ref']}.", partial=True)
    _guard_open(row)
    po = evaluate(po, store(), exclude_id=po_id)
    if po.status == "blocked":
        return render_review(request, po_id, "Blocked issues must be fixed before approval.", partial=True)
    try:
        ref = get_adapter(store()).create_draft_order(po, idempotency_key(po, po_id))
    except ERPError as e:
        store().update_payload(po_id, po, reviewer(request), "erp_failed", {"error": str(e)})
        return render_review(request, po_id, f"ERP error, nothing was created: {e}", partial=True)
    store().decide(po_id, "approved", reviewer(request), erp_ref=ref,
                   detail={"warnings": [f.code for f in po.flags]})
    return render_review(request, po_id, f"Draft sales order {ref} created in the ERP.", partial=True)


@app.post("/po/{po_id}/reject", response_class=HTMLResponse)
def reject(request: Request, po_id: int, reason: str = Form("")):
    row, _ = load(po_id)
    _guard_open(row)
    store().decide(po_id, "rejected", reviewer(request), detail={"reason": reason[:300]})
    return render_review(request, po_id, "PO rejected.", partial=True)


@app.post("/intake/email")
def intake_email():
    from ..intake_email import poll_mailpit
    try:
        result = poll_mailpit(ingest)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    return result


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.headers.get("hx-request") or request.url.path.startswith(("/api", "/intake")):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    return templates.TemplateResponse(request, "error.html", {"code": exc.status_code, "detail": exc.detail},
                                      status_code=exc.status_code)
