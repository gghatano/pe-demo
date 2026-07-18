"""XOR Tab-PE generation with the tabpfn classifier removed (issue #5).

This is a **documented deviation** from the official
``example/tabular/xor_stress_test.py`` (DPSDA @ 9078c67...). The ONLY change is
that the ``TabClassifier`` callback is removed: the official XOR demo hardcodes
the ``tabpfn`` classifier, which requires a one-time interactive license
acceptance + ``TABPFN_TOKEN`` to download weights, which is unavailable in this
autonomous/non-interactive context.

What is unchanged (the Tab-PE algorithm, privacy, and data pipeline are byte-for-
byte the official settings): ``TabularAPI`` mutation schedule, ``TabularEmbedding``,
``NearestNeighbors`` histogram, the composite population, ``epsilon=1.0`` /
``delta = 1/n/ln(n)`` Gaussian mechanism, ``num_iterations=20``, ``num_samples=1000``.

Consequence for the reproduction record:
- Tab-PE **generation** on XOR is exercised end-to-end (synthetic CSVs + checkpoints).
- The XOR classifier **utility metric is recorded as NOT_RUN** (blocked on TABPFN_TOKEN).

Run:
    uv run python scripts/experiments/xor_no_classifier.py --num-features 1
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pe.data import TabularCSV
from pe.logging import setup_logging
from pe.runner import PE
from pe.population import PEPopulation
from pe.population import CompositePopulation
from pe.api import TabularAPI
from pe.embedding import TabularEmbedding
from pe.histogram import NearestNeighbors
from pe.callback import SaveCheckpoints
from pe.callback import SaveTabToCSV
from pe.logger import CSVPrint
from pe.logger import LogPrint

import pandas as pd

pd.options.mode.copy_on_write = True

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-features", type=int, default=1)
    args = parser.parse_args()
    num_features = args.num_features

    exp_name = f"xor_stress_test_{num_features}_features"
    exp_folder = REPO_ROOT / "results" / "raw" / "xor" / exp_name
    exp_folder.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(exp_folder / "log.txt"))

    base = (
        "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/"
        f"heads/main/tabular/sim/xor-stress-test/{num_features}_feature_xor"
    )
    priv_data = TabularCSV(csv_path=f"{base}/data_train.csv", metadata_path=f"{base}/metadata.json")
    priv_info = priv_data.get_tab_info()

    # NOTE (deviation): the official demo also builds `test_data` and a
    # `TabClassifier(model_name="tabpfn", ...)`. We intentionally omit the
    # classifier; test data is unused without it.

    num_iterations = 20

    api = TabularAPI(
        info=priv_info,
        mutation_rate_init=0.5,
        mutation_rate_final=0.01,
        decay_type="polynomial",
        gamma=0.2,
        num_iterations=num_iterations,
    )
    embedding = TabularEmbedding(info=priv_info)
    histogram = NearestNeighbors(
        embedding=embedding,
        mode="L2",
        lookahead_degree=0,
        backend="torch",
    )
    population1 = PEPopulation(
        api=api,
        initial_variation_api_fold=0,
        next_variation_api_fold=1,
        keep_selected=False,
        selection_mode="sample",
        histogram_threshold=0,
    )
    population2 = PEPopulation(
        api=api, initial_variation_api_fold=3, next_variation_api_fold=3, keep_selected=True, selection_mode="rank"
    )
    population = CompositePopulation(populations=[population1] * 5 + [population2] * (num_iterations - 5))

    save_checkpoints = SaveCheckpoints(str(exp_folder / "checkpoint"))
    save_tab_to_csv = SaveTabToCSV(output_folder=str(exp_folder / "synthetic_tab"))

    csv_print = CSVPrint(output_folder=str(exp_folder))
    log_print = LogPrint()

    num_private_samples = len(priv_data.data_frame)
    delta = 1.0 / num_private_samples / np.log(num_private_samples)

    pe_runner = PE(
        priv_data=priv_data,
        population=population,
        histogram=histogram,
        callbacks=[
            save_checkpoints,
            save_tab_to_csv,
            # TabClassifier intentionally omitted (deviation) — see module docstring.
        ],
        loggers=[csv_print, log_print],
    )

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    pe_runner.run(
        num_samples_schedule=[1000] * num_iterations,
        delta=delta,
        epsilon=1.0,
        checkpoint_path=str(exp_folder / "checkpoint"),
    )
    runtime_s = round(time.perf_counter() - t0, 2)

    synth = exp_folder / "synthetic_tab"
    ckpt = exp_folder / "checkpoint"
    record = {
        "experiment_name": exp_name,
        "official_script_path": f"example/tabular/xor_stress_test.py --num-features {num_features}",
        "deviation": "TabClassifier(model_name='tabpfn') removed; generation/DP unchanged.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/xor_no_classifier.py --num-features {num_features}",
        "python_version": platform.python_version(),
        "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor(),
        "random_seed": "not seeded (PE generation is non-deterministic)",
        "privacy_parameters": {"epsilon": 1.0, "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": f"XOR stress test ({num_features} feature)",
        "dataset_source": base + "/",
        "num_iterations": num_iterations,
        "num_samples": 1000,
        "num_private_samples": num_private_samples,
        "started_at_utc": started_at,
        "runtime_seconds": runtime_s,
        "reproduction_status": "EXECUTED",
        "metrics": {
            "classifier_test_acc": "NOT_RUN (tabpfn requires interactive license/TABPFN_TOKEN)",
        },
        "artifacts": {
            "log_relpath": (exp_folder / "log.txt").relative_to(REPO_ROOT).as_posix(),
            "synthetic_csvs": sorted(p.name for p in synth.glob("*.csv")) if synth.exists() else [],
            "checkpoint_files": len(list(ckpt.glob("*"))) if ckpt.exists() else 0,
        },
    }

    summaries = REPO_ROOT / "results" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    out_json = summaries / f"xor_{exp_name}.json"
    out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"runtime={runtime_s}s synthetic_csvs={len(record['artifacts']['synthetic_csvs'])} "
          f"checkpoints={record['artifacts']['checkpoint_files']}")
    print(f"record -> {out_json.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
