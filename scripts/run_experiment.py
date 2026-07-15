"""Run an official DPSDA Tab-PE demo as a recorded experiment (issues #4/#5).

This is the canonical experiment wrapper. It reuses the helper functions from
``run_smoke.py`` (metadata capture, artifact harvesting, final-metric parsing) but
writes ``results/summaries/experiment_<key>.json`` and is intended for the real
reproduction runs rather than the one-off smoke test.

The official script is run *unmodified* from the pinned DPSDA checkout under
``external/DPSDA/example/tabular/``. See docs/research/official-implementation.md.

Usage:
    uv run python scripts/run_experiment.py --script scm.py --arg --prior-function rff
    uv run python scripts/run_experiment.py --script artificial_characters.py
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# scripts/ is on sys.path[0] when invoked as `python scripts/run_experiment.py`.
from run_smoke import (  # noqa: E402
    DPSDA_SHA,
    DPSDA_DIR,
    EXAMPLE_DIR,
    REPO_ROOT,
    _failure_reason,
    _git_sha,
    _snapshot_dirs,
    _tool_version,
    parse_final_metrics,
)

# Classifier + dataset facts per demo (docs/research/official-implementation.md).
DEMO_META = {
    "scm.py": {"classifier": "tabicl", "dataset": "SCM (simulated)",
               "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/sim/scm/"},
    "artificial_characters.py": {"classifier": "tabicl", "dataset": "Artificial Characters (real)",
               "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/artificial-characters/"},
    "person_activity.py": {"classifier": "tabicl", "dataset": "Person Activity (real)",
               "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/person-activity/"},
    "adult.py": {"classifier": "tabicl", "dataset": "Adult (real)",
               "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/adult/"},
    "breast_cancer.py": {"classifier": "tabicl", "dataset": "Breast Cancer (real)",
               "data_source": "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/breast-cancer/"},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--arg", nargs=argparse.REMAINDER, default=[],
                        help="Extra args forwarded verbatim to the official script.")
    args = parser.parse_args()

    script = EXAMPLE_DIR / args.script
    if not script.exists():
        print(f"ERROR: official script not found: {script}", file=sys.stderr)
        return 2

    # Include a suffix from the extra args so scm rff/tree/nn get distinct keys.
    suffix = "".join(a for a in args.arg if not a.startswith("-"))
    key = script.stem + (f"_{suffix}" if suffix else "")
    meta = DEMO_META.get(args.script, {})

    raw_dir = REPO_ROOT / "results" / "raw" / script.stem
    logs_dir = REPO_ROOT / "results" / "logs"
    summaries_dir = REPO_ROOT / "results" / "summaries"
    for d in (raw_dir, logs_dir, summaries_dir):
        d.mkdir(parents=True, exist_ok=True)

    before = _snapshot_dirs()

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    import subprocess
    proc = subprocess.run(
        [sys.executable, script.name, *args.arg],
        cwd=str(EXAMPLE_DIR), capture_output=True, text=True,
    )
    runtime_s = round(time.perf_counter() - t0, 2)

    console_log = logs_dir / f"experiment_{key}_console.log"
    console_log.write_text(
        f"$ python {script.name} {' '.join(args.arg)}\n\n"
        f"[returncode={proc.returncode}]\n\n=== STDOUT ===\n{proc.stdout}\n"
        f"=== STDERR ===\n{proc.stderr}\n",
        encoding="utf-8",
    )

    after = _snapshot_dirs()
    changed = [n for n, m in after.items() if before.get(n) != m]
    harvested: dict[str, object] = {"experiment_folders": changed}
    for exp in changed:
        src = EXAMPLE_DIR / "results" / "tabular" / exp
        dest = raw_dir / exp
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        synth = dest / "synthetic_tab"
        ckpt = dest / "checkpoint"
        harvested[exp] = {
            "copied_to": str(dest.relative_to(REPO_ROOT)),
            "synthetic_csvs": len(list(synth.glob("*.csv"))) if synth.exists() else 0,
            "checkpoint_files": len(list(ckpt.glob("*"))) if ckpt.exists() else 0,
            "log_txt_present": (dest / "log.txt").exists(),
        }
        fm = parse_final_metrics(dest / "log.txt")
        if fm:
            harvested[exp]["final_metrics"] = fm

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

    out_json = summaries_dir / f"experiment_{key}.json"
    out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"returncode={proc.returncode} runtime={runtime_s}s status={record['reproduction_status']}")
    print(f"record -> {out_json.relative_to(REPO_ROOT)}")
    if proc.returncode != 0:
        print("--- stderr tail ---")
        print("\n".join(proc.stderr.splitlines()[-20:]))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
