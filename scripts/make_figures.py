"""Generate figures from the tracked per-iteration series (issue #6).

Reads ``results/summaries/iterations/<key>.csv`` (produced by
``collect_results.py``) and writes PNG figures to ``results/figures/``:

- ``accuracy_vs_iteration.png`` — classifier test accuracy per PE iteration.
- ``wsd_vs_iteration.png`` — k-way Wasserstein marginal distance per iteration.

Figures are regenerated from tracked CSVs (no experiment re-run needed) and are
embedded into the HTML report as base64 by ``build_html.py``.

Usage:
    uv run python scripts/make_figures.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARIES = REPO_ROOT / "results" / "summaries"
ITERS = SUMMARIES / "iterations"
FIGURES = REPO_ROOT / "results" / "figures"

# Friendly labels for known experiment-folder keys.
LABELS = {
    "breast-cancer_composite_population": "Breast Cancer",
    "scm_rff": "SCM (rff)",
    "artificial-characters_composite_population": "Artificial Characters",
    "person-activity_composite_population": "Person Activity",
    "adult_composite_population": "Adult",
}


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _xor_features_figure() -> None:
    """XOR: final synthetic-train→real-test accuracy vs number of XOR features
    (the high-order-correlation stress). Reads results/summaries/xor_clf_*.json."""
    rows = []
    for p in sorted(SUMMARIES.glob("xor_clf_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        fm = d.get("final_metrics", {})
        nf = d.get("dataset_name", "")
        # num-features from the record's experiment_name suffix.
        try:
            n = int(d["experiment_name"].split("_")[3])
        except Exception:
            continue
        rows.append((n, fm.get("classifier_test_acc"), fm.get("classifier_test_f1"),
                     fm.get("classifier_test_auc"), d.get("classifier_model", "")))
    if not rows:
        return
    rows.sort()
    xs = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    for idx, name in ((1, "accuracy"), (2, "macro F1"), (3, "AUC")):
        ys = [r[idx] for r in rows]
        if any(y is not None for y in ys):
            ax.plot(xs, ys, marker="o", ms=5, label=name)
    clf = rows[0][4]
    ax.set_xlabel("XOR features (correlation order)")
    ax.set_ylabel("score (%)")
    ax.set_xticks(xs)
    ax.set_title(f"XOR: synthetic-train -> real-test score vs features (classifier={clf})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "xor_accuracy_vs_features.png", dpi=120)
    print(f"wrote {FIGURES / 'xor_accuracy_vs_features.png'}")
    plt.close(fig)


def _f(row: dict, key: str):
    v = row.get(key, "")
    return float(v) if v not in ("", None) else None


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    # Per-iteration figures cover the main single-run demos. Exclude XOR (shown
    # separately as a num-features trend) and the multi-seed / embedding-variant
    # runs (summarized as mean±std bar charts by aggregate_seeds.py).
    def _skip(stem: str) -> bool:
        return "xor" in stem or "seed" in stem or stem.startswith("adult_embedding")
    series = {p.stem: _read(p) for p in sorted(ITERS.glob("*.csv")) if not _skip(p.stem)}
    _xor_features_figure()
    if not series:
        print("No per-iteration series found; run collect_results.py first.")
        return 1

    # --- accuracy vs iteration ---
    fig, ax = plt.subplots(figsize=(7, 4.2))
    plotted = False
    for key, rows in series.items():
        xs, ys = [], []
        for r in rows:
            y = _f(r, "test_acc")
            if y is not None:
                xs.append(int(r["iteration"])); ys.append(y)
        if xs:
            ax.plot(xs, ys, marker="o", ms=3, label=LABELS.get(key, key))
            plotted = True
    if plotted:
        ax.set_xlabel("PE iteration")
        ax.set_ylabel("Classifier test accuracy (%)")
        ax.set_title("Synthetic-train → real-test accuracy per PE iteration")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURES / "accuracy_vs_iteration.png", dpi=120)
        print(f"wrote {FIGURES / 'accuracy_vs_iteration.png'}")
    plt.close(fig)

    # --- WSD vs iteration (subplots per experiment) ---
    wsd_series = {k: v for k, v in series.items()
                  if any(any(c.startswith("wsd_") for c in r) for r in v)}
    if wsd_series:
        n = len(wsd_series)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 4.0), squeeze=False)
        for ax, (key, rows) in zip(axes[0], wsd_series.items()):
            degs = sorted({c for r in rows for c in r if c.startswith("wsd_")})
            for deg in degs:
                xs, ys = [], []
                for r in rows:
                    y = _f(r, deg)
                    if y is not None:
                        xs.append(int(r["iteration"])); ys.append(y)
                if xs:
                    ax.plot(xs, ys, marker="o", ms=3, label=deg.replace("wsd_", "").replace("way", "-way"))
            ax.set_title(LABELS.get(key, key))
            ax.set_xlabel("PE iteration")
            ax.set_ylabel("Wasserstein marginal distance")
            ax.grid(True, alpha=0.3)
            ax.legend()
        fig.suptitle("k-way Wasserstein marginal distance per PE iteration")
        fig.tight_layout()
        fig.savefig(FIGURES / "wsd_vs_iteration.png", dpi=120)
        print(f"wrote {FIGURES / 'wsd_vs_iteration.png'}")
        plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
