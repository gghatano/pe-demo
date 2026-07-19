"""Audit trail from published numbers to their source logs (issue #19).

The published numbers live in ``results/summaries/*.json``; the underlying logs and
artifacts live under ``results/raw/`` and ``results/logs/`` which are gitignored
(large, and absent on a clean clone). This tool makes the trail auditable:

  build (default)  For every summary, resolve its source log, and (when present
                   locally) record size + SHA-256 and re-parse the metrics from the
                   log to confirm they match the published values. Writes the tracked
                   manifest results/summaries/audit_manifest.json.
  --verify         Re-check the manifest: for every entry whose file is present,
                   the SHA-256 must still match and (for log.txt entries) the
                   re-parsed metrics must match the summary. Missing files are
                   reported but not fatal (expected on a clean clone; regenerate via
                   the recorded command). Exits non-zero on any mismatch.
  --fix-paths      One-off: normalize path fields in the summary JSONs to clean
                   POSIX (collapses stray '\\'/'//' separators; leaves URLs alone).

A clean-clone reviewer verifies a published number by re-running the recorded
`command` and comparing the parsed metrics (byte-identical logs are not expected —
logs carry timestamps); the SHA-256 pins the integrity of our stored artifact.

Run:
    uv run python scripts/audit_results.py            # build manifest
    uv run python scripts/audit_results.py --verify   # check integrity
    uv run python scripts/audit_results.py --fix-paths
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_smoke import parse_final_metrics  # noqa: E402

SUMMARIES = REPO_ROOT / "results" / "summaries"
MANIFEST = SUMMARIES / "audit_manifest.json"
# Summaries that are not single-experiment records (skip for the per-run trail).
SKIP = {"experiments.json", "audit_manifest.json",
        "adult_embedding_seed_aggregate.json", "scm_seed_aggregate.json"}
PATH_KEYS = ("log_relpath", "console_log", "copied_to", "_source_json")
TOL = 1e-6


def _norm_path(p: str) -> str:
    """Collapse OS-native / doubled separators to single POSIX slashes. Leaves a
    scheme like http:// untouched."""
    if "://" in p:
        return p
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    return p


def _sha256(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def _primary_log(rec: dict) -> str | None:
    art = rec.get("artifacts") or {}
    for cand in (art.get("log_relpath"), rec.get("console_log")):
        if isinstance(cand, str) and cand:
            return _norm_path(cand)
    return None


def _iter_summaries():
    for f in sorted(SUMMARIES.glob("*.json")):
        if f.name in SKIP or "_ceiling" in f.name:
            continue
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(rec, dict):
            yield f, rec


def _experiments_by_source() -> dict:
    """Map normalized _source_json -> published experiments.json row."""
    exp = SUMMARIES / "experiments.json"
    if not exp.exists():
        return {}
    out = {}
    for r in json.loads(exp.read_text(encoding="utf-8")):
        if isinstance(r, dict) and r.get("_source_json"):
            out[_norm_path(r["_source_json"])] = r
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _metric_check(summary_rel: str, log_rel: str, fm: dict, exp_row: dict | None) -> dict | None:
    """Re-parse the source log (log.txt or console log) and confirm the published
    numbers trace to it. Prefers the summary's own final_metrics; for console-log
    runs whose summary has none, cross-checks the published experiments.json row."""
    log = REPO_ROOT / log_rel
    if not log.exists():
        return None
    parsed = parse_final_metrics(log)
    if not parsed:
        return None
    if fm:  # summary carries its own metrics (newer runners)
        keys, target, against = [], {}, "summary.final_metrics"
        for k, v in fm.items():
            if isinstance(v, (int, float)):
                target[k] = v
        mism = [k for k, v in target.items()
                if k in parsed and abs(float(parsed[k]) - float(v)) > TOL]
        return {"against": against, "match": not mism, "mismatched_keys": mism}
    if exp_row:  # console-log runs: verify the published table row
        pairs = {"classifier_test_acc": "test_acc",
                 "classifier_test_f1": "test_f1",
                 "classifier_test_auc": "test_auc"}
        mism = []
        for pk, ek in pairs.items():
            pv, ev = parsed.get(pk), _num(exp_row.get(ek))
            if pv is not None and ev is not None and abs(float(pv) - ev) > 1e-2:
                mism.append(ek)
        if not any(_num(exp_row.get(ek)) is not None for ek in pairs.values()):
            return None
        return {"against": "experiments.json", "match": not mism, "mismatched_keys": mism}
    return None


def build() -> int:
    exp_map = _experiments_by_source()
    entries = []
    for f, rec in _iter_summaries():
        log_rel = _primary_log(rec)
        entry = {
            "summary": f.relative_to(REPO_ROOT).as_posix(),
            "experiment_name": rec.get("experiment_name") or rec.get("kind") or f.stem,
            "reproduction_status": rec.get("reproduction_status"),
            "command": rec.get("command"),
            "log": log_rel,
            "present": False, "size_bytes": None, "sha256": None, "metric_check": None,
        }
        if log_rel:
            log = REPO_ROOT / log_rel
            if log.exists():
                sha, size = _sha256(log)
                entry.update(present=True, size_bytes=size, sha256=sha)
                entry["metric_check"] = _metric_check(
                    entry["summary"], log_rel, rec.get("final_metrics") or {},
                    exp_map.get(entry["summary"]))
        entries.append(entry)

    present = sum(e["present"] for e in entries)
    checked = [e for e in entries if e.get("metric_check")]
    matched = sum(e["metric_check"]["match"] for e in checked)
    manifest = {
        "note": ("SHA-256 pins the integrity of our locally-stored logs; results/raw "
                 "and results/logs are gitignored. Reproduce a number by re-running "
                 "`command` and comparing parsed metrics (logs carry timestamps, so "
                 "they are not byte-identical). See docs/engineering-notes.md."),
        "totals": {"summaries": len(entries), "logs_present": present,
                   "metrics_checked": len(checked), "metrics_matched": matched},
        "entries": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(REPO_ROOT)}: {len(entries)} summaries, "
          f"{present} logs present, {matched}/{len(checked)} metric-verified")
    if checked and matched != len(checked):
        for e in checked:
            if not e["metric_check"]["match"]:
                print(f"  MISMATCH {e['summary']} keys={e['metric_check']['mismatched_keys']}")
        return 1
    return 0


