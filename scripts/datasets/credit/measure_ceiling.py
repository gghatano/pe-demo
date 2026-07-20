"""Measure the Credit Card Default downstream ceiling (issue #50).

Trains classifiers on REAL data → REAL test to bound the binary task, and writes a
tracked JSON (cf. #42): results/summaries/credit_ceiling.json. Reports majority
baseline, tabicl on a real subsample of `--n` (same size as the synthetic training
set), and xgboost on the full real train. Metrics: accuracy, macro F1, AUC.

Run:
    uv run python scripts/datasets/credit/measure_ceiling.py
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
DATA = REPO_ROOT / "data" / "credit"


def _load():
    meta = json.loads((DATA / "credit_metadata.json").read_text())
    feat = meta["cat_columns"] + meta["int_columns"] + meta["float_columns"]
    label = meta["label_columns"][0]
    tr = pd.read_csv(DATA / "credit_train.csv")
    te = pd.read_csv(DATA / "credit_test.csv")
    cat = set(meta["cat_columns"])
    for col in feat:
        merged = pd.concat([tr[col], te[col]])
        if col in cat:
            le = LabelEncoder().fit(merged.astype(str))
            tr[col] = le.transform(tr[col].astype(str)); te[col] = le.transform(te[col].astype(str))
        else:
            sc = MinMaxScaler().fit(merged.values.reshape(-1, 1))
            tr[col] = sc.transform(tr[col].values.reshape(-1, 1)); te[col] = sc.transform(te[col].values.reshape(-1, 1))
    return tr[feat].values, tr[label].values, te[feat].values, te[label].values


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
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    Xtr, ytr, Xte, yte = _load()
    _, counts = np.unique(yte, return_counts=True)
    majority = round(counts.max() / counts.sum() * 100, 2)
    rng = np.random.default_rng(args.seed)
    idx = rng.choice(len(Xtr), size=min(args.n, len(Xtr)), replace=False)

    from tabicl import TabICLClassifier
    import xgboost as xgb
    result = {
        "dataset": "Default of Credit Card Clients", "test_n": int(len(Xte)),
        "majority_baseline_acc": majority,
        "real_subsample_tabicl": _metrics(TabICLClassifier(), Xtr[idx], ytr[idx], Xte, yte),
        "real_full_xgboost": _metrics(xgb.XGBClassifier(objective="binary:logistic"), Xtr, ytr, Xte, yte),
        "subsample_n": int(len(idx)), "seed": args.seed,
    }
    out = REPO_ROOT / "results" / "summaries" / "credit_ceiling.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
