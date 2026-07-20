"""Default of Credit Card Clients Tab-PE run (issue #50).

Runs official Tab-PE on the locally-prepared Credit data (binary default
prediction; run scripts/datasets/credit/preprocess.py first). Official
TabularEmbedding, seed control, Adult/Bank-comparable config (30 iterations,
1000 samples, WSD 1/2/3-way, tabicl). Only data / epsilon / seed change.

Run:
    uv run python scripts/experiments/run_credit.py --epsilon 1 --seed 0
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
DATA_DIR = REPO_ROOT / "data" / "credit"


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def _eps_tag(eps: float) -> str:
    return "inf" if np.isinf(eps) else str(eps).replace(".", "p")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epsilon", type=float, default=1.0, help="DP budget; 'inf' for no noise")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-iterations", type=int, default=30)
    parser.add_argument("--num-samples", type=int, default=1000)
    args = parser.parse_args()

    train_csv = DATA_DIR / "credit_train.csv"
    if not train_csv.exists():
        print("Credit data not found. Run scripts/datasets/credit/preprocess.py first.", file=sys.stderr)
        return 2

    np.random.seed(args.seed)
    random.seed(args.seed)
    try:
        import torch
        torch.manual_seed(args.seed)
    except Exception:
        pass

    eps = args.epsilon
    exp_name = f"credit_eps{_eps_tag(eps)}_seed{args.seed}"
    exp_folder = REPO_ROOT / "results" / "raw" / "credit" / exp_name
    exp_folder.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(exp_folder / "log.txt"))

    meta = str(DATA_DIR / "credit_metadata.json")
    priv_data = TabularCSV(csv_path=str(train_csv), metadata_path=meta)
    priv_info = priv_data.get_tab_info()
    test_data = TabularCSV(csv_path=str(DATA_DIR / "credit_test.csv"), metadata_path=meta)

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
                      filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1}) for d in (1, 2, 3)]
    csv_print = CSVPrint(output_folder=str(exp_folder))
    log_print = LogPrint()

    num_private_samples = len(priv_data.data_frame)
    delta = 1.0 / num_private_samples / np.log(num_private_samples)

    pe_runner = PE(priv_data=priv_data, population=population, histogram=histogram,
                   callbacks=[save_checkpoints, save_tab_to_csv, tab_classifier, *wsd],
                   loggers=[csv_print, log_print])

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    pe_runner.run(num_samples_schedule=[args.num_samples] * num_iterations, delta=delta,
                  epsilon=eps, checkpoint_path=str(exp_folder / "checkpoint"))
    runtime_s = round(time.perf_counter() - t0, 2)

    fm = parse_final_metrics(exp_folder / "log.txt")
    record = {
        "experiment_name": exp_name, "kind": "credit_default",
        "official_script_path": "n/a (new dataset via scripts/experiments/run_credit.py)",
        "deviation": "new dataset (UCI Default of Credit Card Clients); official TabularEmbedding + algorithm; seeded.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/run_credit.py --epsilon {eps} --seed {args.seed}",
        "epsilon": ("inf" if np.isinf(eps) else eps), "classifier_model": "tabicl", "seed": args.seed,
        "python_version": platform.python_version(), "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})", "cpu": platform.processor(),
        "privacy_parameters": {"epsilon": ("inf" if np.isinf(eps) else eps),
                               "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": "Default of Credit Card Clients (real)",
        "dataset_source": "data/credit/ (see data/credit/manifest.json)",
        "num_iterations": num_iterations, "num_samples": args.num_samples,
        "num_private_samples": num_private_samples, "started_at_utc": started_at,
        "runtime_seconds": runtime_s, "reproduction_status": "EXECUTED", "final_metrics": fm,
        "artifacts": {
            "log_relpath": (exp_folder / "log.txt").relative_to(REPO_ROOT).as_posix(),
            "synthetic_csvs": len(list((exp_folder / "synthetic_tab").glob("*.csv")))
                              if (exp_folder / "synthetic_tab").exists() else 0,
            "checkpoint_files": len(list((exp_folder / "checkpoint").glob("*")))
                                if (exp_folder / "checkpoint").exists() else 0,
        },
    }
    out = REPO_ROOT / "results" / "summaries" / f"{exp_name}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"epsilon={eps} seed={args.seed} runtime={runtime_s}s acc={fm.get('classifier_test_acc')} "
          f"f1={fm.get('classifier_test_f1')} auc={fm.get('classifier_test_auc')} wsd1={fm.get('wsd_1way')}")
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
