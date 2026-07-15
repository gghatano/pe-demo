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
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
ITERS = REPO_ROOT / "results" / "summaries" / "iterations"
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


def _f(row: dict, key: str):
    v = row.get(key, "")
    return float(v) if v not in ("", None) else None


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    series = {p.stem: _read(p) for p in sorted(ITERS.glob("*.csv"))}
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
