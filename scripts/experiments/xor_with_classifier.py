"""XOR Tab-PE with a substitute classifier (issue #21).

Documented deviation from the official `xor_stress_test.py` (DPSDA @ 9078c67):
the ONLY change is the classifier model — the official demo hardcodes `tabpfn`,
which needs a one-time interactive license + `TABPFN_TOKEN` to download weights.
Per decision, we substitute `tabicl` (the classifier used by the other five
official demos; downloads from the HuggingFace Hub with no license gate). This
lets us complete the XOR classification evaluation and observe how synthetic-train
→ real-test accuracy behaves as the XOR order (num-features) increases.

Unchanged from official: TabularAPI mutation schedule, TabularEmbedding,
NearestNeighbors histogram, composite population, epsilon=1.0 / delta=1/n/ln(n)
Gaussian mechanism, num_iterations=20, num_samples=1000.

Status semantics: `EXECUTED` (not `REPRODUCED`) — the classifier differs from the
official tabpfn, so this is not the official condition verbatim.

Run:
    uv run python scripts/experiments/xor_with_classifier.py --num-features 1 --classifier tabicl
"""

from __future__ import annotations

import argparse
import json
import platform
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
from pe.callback import SaveCheckpoints, SaveTabToCSV, TabClassifier
from pe.logger import CSVPrint, LogPrint
from pe.constant.data import VARIATION_API_FOLD_ID_COLUMN_NAME

pd.options.mode.copy_on_write = True

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_smoke import parse_final_metrics  # noqa: E402


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-features", type=int, default=1)
    parser.add_argument("--classifier", default="tabicl", choices=["tabicl", "xgboost"])
    args = parser.parse_args()
    num_features = args.num_features

    exp_name = f"xor_stress_test_{num_features}_features_{args.classifier}"
    exp_folder = REPO_ROOT / "results" / "raw" / "xor_clf" / exp_name
    exp_folder.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(exp_folder / "log.txt"))

    base = ("https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/"
            f"heads/main/tabular/sim/xor-stress-test/{num_features}_feature_xor")
    priv_data = TabularCSV(csv_path=f"{base}/data_train.csv", metadata_path=f"{base}/metadata.json")
    priv_info = priv_data.get_tab_info()
    test_data = TabularCSV(csv_path=f"{base}/data_test.csv", metadata_path=f"{base}/metadata.json")

    num_iterations = 20
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
    # DEVIATION: official uses model_name="tabpfn"; substituted per issue #21.
    tab_classifier = TabClassifier(test_data=test_data, model_name=args.classifier,
                                   filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1})
    csv_print = CSVPrint(output_folder=str(exp_folder))
    log_print = LogPrint()

    num_private_samples = len(priv_data.data_frame)
    delta = 1.0 / num_private_samples / np.log(num_private_samples)

    pe_runner = PE(priv_data=priv_data, population=population, histogram=histogram,
                   callbacks=[save_checkpoints, save_tab_to_csv, tab_classifier],
                   loggers=[csv_print, log_print])

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    pe_runner.run(num_samples_schedule=[1000] * num_iterations, delta=delta, epsilon=1.0,
                  checkpoint_path=str(exp_folder / "checkpoint"))
    runtime_s = round(time.perf_counter() - t0, 2)

    fm = parse_final_metrics(exp_folder / "log.txt")
    synth = exp_folder / "synthetic_tab"
    ckpt = exp_folder / "checkpoint"
    record = {
        "experiment_name": exp_name,
        "official_script_path": f"example/tabular/xor_stress_test.py --num-features {num_features}",
        "deviation": f"classifier tabpfn -> {args.classifier} (tabpfn is license-gated); generation/DP unchanged.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/xor_with_classifier.py --num-features {num_features} --classifier {args.classifier}",
        "classifier_model": args.classifier,
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
        "final_metrics": fm,
        "artifacts": {
            "log_relpath": str((exp_folder / "log.txt").relative_to(REPO_ROOT)),
            "synthetic_csvs": len(list(synth.glob("*.csv"))) if synth.exists() else 0,
            "checkpoint_files": len(list(ckpt.glob("*"))) if ckpt.exists() else 0,
        },
    }
    summaries = REPO_ROOT / "results" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    out = summaries / f"xor_clf_{num_features}f_{args.classifier}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"num_features={num_features} runtime={runtime_s}s acc={fm.get('classifier_test_acc')} "
          f"f1={fm.get('classifier_test_f1')} auc={fm.get('classifier_test_auc')}")
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
