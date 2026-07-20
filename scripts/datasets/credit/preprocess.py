"""Prepare the UCI "Default of Credit Card Clients" dataset for Tab-PE (issue #50).

Downloads the dataset (an Excel file inside a UCI zip), does a stratified
train/test split, and writes the Tab-PE input format:

    data/credit/credit_train.csv, credit_test.csv   (comma-separated, header)
    data/credit/credit_metadata.json                (int/float/cat/label_columns)
    data/credit/manifest.json                        (provenance)

30000 Taiwanese credit-card clients, binary target `default_payment` (default in
the next month; ~22% positive → imbalanced binary, like Bank/Adult). The Excel
file has a two-row header (a group row + the real names); we read with header=1
and drop the `ID` column. SEX/EDUCATION/MARRIAGE are integer-coded categoricals;
everything else numeric is integer-valued.

Run:
    uv run python scripts/datasets/credit/preprocess.py
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
OUT = REPO_ROOT / "data" / "credit"
SEED = 42
URLS = [
    "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip",
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00350/default%20of%20credit%20card%20clients.xls",
]
RAW_LABEL = "default payment next month"
LABEL = "default_payment"
CAT_COLS = ["SEX", "EDUCATION", "MARRIAGE"]


def _read_excel_bytes(data: bytes) -> pd.DataFrame:
    """Read the two-row-header credit Excel (xls or xlsx), trying both engines."""
    last = None
    for engine in ("xlrd", "openpyxl"):
        try:
            return pd.read_excel(io.BytesIO(data), header=1, engine=engine)
        except Exception as e:
            last = e
    raise RuntimeError(f"could not read credit Excel with xlrd/openpyxl: {last}")


def _download() -> tuple[pd.DataFrame, str, str]:
    last = None
    for url in URLS:
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()  # noqa: S310
            if url.endswith(".zip"):
                zf = zipfile.ZipFile(io.BytesIO(raw))
                xls = [n for n in zf.namelist() if n.lower().endswith((".xls", ".xlsx"))]
                if not xls:
                    raise FileNotFoundError(f"no Excel in {zf.namelist()}")
                data = zf.read(xls[0])
            else:
                data = raw
            sha = hashlib.sha256(data).hexdigest()
            df = _read_excel_bytes(data)
            return df, url, sha
        except Exception as e:
            last = e
    raise RuntimeError(f"could not fetch credit dataset: {last}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df, url, sha = _download()
    df.columns = [str(c).strip() for c in df.columns]
    print(f"downloaded from {url}: {df.shape}, columns={list(df.columns)}")

    if RAW_LABEL not in df.columns:
        raise ValueError(f"label column {RAW_LABEL!r} not found in {list(df.columns)}")
    df = df.rename(columns={RAW_LABEL: LABEL})
    if "ID" in df.columns:
        df = df.drop(columns=["ID"])

    features = [c for c in df.columns if c != LABEL]
    int_cols = [c for c in features if c not in CAT_COLS]
    for c in features + [LABEL]:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.isna().any():
            raise ValueError(f"non-numeric values in column {c!r}")
        df[c] = s.astype(int)

    train, test = train_test_split(df, test_size=0.2, random_state=SEED, stratify=df[LABEL])
    train.to_csv(OUT / "credit_train.csv", index=False)
    test.to_csv(OUT / "credit_test.csv", index=False)

    metadata = {"float_columns": [], "int_columns": int_cols,
                "cat_columns": CAT_COLS, "label_columns": [LABEL]}
    (OUT / "credit_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    manifest = {
        "dataset": "UCI Default of Credit Card Clients",
        "source_url": url,
        "excel_sha256": sha,
        "rows_total": int(df.shape[0]),
        "rows_train": int(train.shape[0]),
        "rows_test": int(test.shape[0]),
        "split": f"stratified 80/20 on {LABEL}",
        "seed": SEED,
        "label_balance_test": {str(k): int(v) for k, v in test[LABEL].value_counts().items()},
        "metadata": metadata,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    pos = test[LABEL].mean() * 100
    print(f"train {train.shape}, test {test.shape}, positive(test)={pos:.1f}%")
    print(f"cat={CAT_COLS}\nint={int_cols}")
    print(f"wrote -> {OUT.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
