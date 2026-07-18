"""Prepare the UCI Dry Bean dataset for Tab-PE (issue #55).

Downloads the Dry Bean dataset (an .xlsx inside a UCI zip), does a stratified
train/test split, and writes the Tab-PE input format:

    data/drybean/drybean_train.csv, drybean_test.csv   (comma-separated, header)
    data/drybean/drybean_metadata.json                 (int/float/cat/label_columns)
    data/drybean/manifest.json                          (provenance)

All 16 features are numeric (geometric shape features); the label is `Class`
(7 bean varieties). Numeric columns are split into int/float by whether their
values are integral. No leaky columns.

Run:
    uv run python scripts/datasets/drybean/preprocess.py
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "data" / "drybean"
SEED = 42
URLS = [
    "https://archive.ics.uci.edu/static/public/602/dry+bean+dataset.zip",
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00602/DryBeanDataset.zip",
]
LABEL = "Class"


def _read_drybean() -> tuple[pd.DataFrame, str, str]:
    last = None
    for url in URLS:
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()  # noqa: S310
            zf = zipfile.ZipFile(io.BytesIO(raw))
            xlsx = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
            if not xlsx:
                raise FileNotFoundError(f"no .xlsx in {zf.namelist()}")
            data = zf.read(xlsx[0])
            sha = hashlib.sha256(data).hexdigest()
            df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
            return df, url, sha
        except Exception as e:
            last = e
    raise RuntimeError(f"could not fetch Dry Bean: {last}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df, url, sha = _read_drybean()
    df.columns = [str(c).strip() for c in df.columns]
    print(f"downloaded from {url}: {df.shape}, columns={list(df.columns)}")
    if LABEL not in df.columns:
        raise ValueError(f"label column {LABEL!r} not found in {list(df.columns)}")

    features = [c for c in df.columns if c != LABEL]
    int_cols, float_cols = [], []
    for c in features:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.isna().any():
            raise ValueError(f"non-numeric values in feature {c!r}")
        df[c] = s
        (int_cols if np.all(np.equal(np.mod(s.to_numpy(), 1), 0)) else float_cols).append(c)

    train, test = train_test_split(df, test_size=0.2, random_state=SEED, stratify=df[LABEL])
    train.to_csv(OUT / "drybean_train.csv", index=False)
    test.to_csv(OUT / "drybean_test.csv", index=False)

    metadata = {"float_columns": float_cols, "int_columns": int_cols,
                "cat_columns": [], "label_columns": [LABEL]}
    (OUT / "drybean_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    manifest = {
        "dataset": "UCI Dry Bean Dataset",
        "source_url": url,
        "xlsx_sha256": sha,
        "rows_total": int(df.shape[0]),
        "rows_train": int(train.shape[0]),
        "rows_test": int(test.shape[0]),
        "split": "stratified 80/20 on Class",
        "seed": SEED,
        "n_classes": int(df[LABEL].nunique()),
        "class_balance": {str(k): int(v) for k, v in df[LABEL].value_counts().items()},
        "metadata": metadata,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"train {train.shape}, test {test.shape}, classes={manifest['n_classes']}")
    print(f"class balance: {manifest['class_balance']}")
    print(f"int={int_cols}\nfloat={float_cols}")
    print(f"wrote -> {OUT.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
