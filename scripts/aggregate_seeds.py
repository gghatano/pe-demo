"""Aggregate multi-seed runs into mean/std/min/max (issues #22, #24).

Groups seeded run records by a key field (e.g. ``prior_function`` for SCM,
``variant`` for the Adult embedding experiment), and writes mean/std/min/max/n per
metric so single-trial and multi-trial results are never conflated.

Outputs (prefix chosen by ``--out``):
    results/summaries/<out>_aggregate.csv
    results/summaries/<out>_aggregate.json
    results/figures/<out>_stability.png   (bar chart with std error bars)

Usage:
    uv run python scripts/aggregate_seeds.py --glob "scm_*_seed*.json" --group prior_function --out scm_seed
    uv run python scripts/aggregate_seeds.py --glob "adult_embedding_*_seed*.json" --group variant --out adult_embedding_seed
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARIES = REPO_ROOT / "results" / "summaries"
FIGURES = REPO_ROOT / "results" / "figures"

METRICS = ["classifier_test_acc", "classifier_test_f1", "classifier_test_auc",
           "wsd_1way", "wsd_2way", "wsd_3way", "wsd_5way", "wsd_6way", "wsd_7way",
           "runtime_seconds"]


def _collect(glob: str, group_field: str) -> dict[str, dict[str, list[float]]]:
    groups: dict[str, dict[str, list[float]]] = {}
    for p in sorted(SUMMARIES.glob(glob)):
        if p.name.endswith("_aggregate.json"):
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        key = str(rec.get(group_field, "?"))
        fm = dict(rec.get("final_metrics") or {})
        fm["runtime_seconds"] = rec.get("runtime_seconds")
        g = groups.setdefault(key, {})
        g.setdefault("_seeds", []).append(rec.get("seed"))
        for m in METRICS:
            v = fm.get(m)
            if isinstance(v, (int, float)):
                g.setdefault(m, []).append(float(v))
    return groups


def _stats(values: list[float]) -> dict[str, float]:
    a = np.array(values, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=0)),
            "min": float(a.min()), "max": float(a.max()), "n": int(a.size)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    groups = _collect(args.glob, args.group)
    if not groups:
        print(f"No records matched {args.glob}; skipping (nothing to aggregate).")
        return 0

    agg = {}
    rows = []
    for key, data in sorted(groups.items()):
        seeds = sorted(s for s in data.get("_seeds", []) if s is not None)
        entry = {"group": key, "seeds": seeds, "n_runs": len(seeds)}
        for m in METRICS:
            if m in data and data[m]:
                st = _stats(data[m])
                entry[m] = st
                rows.append({"group": key, "metric": m, "n": st["n"],
                             "mean": round(st["mean"], 4), "std": round(st["std"], 4),
                             "min": round(st["min"], 4), "max": round(st["max"], 4)})
        agg[key] = entry

    SUMMARIES.mkdir(parents=True, exist_ok=True)
    (SUMMARIES / f"{args.out}_aggregate.json").write_text(json.dumps(agg, indent=2), encoding="utf-8")
    with (SUMMARIES / f"{args.out}_aggregate.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "metric", "n", "mean", "std", "min", "max"])
        w.writeheader()
        w.writerows(rows)

    # Figure: accuracy mean±std per group (the headline utility metric).
    keys = sorted(agg.keys())
    means = [agg[k].get("classifier_test_acc", {}).get("mean") for k in keys]
    stds = [agg[k].get("classifier_test_acc", {}).get("std") for k in keys]
    if all(m is not None for m in means):
        FIGURES.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(6.5, 4.0))
        x = np.arange(len(keys))
        ax.bar(x, means, yerr=stds, capsize=6, color="#3949ab", alpha=0.85)
        for i, (m, s) in enumerate(zip(means, stds)):
            ax.text(i, m + (s or 0) + 0.5, f"{m:.1f}±{s:.1f}", ha="center", fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{k}\n(n={agg[k]['n_runs']})" for k in keys])
        ax.set_ylabel("classifier test accuracy (%)")
        ax.set_title(f"{args.out}: accuracy mean +/- std across seeds")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIGURES / f"{args.out}_stability.png", dpi=120)
        print(f"wrote {FIGURES / f'{args.out}_stability.png'}")
        plt.close(fig)

    print(f"aggregated {sum(a['n_runs'] for a in agg.values())} runs into {len(agg)} groups "
          f"-> results/summaries/{args.out}_aggregate.{{csv,json}}")
    for k in keys:
        acc = agg[k].get("classifier_test_acc", {})
        print(f"  {k}: n={agg[k]['n_runs']} seeds={agg[k]['seeds']} "
              f"acc={acc.get('mean'):.2f}±{acc.get('std'):.2f}" if acc else f"  {k}: (no acc)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
