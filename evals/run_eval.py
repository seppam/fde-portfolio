"""Eval harness: run the real pipeline on the 30-PO golden set and score it.

Two passes over the same extractions:
  cold   - empty alias table (day one at the client)
  learn  - after each PO, the "admin" fixes wrong SKUs and the fixes become
           aliases, like the review screen does. Shows how fast the agent learns.

Writes experiments/<run>.json, experiments/latest.md and appends experiments/history.csv.
Run: uv run python evals/run_eval.py [--no-llm-match] [--workers 3] [--note "..."]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from po_agent.extract import extract
from po_agent.pipeline import build
from po_agent.rules import SCENARIO_CODES
from po_agent.store import Store, po_key

GOLD = ROOT / "data" / "golden"
EXP = ROOT / "experiments"


def norm_no(s: str | None) -> str | None:
    return po_key(s)


def align(pred_lines, truth_lines):
    """Pair each truth line with the most similar predicted line (by written name)."""
    used, pairs = set(), []
    for t in truth_lines:
        best, best_s = None, 0
        for j, p in enumerate(pred_lines):
            if j in used:
                continue
            s = fuzz.ratio(t["raw_name"].lower(), p.raw_name.lower())
            if s > best_s:
                best, best_s = j, s
        if best is not None and best_s >= 60:
            used.add(best)
            pairs.append((t, pred_lines[best]))
        else:
            pairs.append((t, None))
    return pairs, len(pred_lines) - len(used)


def score_po(lab: dict, po) -> dict:
    t = lab["truth"]
    pairs, extra = align(po.lines, t["lines"])
    found = sum(1 for _, p in pairs if p is not None)
    sku_ok = sum(1 for tl, p in pairs if p is not None and p.sku == tl["sku"])
    qty_ok = sum(1 for tl, p in pairs if p is not None and p.qty == tl["qty"] and p.unit == tl["unit"])
    raised = {f.code for f in po.flags} & SCENARIO_CODES
    expected = set(t["expected_flags"])
    header_ok = (po.shop_id == t["shop_id"] and norm_no(po.po_number) == norm_no(t["po_number"])
                 and po.po_date == t["po_date"])
    flagged_lines = {f.line for f in po.flags if f.line}
    silent = sum(1 for tl, p in pairs if p is not None and p.sku is not None and p.sku != tl["sku"]
                 and (po.lines.index(p) + 1) not in flagged_lines)
    lines_ok = found == len(t["lines"]) and extra == 0 and sku_ok == qty_ok == len(t["lines"])
    return {
        "id": lab["id"], "format": lab["format"], "scenario": lab["scenario"],
        "shop_ok": po.shop_id == t["shop_id"], "po_number_ok": norm_no(po.po_number) == norm_no(t["po_number"]),
        "date_ok": po.po_date == t["po_date"], "lines_truth": len(t["lines"]), "lines_found": found,
        "lines_extra": extra, "sku_ok": sku_ok, "qty_unit_ok": qty_ok,
        "expected_flags": sorted(expected), "raised_flags": sorted(raised),
        "missed_flags": sorted(expected - raised), "false_flags": sorted(raised - expected),
        "zero_edit": header_ok and lines_ok, "status": po.status, "silent_errors": silent,
        "methods": [p.method for _, p in pairs if p is not None],
        "wrong_lines": [{"written": tl["raw_name"], "truth": tl["sku"], "got": p.sku if p else None,
                         "qty": [tl["qty"], tl["unit"], p.qty if p else None, p.unit if p else None]}
                        for tl, p in pairs if p is None or p.sku != tl["sku"] or p.qty != tl["qty"] or p.unit != tl["unit"]],
    }


def run_pass(labels, extractions, learn: bool, use_llm: bool) -> list[dict]:
    store = Store("sqlite://")
    results = []
    for lab in labels:
        ex = extractions[lab["id"]]
        po = build(ex.po.model_copy(deep=True), ex.usage.model_copy(), lab["file"], store, use_llm=use_llm)
        results.append(score_po(lab, po))
        po_id = store.save(po)
        if learn:  # the admin fixes wrong SKUs on the review screen, then approves
            pairs, _ = align(po.lines, lab["truth"]["lines"])
            for tl, p in pairs:
                if p is not None and tl["sku"] and p.sku != tl["sku"]:
                    store.put(lab["truth"]["shop_id"], p.raw_name, tl["sku"], "admin")
                    p.sku = tl["sku"]
            po.shop_id = lab["truth"]["shop_id"]
            store.update_payload(po_id, po, "eval-admin", "corrected", {})
            store.decide(po_id, "approved", "eval-admin")
    return results


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    lines = sum(r["lines_truth"] for r in rows)
    flag_exp = sum(len(r["expected_flags"]) for r in rows)
    return {
        "pos": n,
        "shop_acc": round(sum(r["shop_ok"] for r in rows) / n, 3),
        "po_number_acc": round(sum(r["po_number_ok"] for r in rows) / n, 3),
        "date_acc": round(sum(r["date_ok"] for r in rows) / n, 3),
        "line_recall": round(sum(r["lines_found"] for r in rows) / lines, 3),
        "extra_lines": sum(r["lines_extra"] for r in rows),
        "sku_acc": round(sum(r["sku_ok"] for r in rows) / lines, 3),
        "qty_unit_acc": round(sum(r["qty_unit_ok"] for r in rows) / lines, 3),
        "flag_recall": round(sum(len(r["expected_flags"]) - len(r["missed_flags"]) for r in rows) / flag_exp, 3),
        "false_flags": sum(len(r["false_flags"]) for r in rows),
        "zero_edit_rate": round(sum(r["zero_edit"] for r in rows) / n, 3),
        "silent_errors": sum(r["silent_errors"] for r in rows),
        "by_format": {f: round(sum(r["zero_edit"] for r in rows if r["format"] == f) /
                               max(1, sum(1 for r in rows if r["format"] == f)), 3)
                      for f in ("pdf", "image", "xlsx")},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm-match", action="store_true", help="fuzzy only, no LLM tie-break")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    labels = [json.loads(p.read_text()) for p in sorted((GOLD / "labels").glob("po_*.json"))]
    t0 = time.monotonic()

    def do(lab):
        data = (GOLD / "files" / lab["file"]).read_bytes()
        for attempt in range(3):
            try:
                return lab["id"], extract(data, lab["file"])
            except Exception as e:  # keep going; a failed PO counts as all wrong
                err = e
                time.sleep(5 * (attempt + 1))
        raise SystemExit(f"{lab['id']}: extraction failed: {err}")

    with ThreadPoolExecutor(args.workers) as pool:
        extractions = dict(pool.map(do, labels))
    use_llm = not args.no_llm_match
    cold = run_pass(labels, extractions, learn=False, use_llm=use_llm)
    learn = run_pass(labels, extractions, learn=True, use_llm=use_llm)

    usages = [e.usage for e in extractions.values()]
    fresh = [u for u in usages if not u.cached]
    run = {
        "run": datetime.now().strftime("%Y%m%d-%H%M%S"), "note": args.note, "llm_match": use_llm,
        "models": sorted({f"{u.provider}/{u.model}" for u in usages}),
        "tokens_in": sum(u.input_tokens for u in usages), "tokens_out": sum(u.output_tokens for u in usages),
        "avg_extract_latency_ms": int(sum(u.latency_ms for u in fresh) / len(fresh)) if fresh else None,
        "cached_extractions": len(usages) - len(fresh), "wall_s": round(time.monotonic() - t0, 1),
        "cold": summarize(cold), "learn": summarize(learn), "rows_cold": cold, "rows_learn": learn,
    }
    EXP.mkdir(exist_ok=True)
    (EXP / f"eval-{run['run']}.json").write_text(json.dumps(run, indent=2, ensure_ascii=False))
    hist = EXP / "history.csv"
    new = not hist.exists()
    with hist.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run", "note", "llm_match", "models", "shop_acc", "sku_acc", "qty_unit_acc",
                        "flag_recall", "false_flags", "zero_edit_cold", "zero_edit_learn", "tokens_in", "tokens_out"])
        c, lr = run["cold"], run["learn"]
        w.writerow([run["run"], args.note, use_llm, " ".join(run["models"]), c["shop_acc"], c["sku_acc"],
                    c["qty_unit_acc"], c["flag_recall"], c["false_flags"], c["zero_edit_rate"],
                    lr["zero_edit_rate"], run["tokens_in"], run["tokens_out"]])
    md = [f"# Eval {run['run']}", "", f"Models: {', '.join(run['models'])}  ", f"LLM tie-break: {use_llm}  ",
          f"Tokens: {run['tokens_in']} in / {run['tokens_out']} out  ",
          f"Avg extraction latency (uncached): {run['avg_extract_latency_ms']} ms", "",
          "| metric | cold start | with learned aliases |", "|---|---|---|"]
    for k in ("shop_acc", "po_number_acc", "date_acc", "line_recall", "extra_lines", "sku_acc",
              "qty_unit_acc", "flag_recall", "false_flags", "silent_errors", "zero_edit_rate"):
        md.append(f"| {k} | {run['cold'][k]} | {run['learn'][k]} |")
    md += ["", "Zero-edit rate by format (cold): " + json.dumps(run["cold"]["by_format"]), "",
           "## Misses (cold)", ""]
    for r in cold:
        if not r["zero_edit"] or r["missed_flags"] or r["false_flags"]:
            md.append(f"- **{r['id']}** ({r['format']}, {r['scenario']}): missed {r['missed_flags']} "
                      f"false {r['false_flags']} wrong lines {json.dumps(r['wrong_lines'], ensure_ascii=False)}"
                      + ("" if r["shop_ok"] else " shop wrong") + ("" if r["po_number_ok"] else " po_number wrong")
                      + ("" if r["date_ok"] else " date wrong"))
    (EXP / "latest.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:20]))


if __name__ == "__main__":
    main()