def verify() -> int:
    if not MANIFEST.exists():
        print("no manifest; run `python scripts/audit_results.py` first", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    exp_map = _experiments_by_source()
    bad, present, missing = 0, 0, 0
    for e in manifest["entries"]:
        log_rel = e.get("log")
        if not log_rel:
            continue
        log = REPO_ROOT / log_rel
        if not log.exists():
            missing += 1
            continue
        present += 1
        sha, size = _sha256(log)
        if e.get("sha256") and sha != e["sha256"]:
            print(f"  HASH MISMATCH {e['summary']} ({log_rel})")
            bad += 1
            continue
        # Re-verify metrics against the summary / published table directly.
        summ = REPO_ROOT / e["summary"]
        if summ.exists():
            rec = json.loads(summ.read_text(encoding="utf-8"))
            chk = _metric_check(e["summary"], log_rel, rec.get("final_metrics") or {},
                                exp_map.get(e["summary"]))
            if chk and not chk["match"]:
                print(f"  METRIC MISMATCH {e['summary']} keys={chk['mismatched_keys']}")
                bad += 1
    print(f"verify: {present} present, {missing} missing (regenerate via command), {bad} bad")
    return 1 if bad else 0


def fix_paths() -> int:
    changed = 0
    for f, rec in _iter_summaries():
        text = f.read_text(encoding="utf-8")
        rec = json.loads(text)

        def _walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in PATH_KEYS and isinstance(v, str):
                        o[k] = _norm_path(v)
                    else:
                        _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)

        _walk(rec)
        new = json.dumps(rec, indent=2) + ("\n" if text.endswith("\n") else "")
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
    # experiments.json is a list of records with _source_json.
    exp = SUMMARIES / "experiments.json"
    if exp.exists():
        text = exp.read_text(encoding="utf-8")
        data = json.loads(text)
        for r in data:
            if isinstance(r, dict) and isinstance(r.get("_source_json"), str):
                r["_source_json"] = _norm_path(r["_source_json"])
        new = json.dumps(data, indent=2) + ("\n" if text.endswith("\n") else "")
        if new != text:
            exp.write_text(new, encoding="utf-8")
            changed += 1
    print(f"normalized path fields in {changed} files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--fix-paths", action="store_true")
    args = ap.parse_args()
    if args.fix_paths:
        return fix_paths()
    if args.verify:
        return verify()
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
