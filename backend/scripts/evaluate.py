"""
Measures extraction + flagging accuracy of the pipeline against ground truth.

    python scripts/evaluate.py                 # uses sample_data/ + ground_truth.json
    python scripts/evaluate.py --md            # also writes docs/EVALUATION.md
    python scripts/evaluate.py --dir my_reports --truth my_truth.json

Ground-truth file format (same as sample_data/ground_truth.json):
  { "report.txt": { "layout": 0, "params": { "hemoglobin": {"value": 13.2, "status": "normal"} } } }
  canonical names = keys of app.reference_ranges.REFERENCE_RANGES
  value  = number in the standard table unit;  status = low | normal | high

To measure on REAL reports: put de-identified report files (.txt, or extract
text from PDFs/images first) in a folder, hand-label 15-20 values per report in
the JSON above, and run with --dir / --truth. That number is your real accuracy.

Runs in rule-based mode (no API key) so results are deterministic.
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.pop("ANTHROPIC_API_KEY", None)

from app.models import PipelineState  # noqa: E402
from app.pipeline import run_pipeline  # noqa: E402
from app.reference_ranges import normalize_parameter_name  # noqa: E402


def collapse(status: str) -> str:
    return "low" if "low" in status else "high" if "high" in status else status


def canon(name: str, truth_keys):
    k = name.lower()
    return k if k in truth_keys else normalize_parameter_name(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "sample_data"))
    ap.add_argument("--truth", default=None)
    ap.add_argument("--md", action="store_true", help="write docs/EVALUATION.md")
    args = ap.parse_args()

    folder = Path(args.dir)
    truth_path = Path(args.truth) if args.truth else folder / "ground_truth.json"
    gt = json.loads(truth_path.read_text())

    tot = found = val_ok = stat_ok = spurious = extracted_total = 0
    abn_truth = abn_hit = abn_pred = 0
    conf = defaultdict(int)
    by_layout = defaultdict(lambda: [0, 0, 0, 0])   # expected, found, value_ok, status_ok
    misses = []
    times = []

    for fname, meta in sorted(gt.items()):
        text = (folder / fname).read_text()
        t0 = time.time()
        st = run_pipeline(PipelineState(raw_text=text, file_type="text"))
        times.append(time.time() - t0)
        got = {}
        for p in st.extracted.parameters:
            c = canon(p.name, meta["params"])
            if c in meta["params"] and c not in got:
                got[c] = p
            else:
                spurious += 1
            extracted_total += 1
        for c, tr in meta["params"].items():
            tot += 1
            L = by_layout[meta.get("layout", 0)]
            L[0] += 1
            p = got.get(c)
            if p is None:
                misses.append((fname, c, "not extracted"))
                if tr["status"] != "normal":
                    abn_truth += 1
                continue
            found += 1
            L[1] += 1
            ok_v = p.value is not None and abs(p.value - tr["value"]) <= 0.01 * max(abs(tr["value"]), 1e-9)
            val_ok += ok_v
            L[2] += ok_v
            if not ok_v:
                misses.append((fname, c, f"value {p.value} {p.unit} != {tr['value']}"))
            pred = collapse(p.status)
            ok_s = pred == tr["status"]
            stat_ok += ok_s
            L[3] += ok_s
            if not ok_s:
                conf[(tr["status"], pred)] += 1
                misses.append((fname, c, f"status {pred} != {tr['status']}"))
            if tr["status"] != "normal":
                abn_truth += 1
                abn_hit += ok_s
            if pred != "normal":
                abn_pred += 1

    pct = lambda a, b: f"{(a / b * 100 if b else 0):.1f}%"  # noqa: E731
    abn_correct_pred = abn_hit
    lines = [
        f"Reports: {len(gt)}   Expected values: {tot}   (SYNTHETIC data unless you passed real labelled reports)",
        f"Extraction recall (value found):        {found}/{tot} = {pct(found, tot)}",
        f"Value correct (within 1%, std units):   {val_ok}/{found} = {pct(val_ok, found)}",
        f"Status correct (low/normal/high):       {stat_ok}/{found} = {pct(stat_ok, found)}",
        f"Abnormal recall  (flagged / truly abn): {abn_hit}/{abn_truth} = {pct(abn_hit, abn_truth)}",
        f"Abnormal precision (correct / flagged): {abn_correct_pred}/{abn_pred} = {pct(abn_correct_pred, abn_pred)}",
        f"Spurious / unmatched parameters:        {spurious} of {extracted_total} extracted rows",
        f"Avg pipeline time (rule-based):         {sum(times) / len(times) * 1000:.0f} ms/report",
        "Status confusions (truth -> predicted): " + (", ".join(f"{a}->{b}: {n}" for (a, b), n in conf.items()) or "none"),
        "",
        "Per layout   (expected / found / value-ok / status-ok)",
    ]
    names = {0: "colon list", 1: "spaced table", 2: "pipe table + flags", 3: "Indian-lab style"}
    for k in sorted(by_layout):
        e, f, v, s = by_layout[k]
        lines.append(f"  layout {k} ({names.get(k, '?')}): {e} / {f} / {v} / {s}   -> status acc {pct(s, f)}")
    if misses:
        lines += ["", f"First {min(15, len(misses))} misses:"] + [f"  {a}: {b} -> {c}" for a, b, c in misses[:15]]
    out = "\n".join(lines)
    print(out)

    if args.md:
        md = ROOT.parent / "docs" / "EVALUATION.md"
        md.write_text("# Evaluation results\n\nGenerated by `backend/scripts/evaluate.py`.\n\n```\n" + out + "\n```\n")
        print(f"\nWrote {md}")


if __name__ == "__main__":
    main()
