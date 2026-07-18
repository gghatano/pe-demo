"""Adult epsilon sweep (issue #38).

Runs the official Adult demo (unmodified `TabularEmbedding`) at a chosen DP budget
epsilon, with seed control. Only epsilon and the RNG seed vary; the algorithm,
populations, classifier (tabicl), and WSD are the official settings. `epsilon=inf`
gives noise_multiplier=0 (no DP noise = the PE upper bound).

Usage:
    uv run python scripts/experiments/run_adult_epsilon.py --epsilon 2 --seed 0
    uv run python scripts/experiments/run_adult_epsilon.py --epsilon inf --seed 0
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
from pe.histogram import NearestNeighbors
from pe.callback import SaveCheckpoints, SaveTabToCSV, TabClassifier, ComputeWSD
from pe.logger import CSVPrint, LogPrint
from pe.constant.data import VARIATION_API_FOLD_ID_COLUMN_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pe_demo.embedding.adult import AdultEmbedding, AdultEmbeddingConfig  # noqa: E402
from run_smoke import parse_final_metrics  # noqa: E402

pd.options.mode.copy_on_write = True

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"
DATA_BASE = "https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/real/adult"


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def _eps_tag(eps: float) -> str:
    if np.isinf(eps):
        return "inf"
    return str(eps).replace(".", "p")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epsilon", type=float, required=True, help="DP budget; use 'inf' for no noise")
    parser.add_argument("--variant", default="official",
                        choices=["official", "robust_numeric", "adult_semantic", "public_fe"])
    parser.add_argument("--capital-presence-weight", type=float, default=None,
                        help="override AdultEmbeddingConfig.capital_presence_weight (diagnostic)")
    parser.add_argument("--capital-amount-weight", type=float, default=None,
                        help="override AdultEmbeddingConfig.capital_amount_weight (diagnostic)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-iterations", type=int, default=30)
    parser.add_argument("--num-samples", type=int, default=1000)
    args = parser.parse_args()

    np.random.seed(args.seed)
    random.seed(args.seed)
    try:
        import torch
        torch.manual_seed(args.seed)
    except Exception:
        pass

    eps = args.epsilon
    tag = _eps_tag(eps)
    # Keep the official-embedding names unchanged (#38); tag other variants.
    vpart = "" if args.variant == "official" else f"_{args.variant}"
    if args.capital_presence_weight is not None:
        vpart += f"_cpw{args.capital_presence_weight}".replace(".", "p")
    if args.capital_amount_weight is not None:
        vpart += f"_caw{args.capital_amount_weight}".replace(".", "p")
    exp_name = f"adult_eps{tag}{vpart}_seed{args.seed}"
    exp_folder = REPO_ROOT / "results" / "raw" / "adult_eps" / exp_name
    exp_folder.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(exp_folder / "log.txt"))

    priv_data = TabularCSV(csv_path=f"{DATA_BASE}/adult_train.csv",
                           metadata_path=f"{DATA_BASE}/adult_metadata.json")
    priv_info = priv_data.get_tab_info()
    test_data = TabularCSV(csv_path=f"{DATA_BASE}/adult_test.csv",
                           metadata_path=f"{DATA_BASE}/adult_metadata.json")

    num_iterations = args.num_iterations
    api = TabularAPI(info=priv_info, mutation_rate_init=0.5, mutation_rate_final=0.01,
                     decay_type="polynomial", gamma=0.2, num_iterations=num_iterations)
    cfg_kwargs = {"variant": args.variant}
    if args.capital_presence_weight is not None:
        cfg_kwargs["capital_presence_weight"] = args.capital_presence_weight
    if args.capital_amount_weight is not None:
        cfg_kwargs["capital_amount_weight"] = args.capital_amount_weight
    emb_config = AdultEmbeddingConfig(**cfg_kwargs)
    embedding = AdultEmbedding(info=priv_info, config=emb_config)
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
        "experiment_name": exp_name,
        "kind": "adult_epsilon_sweep",
        "official_script_path": "example/tabular/adult.py",
        "deviation": f"seeded; epsilon varied (official demo uses epsilon=1); embedding={args.variant}. "
                     "algorithm unchanged.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/run_adult_epsilon.py --epsilon {eps} --seed {args.seed}",
        "epsilon": ("inf" if np.isinf(eps) else eps),
        "variant": args.variant,
        "embedding_config": vars(emb_config),
        "classifier_model": "tabicl",
        "seed": args.seed,
        "python_version": platform.python_version(),
        "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor(),
        "privacy_parameters": {"epsilon": ("inf" if np.isinf(eps) else eps),
                               "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": "Adult (real)",
        "dataset_source": DATA_BASE + "/",
        "num_iterations": num_iterations,
        "num_samples": args.num_samples,
        "num_private_samples": num_private_samples,
        "started_at_utc": started_at,
        "runtime_seconds": runtime_s,
        "reproduction_status": "EXECUTED",
        "final_metrics": fm,
        "artifacts": {
            "log_relpath": str((exp_folder / "log.txt").relative_to(REPO_ROOT)),
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

    print(f"epsilon={eps} seed={args.seed} runtime={runtime_s}s "
          f"acc={fm.get('classifier_test_acc')} f1={fm.get('classifier_test_f1')} "
          f"auc={fm.get('classifier_test_auc')} nm={fm.get('dp',{}).get('noise_multiplier')}")
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
