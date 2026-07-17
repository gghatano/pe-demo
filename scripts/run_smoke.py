"""Smoke test for an official DPSDA Tab-PE demo (issue #2).

Runs an *unmodified* official example script from a pinned DPSDA checkout under
``external/DPSDA/example/tabular/``, captures reproducibility metadata and
runtime, harvests the produced artifacts into ``results/raw/<key>/`` and writes a
machine-readable record to ``results/summaries/smoke_<key>.json``.

This does not modify the official algorithm; it only orchestrates execution and
records evidence. See docs/research/official-implementation.md.

Default target is ``breast_cancer.py`` (uses the ``tabicl`` classifier, which
downloads weights from the HuggingFace Hub without a license gate). The XOR demo
is intentionally not the default because it hardcodes the ``tabpfn`` classifier,
which requires a one-time interactive license acceptance / API token to download
weights (see reproduction log).

Usage:
    uv run python scripts/run_smoke.py                      # breast_cancer.py
    uv run python scripts/run_smoke.py --script scm.py --arg --prior-function rff
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"

REPO_ROOT = Path(__file__).resolve().parents[1]
DPSDA_DIR = REPO_ROOT / "external" / "DPSDA"
EXAMPLE_DIR = DPSDA_DIR / "example" / "tabular"
TABULAR_RESULTS = EXAMPLE_DIR / "results" / "tabular"

# Static facts per demo (from docs/research/official-implementation.md).
DEMO_META = {
    "breast_cancer.py": {
        "classifier": "tabicl",
        "dataset": "Breast Cancer (real)",
        "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/breast-cancer/",
    },
    "scm.py": {
        "classifier": "tabicl",
        "dataset": "SCM (simulated)",
        "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/sim/scm/",
    },
    "xor_stress_test.py": {
        "classifier": "tabpfn",
        "dataset": "XOR stress test (simulated)",
        "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/sim/xor-stress-test/",
    },
}


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def _tool_version(args: list[str]) -> str | None:
    try:
        out = subprocess.run(args, capture_output=True, text=True, check=True)
        return (out.stdout or out.stderr).strip()
    except Exception:
        return None


def parse_final_metrics(log_txt: Path) -> dict[str, object]:
    """Extract the last-iteration classifier + WSD + DP metrics from an official
    ``log.txt``. Returns {} if the file is missing."""
    import re

    if not log_txt.exists():
        return {}
    text = log_txt.read_text(encoding="utf-8", errors="replace")
    out: dict[str, object] = {}

    def _last(pattern: str) -> str | None:
        matches = re.findall(pattern, text)
        return matches[-1] if matches else None

    acc = _last(r"Tabular classifier test accuracy:\s*([\d.]+)%")
    f1 = _last(r"Tabular classifier test \(macro\) F1 score:\s*([\d.]+)")
    auc = _last(r"Tabular classifier test AUC:\s*([\d.]+)")
    if acc:
        out["classifier_test_acc"] = float(acc)
    if f1:
        out["classifier_test_f1"] = float(f1)
    if auc:
        out["classifier_test_auc"] = float(auc)
    for deg in range(1, 8):
        # The metric line may embed a filter-criterion dict that itself contains a
        # colon, so match greedily up to the last ": <value>" on the line.
        v = _last(rf"{deg}way-wsd_\d+samples_\d+seed[^\n]*:\s*([\d.]+)")
        if v:
            out[f"wsd_{deg}way"] = float(v)
    # epsilon may be printed as "inf" (no-DP / epsilon=inf case).
    dp = _last(r"DP epsilon=(inf|[\d.]+), delta=([\d.eE+-]+), noise_multiplier=([\d.]+), num_iterations=(\d+)")
    if dp:
        out["dp"] = {
            "epsilon": float(dp[0]),
            "delta": float(dp[1]),
            "noise_multiplier": float(dp[2]),
            "accounted_num_iterations": int(dp[3]),
        }
    return out


def _failure_reason(stderr: str) -> str | None:
    """Best-effort one-line failure summary: the final exception line from stderr."""
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
    if not lines:
        return None
    for ln in reversed(lines):
        if "Error" in ln or "Exception" in ln:
            return ln
    return lines[-1]


def _snapshot_dirs() -> dict[str, float]:
    if not TABULAR_RESULTS.exists():
        return {}
    return {p.name: p.stat().st_mtime for p in TABULAR_RESULTS.iterdir() if p.is_dir()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default="breast_cancer.py")
    parser.add_argument("--arg", nargs=argparse.REMAINDER, default=[],
                        help="Extra args forwarded verbatim to the official script.")
    args = parser.parse_args()

    script = EXAMPLE_DIR / args.script
    if not script.exists():
        print(f"ERROR: official script not found: {script}", file=sys.stderr)
        print("Clone DPSDA at the pinned SHA into external/DPSDA first.", file=sys.stderr)
        return 2

    key = script.stem
    meta = DEMO_META.get(args.script, {})

    raw_dir = REPO_ROOT / "results" / "raw" / key
    logs_dir = REPO_ROOT / "results" / "logs"
    summaries_dir = REPO_ROOT / "results" / "summaries"
    for d in (raw_dir, logs_dir, summaries_dir):
        d.mkdir(parents=True, exist_ok=True)

    before = _snapshot_dirs()

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, script.name, *args.arg],
        cwd=str(EXAMPLE_DIR), capture_output=True, text=True,
    )
    runtime_s = round(time.perf_counter() - t0, 2)

    console_log = logs_dir / f"smoke_{key}_console.log"
    console_log.write_text(
        f"$ python {script.name} {' '.join(args.arg)}\n\n"
        f"[returncode={proc.returncode}]\n\n=== STDOUT ===\n{proc.stdout}\n"
        f"=== STDERR ===\n{proc.stderr}\n",
        encoding="utf-8",
    )

    # Identify the experiment folder produced/updated by this run.
    after = _snapshot_dirs()
    changed = [n for n, m in after.items() if before.get(n) != m]
    harvested: dict[str, object] = {"experiment_folders": changed}
    for exp in changed:
        src = TABULAR_RESULTS / exp
        dest = raw_dir / exp
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        synth = dest / "synthetic_tab"
        ckpt = dest / "checkpoint"
        harvested[exp] = {
            "copied_to": str(dest.relative_to(REPO_ROOT)),
            "synthetic_csvs": sorted(p.name for p in synth.glob("*.csv")) if synth.exists() else [],
            "checkpoint_files": len(list(ckpt.glob("*"))) if ckpt.exists() else 0,
            "log_txt_present": (dest / "log.txt").exists(),
        }
        final_metrics = parse_final_metrics(dest / "log.txt")
        if final_metrics:
            harvested[exp]["final_metrics"] = final_metrics

    record = {
        "experiment_name": key,
        "official_script_path": f"example/tabular/{args.script} {' '.join(args.arg)}".strip(),
        "official_commit_sha": DPSDA_SHA,
        "official_commit_sha_observed": _git_sha(DPSDA_DIR),
        "command": f"python {args.script} {' '.join(args.arg)}".strip(),
        "classifier_model": meta.get("classifier"),
        "python_version": platform.python_version(),
        "uv_version": _tool_version(["uv", "--version"]),
        "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor(),
        "random_seed": "not seeded (PE generation is non-deterministic; WSD sampling uses seed=42)",
        "privacy_parameters": {"epsilon": 1.0, "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": meta.get("dataset"),
        "dataset_source": meta.get("data_source"),
        "started_at_utc": started_at,
        "runtime_seconds": runtime_s,
        "returncode": proc.returncode,
        "reproduction_status": "EXECUTED" if proc.returncode == 0 else "FAILED",
        "failure_reason": _failure_reason(proc.stderr) if proc.returncode != 0 else None,
        "artifacts": harvested,
        "console_log": str(console_log.relative_to(REPO_ROOT)),
    }

    out_json = summaries_dir / f"smoke_{key}.json"
    out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"returncode={proc.returncode} runtime={runtime_s}s status={record['reproduction_status']}")
    print(f"record -> {out_json.relative_to(REPO_ROOT)}")
    if proc.returncode != 0:
        print("--- stderr tail ---")
        print("\n".join(proc.stderr.splitlines()[-25:]))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
