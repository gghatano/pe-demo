"""Adult embedding comparison runner (issue #24).

Runs the Adult Tab-PE demo with a swappable embedding variant
(``official`` / ``robust_numeric`` / ``adult_semantic``) and a fixed seed.
Everything else matches the official ``adult.py``: num_iterations, num_samples,
epsilon/delta, composite population, TabularAPI mutation, TabClassifier(tabicl),
and 1/2/3-way WSD. Only the embedding object changes; the change is recorded.

This is an additional experiment (a deviation from the official condition). It does
NOT replace the official ``adult`` result — records are written under
``adult_embedding_*`` and the status is ``EXECUTED``.

Implementation-first note (#24 depends on #22): num_iterations is a CLI arg
(default 30 = official) so a fast single-seed smoke can use e.g. 2. The full
comparison uses the default 30 with >=3 seeds once #22 lands.

Usage:
    uv run python scripts/experiments/run_adult_embedding.py --variant official --seed 42
    uv run python scripts/experiments/run_adult_embedding.py --variant robust_numeric --seed 42 --num-iterations 2  # smoke
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
from pe.constant.data import VARIATION_API_FOLD_ID_COLUMN_NAME, TABULAR_DATA_COLUMN_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from pe_demo.embedding.adult import AdultEmbedding, AdultEmbeddingConfig, EDUCATION_TO_NUM  # noqa: E402
from run_smoke import parse_final_metrics  # noqa: E402

pd.options.mode.copy_on_write = True

DPSDA_SHA = "9078c67995499e6769113780200bbf1d788d3d60"
DATA_BASE = ("https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/"
             "heads/main/tabular/real/adult")


def _git_sha(repo: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def _features_df(data, feature_columns) -> pd.DataFrame:
    rows = data.data_frame[TABULAR_DATA_COLUMN_NAME].tolist()
    return pd.DataFrame(rows, columns=feature_columns)


def _extra_metrics(synth_df: pd.DataFrame, real_df: pd.DataFrame) -> dict:
    """Additional evaluations on the final synthetic data (separate from the
    official TabICL evaluation; not used in PE selection)."""
    out: dict[str, float] = {}
    try:
        exp = synth_df["education"].map(EDUCATION_TO_NUM)
        got = pd.to_numeric(synth_df["education-num"], errors="coerce").round()
        out["education_inconsistency_rate"] = float((exp.to_numpy() != got.to_numpy()).mean())
    except Exception:
        pass
    for col in ("capital-gain", "capital-loss"):
        try:
            s = float((pd.to_numeric(synth_df[col], errors="coerce") > 0).mean())
            r = float((pd.to_numeric(real_df[col], errors="coerce") > 0).mean())
            out[f"{col}_pos_ratio_synth"] = s
            out[f"{col}_pos_ratio_real"] = r
            out[f"{col}_pos_ratio_abs_diff"] = abs(s - r)
        except Exception:
            pass
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True,
                        choices=["official", "robust_numeric", "adult_semantic", "public_fe"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-iterations", type=int, default=30)
    parser.add_argument("--num-samples", type=int, default=1000)
    args = parser.parse_args()

    # Seed control (subset of #22): make PE generation and DP noise reproducible.
    # Same triple as the other runners (np / random / torch) so the whole path is seeded.
    np.random.seed(args.seed)
    random.seed(args.seed)
    try:
        import torch
        torch.manual_seed(args.seed)
    except Exception:
        pass

    exp_name = f"adult_embedding_{args.variant}_seed{args.seed}"
    exp_folder = REPO_ROOT / "results" / "raw" / "adult_embedding" / exp_name
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
    embedding = AdultEmbedding(info=priv_info, config=AdultEmbeddingConfig(variant=args.variant))
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
    # WSD's reference subsample seed is fixed (42) to match the other runners, so the
    # fidelity metric is measured against the same reference regardless of the run seed.
    wsd = [ComputeWSD(priv_data=priv_data, degree=d, num_samples=args.num_samples, seed=42,
                      filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1}) for d in (1, 2, 3)]
    csv_print = CSVPrint(output_folder=str(exp_folder))
    log_print = LogPrint()

    num_private_samples = len(priv_data.data_frame)
    delta = 1.0 / num_private_samples / np.log(num_private_samples)

    # Embedding dimension for provenance.
    feature_columns = priv_data.metadata["feature_columns"]
    emb_dim = int(embedding.compute_vectors(_features_df(priv_data, feature_columns).iloc[:1]).shape[1])

    pe_runner = PE(priv_data=priv_data, population=population, histogram=histogram,
                   callbacks=[save_checkpoints, save_tab_to_csv, tab_classifier, *wsd],
                   loggers=[csv_print, log_print])

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    pe_runner.run(num_samples_schedule=[args.num_samples] * num_iterations, delta=delta, epsilon=1.0,
                  checkpoint_path=str(exp_folder / "checkpoint"))
    runtime_s = round(time.perf_counter() - t0, 2)

    fm = parse_final_metrics(exp_folder / "log.txt")

    # Additional evaluations on the last synthetic CSV vs the real test data.
    extra: dict = {}
    synth_dir = exp_folder / "synthetic_tab"
    synth_files = sorted(synth_dir.glob("*.csv")) if synth_dir.exists() else []
    if synth_files:
        try:
            synth_df = pd.read_csv(synth_files[-1])
            real_df = _features_df(test_data, feature_columns)
            extra = _extra_metrics(synth_df, real_df)
        except Exception as e:  # keep the run recorded even if extra eval fails
            extra = {"error": str(e)}

    cfg = AdultEmbeddingConfig(variant=args.variant)
    record = {
        "experiment_name": exp_name,
        "kind": "adult_embedding_additional",  # separate from official reproduction
        "official_script_path": "example/tabular/adult.py",
        "deviation": f"embedding TabularEmbedding -> AdultEmbedding(variant={args.variant}); "
                     "generation/DP/populations/classifier/WSD unchanged.",
        "official_commit_sha": DPSDA_SHA,
        "command": f"python scripts/experiments/run_adult_embedding.py --variant {args.variant} "
                   f"--seed {args.seed} --num-iterations {num_iterations}",
        "variant": args.variant,
        "embedding_config": vars(cfg),
        "embedding_dim": emb_dim,
        "classifier_model": "tabicl",
        "seed": args.seed,
        "python_version": platform.python_version(),
        "uv_lock_commit": _git_sha(REPO_ROOT),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor(),
        "privacy_parameters": {"epsilon": 1.0, "delta": "1/n/ln(n)", "mechanism": "Gaussian on NN histogram"},
        "dataset_name": "Adult (real)",
        "dataset_source": DATA_BASE + "/",
        "num_iterations": num_iterations,
        "num_samples": args.num_samples,
        "num_private_samples": num_private_samples,
        "started_at_utc": started_at,
        "runtime_seconds": runtime_s,
        "reproduction_status": "EXECUTED",
        "final_metrics": fm,
        "extra_metrics": extra,
        "artifacts": {
            "log_relpath": (exp_folder / "log.txt").relative_to(REPO_ROOT).as_posix(),
            "synthetic_csvs": len(synth_files),
            "checkpoint_files": len(list((exp_folder / "checkpoint").glob("*")))
                                if (exp_folder / "checkpoint").exists() else 0,
        },
    }
    summaries = REPO_ROOT / "results" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    out = summaries / f"{exp_name}.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"variant={args.variant} seed={args.seed} iters={num_iterations} runtime={runtime_s}s "
          f"dim={emb_dim} acc={fm.get('classifier_test_acc')} f1={fm.get('classifier_test_f1')} "
          f"auc={fm.get('classifier_test_auc')}")
    print(f"extra={extra}")
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
