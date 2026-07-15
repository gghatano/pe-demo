"""Aggregate per-experiment summary records into unified tables (issue #6).

Reads every ``results/summaries/{smoke_,experiment_,xor_}*.json`` record, normalizes
them into a single tidy table, and writes:

- ``results/summaries/experiments.csv``
- ``results/summaries/experiments.json``

It also extracts per-iteration metric time series from the harvested official
``log.txt`` files (``results/raw/**/log.txt``) into
``results/summaries/iterations/<key>.csv`` so that figures can be regenerated from
tracked data without re-running experiments.

Note: the official ``CSVPrint`` logger writes one file per metric named after the
metric, and tabular metric names embed a filter dict containing ``:`` — illegal in
Windows filenames — so those per-iteration CSVs come out empty on Windows. We
therefore parse the time series from ``log.txt`` instead.

Usage:
    uv run python scripts/collect_results.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARIES = REPO_ROOT / "results" / "summaries"
RAW = REPO_ROOT / "results" / "raw"

# Columns for the tidy experiments table.
COLUMNS = [
    "experiment", "dataset", "command", "status", "runtime_s", "classifier",
    "test_acc", "test_f1", "test_auc", "wsd", "epsilon", "delta", "notes",
]


def _find_final_metrics(record: dict) -> dict:
    """Locate a ``final_metrics`` dict nested anywhere in a record's artifacts."""
    arts = record.get("artifacts", {})
    if isinstance(arts, dict):
        for v in arts.values():
            if isinstance(v, dict) and "final_metrics" in v:
                return v["final_metrics"]
    return {}


def _wsd_string(fm: dict) -> str:
    degs = [(int(k.split("_")[1].replace("way", "")), v)
            for k, v in fm.items() if k.startswith("wsd_")]
    degs.sort()
    return "; ".join(f"{d}-way={v:.4f}" for d, v in degs)


def normalize(path: Path) -> dict:
    rec = json.loads(path.read_text(encoding="utf-8"))
    fm = _find_final_metrics(rec)
    priv = rec.get("privacy_parameters", {})

    # Classifier accuracy: prefer parsed final metric; else explicit metrics field.
    acc = fm.get("classifier_test_acc")
    notes_bits = []
    if acc is None:
        m = rec.get("metrics", {})
        raw_acc = m.get("classifier_test_acc")
        if isinstance(raw_acc, str):
            notes_bits.append(f"classifier: {raw_acc}")
    if rec.get("failure_reason"):
        notes_bits.append(rec["failure_reason"])
    if rec.get("deviation"):
        notes_bits.append(f"deviation: {rec['deviation']}")

    dp = fm.get("dp", {})
    return {
        "experiment": rec.get("experiment_name", path.stem),
        "dataset": rec.get("dataset_name", ""),
        "command": rec.get("command", ""),
        "status": rec.get("reproduction_status", ""),
        "runtime_s": rec.get("runtime_seconds", ""),
        "classifier": rec.get("classifier_model") or "",
        "test_acc": acc if isinstance(acc, (int, float)) else "",
        "test_f1": fm.get("classifier_test_f1", ""),
        "test_auc": fm.get("classifier_test_auc", ""),
        "wsd": _wsd_string(fm),
        "epsilon": dp.get("epsilon", priv.get("epsilon", "")),
        "delta": dp.get("delta", priv.get("delta", "")),
        "notes": " | ".join(notes_bits),
        "_source_json": str(path.relative_to(REPO_ROOT)),
    }


# --- per-iteration series ---------------------------------------------------

ITER_RE = re.compile(r"PE iteration (\d+)")
ACC_RE = re.compile(r"Tabular classifier test accuracy:\s*([\d.]+)%")
F1_RE = re.compile(r"Tabular classifier test \(macro\) F1 score:\s*([\d.]+)")
WSD_RE = re.compile(r"(\d)way-wsd_\d+samples_\d+seed[^\n]*:\s*([\d.]+)")


def extract_iterations(log_txt: Path) -> list[dict]:
    """Parse a per-iteration series from an official log. Iteration 0 is the initial
    data; subsequent blocks follow each 'PE iteration N' marker."""
    text = log_txt.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rows: list[dict] = []
    cur = {"iteration": 0}
    seen_metric = False

    def flush():
        nonlocal cur, seen_metric
        if seen_metric:
            rows.append(cur)
        seen_metric = False

    for ln in lines:
        mi = ITER_RE.search(ln)
        if mi:
            flush()
            cur = {"iteration": int(mi.group(1))}
            continue
        ma = ACC_RE.search(ln)
        if ma:
            cur["test_acc"] = float(ma.group(1)); seen_metric = True
        mf = F1_RE.search(ln)
        if mf:
            cur["test_f1"] = float(mf.group(1)); seen_metric = True
        mw = WSD_RE.search(ln)
        if mw:
            cur[f"wsd_{mw.group(1)}way"] = float(mw.group(2)); seen_metric = True
    flush()
    return rows


def main() -> int:
    SUMMARIES.mkdir(parents=True, exist_ok=True)
    records = []
    for pat in ("smoke_*.json", "experiment_*.json", "xor_*.json"):
        for p in sorted(SUMMARIES.glob(pat)):
            if p.name in ("experiments.json",):
                continue
            records.append(normalize(p))

    # Stable ordering: EXECUTED/REPRODUCED first, then FAILED/other, by name.
    order = {"REPRODUCED": 0, "PARTIALLY_REPRODUCED": 1, "EXECUTED": 2, "FAILED": 3, "NOT_RUN": 4}
    records.sort(key=lambda r: (order.get(r["status"], 9), r["experiment"]))

    (SUMMARIES / "experiments.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    with (SUMMARIES / "experiments.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in COLUMNS})

    # Per-iteration series from harvested logs.
    iters_dir = SUMMARIES / "iterations"
    iters_dir.mkdir(exist_ok=True)
    series_written = []
    for log_txt in sorted(RAW.glob("**/log.txt")):
        rows = extract_iterations(log_txt)
        if not rows:
            continue
        # Key by the experiment folder name.
        key = log_txt.parent.name
        cols = ["iteration"] + sorted({k for r in rows for k in r if k != "iteration"})
        out = iters_dir / f"{key}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        series_written.append(out.relative_to(REPO_ROOT))

    print(f"experiments: {len(records)} rows -> results/summaries/experiments.{{csv,json}}")
    for s in series_written:
        print(f"iterations  -> {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
