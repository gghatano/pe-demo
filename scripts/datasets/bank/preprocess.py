"""Prepare the UCI Bank Marketing dataset for Tab-PE (issue #49).

Downloads `bank-full.csv` from the UCI archive, drops the leaky `duration` column
(known only after the call; UCI recommends discarding it for realistic modeling),
does a stratified train/test split, and writes the Tab-PE input format:

    data/bank/bank_train.csv, bank_test.csv   (comma-separated, with header)
    data/bank/bank_metadata.json              (float/int/cat/label_columns)
    data/bank/manifest.json                   (provenance: source, sha256, rows, split)

Column ranges/categories are derived from the data by TabularCSV at load time
(same as the official demos); this script only selects columns and splits rows.

Run:
    uv run python scripts/datasets/bank/preprocess.py
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "data" / "bank"
SEED = 42

# Candidate sources (UCI moved URLs over time; try in order).
URLS = [
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank.zip",
    "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
]

INT_COLS = ["age", "balance", "day", "campaign", "pdays", "previous"]
CAT_COLS = ["job", "marital", "education", "default", "housing", "loan",
            "contact", "month", "poutcome"]
LABEL_COLS = ["y"]
DROP_COLS = ["duration"]  # leaky: determined by the outcome (UCI advises dropping)


def _read_bank_full() -> tuple[pd.DataFrame, str, str]:
    """Return (dataframe, source_url, sha256 of bank-full.csv bytes)."""
    last_err = None
    for url in URLS:
        try:
            raw = urllib.request.urlopen(url, timeout=60).read()  # noqa: S310
            zf = zipfile.ZipFile(io.BytesIO(raw))
            # bank+marketing.zip nests bank.zip; bank.zip has bank-full.csv.
            names = zf.namelist()
            if "bank-full.csv" in names:
                data = zf.read("bank-full.csv")
            elif "bank.zip" in names:
                inner = zipfile.ZipFile(io.BytesIO(zf.read("bank.zip")))
                data = inner.read("bank-full.csv")
            else:
                raise FileNotFoundError(f"bank-full.csv not in {names}")
            sha = hashlib.sha256(data).hexdigest()
            df = pd.read_csv(io.BytesIO(data), sep=";")
            return df, url, sha
        except Exception as e:  # try next url
            last_err = e
    raise RuntimeError(f"could not fetch bank-full.csv: {last_err}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df, url, sha = _read_bank_full()
    print(f"downloaded from {url}: {df.shape[0]} rows, columns={list(df.columns)}")

    keep = CAT_COLS + INT_COLS + LABEL_COLS
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"expected columns missing: {missing}")
    df = df[keep].copy()  # drops `duration` and anything unexpected

    train, test = train_test_split(df, test_size=0.2, random_state=SEED,
                                   stratify=df[LABEL_COLS[0]])
    train.to_csv(OUT / "bank_train.csv", index=False)
    test.to_csv(OUT / "bank_test.csv", index=False)

    metadata = {"float_columns": [], "int_columns": INT_COLS,
                "cat_columns": CAT_COLS, "label_columns": LABEL_COLS}
    (OUT / "bank_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    manifest = {
        "dataset": "UCI Bank Marketing (bank-full.csv)",
        "source_url": url,
        "bank_full_sha256": sha,
        "dropped_columns": DROP_COLS,
        "rows_total": int(df.shape[0]),
        "rows_train": int(train.shape[0]),
        "rows_test": int(test.shape[0]),
        "split": "stratified 80/20 on y",
        "seed": SEED,
        "label_balance_test": {str(k): int(v) for k, v in test[LABEL_COLS[0]].value_counts().items()},
        "metadata": metadata,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"train {train.shape}, test {test.shape}")
    print(f"test label balance: {manifest['label_balance_test']}")
    print(f"wrote -> {OUT.relative_to(REPO_ROOT)}/ (bank_train.csv, bank_test.csv, "
          "bank_metadata.json, manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
