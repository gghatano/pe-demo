"""Seed-controlled SCM runner (issue #22).

Mirrors the official ``example/tabular/scm.py`` exactly, adding only RNG seeding so
the run is reproducible. The Tab-PE algorithm, populations, embedding, NN histogram,
classifier, WSD, and the epsilon=1.0 Gaussian mechanism are unchanged.

Why just ``np.random.seed`` controls it: the whole tabular generation path uses
NumPy's global RNG — ``TabularAPI.random_api``/``variation_api``
(``np.random.choice/randint/uniform/rand``), ``pe.dp.gaussian.add_noise``
(``np.random.normal``), and ``PEPopulation.next`` sample selection
(``np.random.choice``). The NN histogram (torch, ``lookahead_degree=0``) is a
deterministic argmin, and ``tabicl`` inference is deterministic given fixed weights,
so no torch RNG seeding is required for the tabular path. ``ComputeWSD`` already uses
its own fixed ``random_state`` (42). We also seed ``random`` and torch defensively.

Usage:
    uv run python scripts/experiments/run_scm_seeded.py --prior-function rff --seed 0
    uv run python scripts/experiments/run_scm_seeded.py --prior-function tree --seed 0 --num-iterations 2  # smoke
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pe.data import TabularCSV
from pe.logging import setup_logging
from pe.runner import PE
from pe.population import PEPopulation, CompositePopulation
from pe.api import TabularAPI
from pe.embedding import TabularEmbedding
from pe.histogram import NearestNeighbors
from pe.callback import SaveCheckpoints, SaveTabToCSV, TabClassifier, ComputeWSD
from pe.logger import CSVPrint, LogPrint
from pe.constant.data import VARIATION_API_FOLD_ID_COLUMN_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_smoke import parse_final_metrics  # noqa: E402

pd.options.mode.copy_on_write = True

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"
DATA_BASE = "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/sim/scm"


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def _seed_everything(seed: int) -> None:
    np.random.seed(seed)
    random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-function", required=True, choices=["tree", "nn", "rff"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-iterations", type=int, default=15)
    parser.add_argument("--num-samples", type=int, default=1000)
    args = parser.parse_args()

    _seed_everything(args.seed)

    prior = args.prior_function
    exp_name = f"scm_{prior}_seed{args.seed}"
    exp_folder = REPO_ROOT / "results" / "raw" / "scm_seeded" / exp_name
    exp_folder.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(exp_folder / "log.txt"))

    base = f"{DATA_BASE}/{prior}"
    priv_data = TabularCSV(csv_path=f"{base}/data_train.csv", metadata_path=f"{base}/metadata.json")
    priv_info = priv_data.get_tab_info()
    test_data = TabularCSV(csv_path=f"{base}/data_test.csv", metadata_path=f"{base}/metadata.json")

    num_iterations = args.num_iterations
    api = TabularAPI(info=priv_info, mutation_rate_init=0.5, mutation_rate_final=0.01,
                     decay_type="polynomial", gamma=0.2, num_iterations=num_iterations)
    embedding = TabularEmbedding(info=priv_info)
    histogram = NearestNeighbors(embedding=embedding, mode="L2", lookahead_degree=0, backend="torch")
    population1 = PEPopulation(api=api, initial_variation_api_fold=0, next_variation_api_fold=1,
                               keep_selected=False, selection_mode="sample", histogram_threshold=0)
    population2 = PEPopulation(api=api, initial_variation_api_fold=3, next_variation_api_fold=3,
                               keep_selected=True, selection_mode="rank")
    population = CompositePopulation(populations=[population1] * 5 + [population2] * (num_iterations - 5))

    save_checkpoints = SaveCheckpoints(str(exp_folder / "checkpoint"))
    save_tab_to_csv = SaveTabToCSV(output_folder=str(exp_folder / "synthetic_tab"))
    tab_classifier = TabClassifier(test_data=test_data, model_name="tabicl",
                                   filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1})
    wsd = [ComputeWSD(priv_data=priv_data, degree=d, num_samples=args.num_samples, seed=42,
                      filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1}) for d in (5, 6, 7)]
    csv_print = CSVPrint(output_folder=str(exp_folder))
    log_print = LogPrint()

    num_private_samples = len(priv_data.data_frame)
    delta = 1.0 / num_private_samples / np.log(num_private_samples)

    pe_runner = PE(priv_data=priv_data, population=population, histogram=histogram,
                   callbacks=[save_checkpoints, save_tab_to_csv, tab_classifier, *wsd],
                   loggers=[csv_print, log_print])

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    pe_runner.run(num_samples_schedule=[args.num_samples] * num_iterations, delta=delta, epsilon=1.0,
                  checkpoint_path=str(exp_folder / "checkpoint"))
    runtime_s = round(time.perf_counter() - t0, 2)

    fm = parse_final_metrics(exp_folder / "log.txt")
    record = {
        "experiment_name": exp_name,
        "kind": "scm_seeded",
        "official_script_path": f"example/tabular/scm.py --prior-function {prior}",
        "deviation": "np.random/random/torch seeded for reproducibility; algorithm unchanged.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/run_scm_seeded.py --prior-function {prior} "
                   f"--seed {args.seed} --num-iterations {num_iterations}",
        "prior_function": prior,
        "classifier_model": "tabicl",
        "seed": args.seed,
        "python_version": platform.python_version(),
        "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor(),
        "privacy_parameters": {"epsilon": 1.0, "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": f"SCM ({prior})",
        "dataset_source": base + "/",
        "num_iterations": num_iterations,
        "num_samples": args.num_samples,
        "num_private_samples": num_private_samples,
        "started_at_utc": started_at,
        "runtime_seconds": runtime_s,
        "reproduction_status": "EXECUTED",
        "final_metrics": fm,
        "artifacts": {
            "log_relpath": (exp_folder / "log.txt").relative_to(REPO_ROOT).as_posix(),
            "synthetic_csvs": len(list((exp_folder / "synthetic_tab").glob("*.csv")))
                              if (exp_folder / "synthetic_tab").exists() else 0,
            "checkpoint_files": len(list((exp_folder / "checkpoint").glob("*")))
                                if (exp_folder / "checkpoint").exists() else 0,
        },
    }
    summaries = REPO_ROOT / "results" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    out = summaries / f"{exp_name}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"prior={prior} seed={args.seed} iters={num_iterations} runtime={runtime_s}s "
          f"acc={fm.get('classifier_test_acc')} f1={fm.get('classifier_test_f1')} auc={fm.get('classifier_test_auc')} "
          f"wsd5={fm.get('wsd_5way')}")
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
