"""Measure the Bank Marketing downstream ceiling (issue #49).

Trains classifiers on REAL data and evaluates on the REAL test set, to bound how
good the downstream task can be (the reference for DP-synthetic utility). Writes a
tracked JSON so the ceiling has provenance (cf. review issue #42):

    results/summaries/bank_ceiling.json

Reports: majority baseline; tabicl trained on a real subsample of `--n` (same size
as the synthetic training set) → real test; xgboost trained on the full real train
→ real test. Uses the same encoding as pe's TabClassifier (LabelEncoder for
categoricals, MinMaxScaler for numerics, fit on train+test).

Run:
    uv run python scripts/datasets/bank/measure_ceiling.py
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

warnings.filterwarnings("ignore")
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / "data" / "bank"


def _load():
    meta = json.loads((DATA / "bank_metadata.json").read_text())
    feat = meta["cat_columns"] + meta["int_columns"] + meta["float_columns"]
    label = meta["label_columns"][0]
    tr = pd.read_csv(DATA / "bank_train.csv")
    te = pd.read_csv(DATA / "bank_test.csv")
    cat = set(meta["cat_columns"])
    for col in feat + [label]:
        merged = pd.concat([tr[col], te[col]])
        if col in cat or col == label:
            le = LabelEncoder().fit(merged.astype(str))
            tr[col] = le.transform(tr[col].astype(str)); te[col] = le.transform(te[col].astype(str))
        else:
            sc = MinMaxScaler().fit(merged.values.reshape(-1, 1))
            tr[col] = sc.transform(tr[col].values.reshape(-1, 1)); te[col] = sc.transform(te[col].values.reshape(-1, 1))
    Xtr, ytr = tr[feat].values, tr[label].values
    Xte, yte = te[feat].values, te[label].values
    return Xtr, ytr, Xte, yte


def _metrics(model, Xtr, ytr, Xte, yte) -> dict:
    model.fit(Xtr, ytr)
    p = model.predict(Xte)
    out = {"acc": round(accuracy_score(yte, p) * 100, 2),
           "macro_f1": round(f1_score(yte, p, average="macro") * 100, 2),
           "train_n": int(len(Xtr))}
    try:
        out["auc"] = round(roc_auc_score(yte, model.predict_proba(Xte)[:, 1]) * 100, 2)
    except Exception:
        pass
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000, help="real-subsample size for the fair upper bound")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    Xtr, ytr, Xte, yte = _load()
    vals, counts = np.unique(yte, return_counts=True)
    majority = round(counts.max() / counts.sum() * 100, 2)

    rng = np.random.default_rng(args.seed)
    idx = rng.choice(len(Xtr), size=min(args.n, len(Xtr)), replace=False)

    from tabicl import TabICLClassifier
    import xgboost as xgb
    result = {
        "dataset": "Bank Marketing",
        "test_n": int(len(Xte)),
        "majority_baseline_acc": majority,
        "real_subsample_tabicl": _metrics(TabICLClassifier(), Xtr[idx], ytr[idx], Xte, yte),
        "real_full_xgboost": _metrics(xgb.XGBClassifier(objective="binary:logistic"), Xtr, ytr, Xte, yte),
        "subsample_n": int(len(idx)),
        "seed": args.seed,
    }
    out = REPO_ROOT / "results" / "summaries" / "bank_ceiling.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"record -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
