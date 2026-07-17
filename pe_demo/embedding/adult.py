"""Adult-specific embedding for Tab-PE (issue #24).

A documented deviation from the official ``pe.embedding.TabularEmbedding`` that
adds column-aware transforms for the Adult dataset. Three variants:

- ``official``       — identical to ``TabularEmbedding`` (regression baseline).
- ``robust_numeric`` — official, but ``fnlwgt`` uses a log transform and
  ``capital-gain``/``capital-loss`` are split into presence + log-amount.
- ``adult_semantic`` — ``robust_numeric`` plus: drop the ``education`` one-hot
  (use ``education-num`` as the ordinal primary), and add an
  ``education``/``education-num`` inconsistency penalty.

Design and the public constants (bounds + education→num table with sources) are in
``docs/research/adult-embedding.md``. Transform ranges for the non-official variants
come from **fixed public Adult domain bounds**, never learned from the private data.
The embedding is row-independent (each row's vector depends only on that row), so it
does not change the 1-record sensitivity of the nearest-neighbor histogram.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pe.embedding import Embedding
from pe.constant.data import TABULAR_DATA_COLUMN_NAME

VARIANTS = ("official", "robust_numeric", "adult_semantic", "public_fe")

NUMERIC_COLS = ["age", "fnlwgt", "education-num", "capital-gain", "capital-loss", "hours-per-week"]
CATEGORICAL_COLS = ["workclass", "education", "marital-status", "occupation",
                    "relationship", "race", "sex", "native-country"]
CAPITAL_COLS = ["capital-gain", "capital-loss"]
STANDARD_NUM_COLS = ["age", "hours-per-week"]  # education-num handled separately

# Fixed public domain bounds (UCI Adult). NOT derived from the private data.
# See docs/research/adult-embedding.md for sources.
PUBLIC_BOUNDS = {
    "age": (17, 90),
    "fnlwgt": (0, 1_500_000),
    "education-num": (1, 16),
    "capital-gain": (0, 99_999),
    "capital-loss": (0, 4_356),
    "hours-per-week": (1, 99),
}

# UCI Adult education -> education-num mapping (public).
EDUCATION_TO_NUM = {
    "Preschool": 1, "1st-4th": 2, "5th-6th": 3, "7th-8th": 4, "9th": 5, "10th": 6,
    "11th": 7, "12th": 8, "HS-grad": 9, "Some-college": 10, "Assoc-voc": 11,
    "Assoc-acdm": 12, "Bachelors": 13, "Masters": 14, "Prof-school": 15, "Doctorate": 16,
}

# --- public feature-engineering constants (variant "public_fe") ---
# Fixed, public bin edges from the common Adult ML literature (NOT private quantiles),
# so binning does not leak the private data. Sources in docs/research/adult-embedding.md.
AGE_BIN_EDGES = [35, 50]          # young <=35, middle (35,50], old >50
HOURS_BIN_EDGES = [30, 40, 60]    # part-time / standard / long / excessive
US_COUNTRY = "United-States"      # native-country grouped to US vs non-US
# Categoricals kept as-is (one-hot) in public_fe (education & native-country handled specially).
PUBLIC_FE_CAT_COLS = ["workclass", "marital-status", "occupation", "relationship", "race", "sex"]


@dataclass(frozen=True)
class AdultEmbeddingConfig:
    """Configuration for :class:`AdultEmbedding`. Weights are fixed per variant and
    must not be tuned against the private data (see the DP note in the design doc)."""

    variant: str
    fnlwgt_weight: float = 0.25
    capital_presence_weight: float = 1.0 / 3.0
    capital_amount_weight: float = 1.0
    education_weight: float = 1.0
    education_consistency_weight: float = 1.0 / 3.0
    categorical_weight: float = 1.0 / 3.0
    numerical_weight: float = 1.0

    def __post_init__(self):
        if self.variant not in VARIANTS:
            raise ValueError(f"variant must be one of {VARIANTS}, got {self.variant!r}")


class AdultEmbedding(Embedding):
    """Adult-aware embedding. See module docstring and design doc."""

    def __init__(self, info: dict, config: AdultEmbeddingConfig):
        super().__init__()
        self._info = info
        self._config = config

    # --- pure vector construction (unit-testable, no pe.data.Data needed) ---

    def _minmax_info(self, x: np.ndarray, col: str, weight: float) -> np.ndarray:
        """min-max using the metadata (info) bounds, matching TabularEmbedding
        (no clipping). Used by the official variant and for the columns the
        non-official variants keep identical to official."""
        lo = self._info[col]["min"]
        hi = self._info[col]["max"]
        denom = (hi - lo) if hi != lo else 1.0
        return ((x.astype(float) - lo) * weight / denom).reshape(-1, 1)

    @staticmethod
    def _log_public(x: np.ndarray, col: str, weight: float) -> np.ndarray:
        """log1p normalized by the fixed public max bound, clipped to [0,1]."""
        hi = PUBLIC_BOUNDS[col][1]
        v = np.log1p(np.clip(x.astype(float), 0, None)) / np.log1p(hi)
        return (np.clip(v, 0.0, 1.0) * weight).reshape(-1, 1)

    def _onehot(self, values: np.ndarray, col: str, weight: float) -> np.ndarray:
        """One-hot using the info category list. Unknown categories raise (they are
        NOT silently mapped to category 0, unlike the official embedding)."""
        categories = self._info[col]["categories"]
        idx = {c: i for i, c in enumerate(categories)}
        n, k = len(values), len(categories)
        out = np.zeros((n, k))
        for i, v in enumerate(values):
            if v not in idx:
                raise ValueError(f"AdultEmbedding: unknown category {v!r} in column {col!r}")
            out[i, idx[v]] = weight
        return out

    def _education_penalty(self, features_df: pd.DataFrame) -> np.ndarray:
        ed = features_df["education"].to_numpy()
        ednum = features_df["education-num"].to_numpy()
        pen = np.zeros((len(ed), 1))
        for i, (e, n) in enumerate(zip(ed, ednum)):
            expected = EDUCATION_TO_NUM.get(e)
            if expected is None:
                raise ValueError(f"AdultEmbedding: unknown education {e!r}")
            if int(round(float(n))) != expected:
                pen[i, 0] = 1.0
        return pen

    # --- public feature-engineering helpers (variant "public_fe") ---

    @staticmethod
    def _ordinal_bins(x: np.ndarray, edges: list[float], weight: float) -> np.ndarray:
        """Ordinal bin index (via fixed public edges) normalized to [0,1] x weight.
        Uses np.digitize with public constants, so it does not learn from private data."""
        idx = np.digitize(x.astype(float), edges)  # 0..len(edges)
        denom = float(len(edges)) or 1.0
        return ((idx / denom) * weight).reshape(-1, 1)

    @staticmethod
    def _extra_income_onehot(gain: np.ndarray, loss: np.ndarray, weight: float) -> np.ndarray:
        """capital-gain/loss -> {none, positive, negative} one-hot (public sign encoding)."""
        gain = gain.astype(float)
        loss = loss.astype(float)
        n = len(gain)
        out = np.zeros((n, 3))
        positive = gain > 0
        negative = (~positive) & (loss > 0)
        none = ~(positive | negative)
        out[none, 0] = weight
        out[positive, 1] = weight
        out[negative, 2] = weight
        return out

    def _us_nonus_onehot(self, country: np.ndarray, weight: float) -> np.ndarray:
        """native-country grouped into US vs non-US (public geography, 2 dims)."""
        out = np.zeros((len(country), 2))
        for i, v in enumerate(country):
            if v not in self._info["native-country"]["categories"]:
                raise ValueError(f"AdultEmbedding: unknown category {v!r} in column 'native-country'")
            out[i, 0 if v == US_COUNTRY else 1] = weight
        return out

    def compute_vectors(self, features_df: pd.DataFrame) -> np.ndarray:
        """Build the embedding matrix (n_samples x dim) from a features DataFrame
        whose columns are the Adult feature names (label excluded)."""
        missing = [c for c in NUMERIC_COLS + CATEGORICAL_COLS if c not in features_df.columns]
        if missing:
            raise ValueError(f"AdultEmbedding: missing feature columns {missing}")

        cfg = self._config
        parts: list[np.ndarray] = []

        if cfg.variant == "public_fe":
            # Public, non-leaking feature engineering (fixed public rules; the private
            # target `income` and private statistics are never used).
            nw, cw = cfg.numerical_weight, cfg.categorical_weight
            parts.append(self._ordinal_bins(features_df["age"].to_numpy(), AGE_BIN_EDGES, nw))
            parts.append(self._ordinal_bins(features_df["hours-per-week"].to_numpy(), HOURS_BIN_EDGES, nw))
            parts.append(self._minmax_info(features_df["education-num"].to_numpy(), "education-num", nw))
            # capital: 3-way sign one-hot + a public log-magnitude (drops raw gain/loss & fnlwgt).
            gain = features_df["capital-gain"].to_numpy()
            loss = features_df["capital-loss"].to_numpy()
            parts.append(self._extra_income_onehot(gain, loss, cw))
            parts.append(self._log_public(gain.astype(float) + loss.astype(float),
                                          "capital-gain", cfg.capital_amount_weight))
            for col in PUBLIC_FE_CAT_COLS:
                parts.append(self._onehot(features_df[col].to_numpy(), col, cw))
            parts.append(self._us_nonus_onehot(features_df["native-country"].to_numpy(), cw))
            return np.concatenate(parts, axis=1)

        if cfg.variant == "official":
            for col in NUMERIC_COLS:
                parts.append(self._minmax_info(features_df[col].to_numpy(), col, cfg.numerical_weight))
            for col in CATEGORICAL_COLS:
                parts.append(self._onehot(features_df[col].to_numpy(), col, cfg.categorical_weight))
            return np.concatenate(parts, axis=1)

        # robust_numeric / adult_semantic share the numeric handling.
        for col in STANDARD_NUM_COLS:
            parts.append(self._minmax_info(features_df[col].to_numpy(), col, cfg.numerical_weight))

        ednum_weight = cfg.education_weight if cfg.variant == "adult_semantic" else cfg.numerical_weight
        parts.append(self._minmax_info(features_df["education-num"].to_numpy(), "education-num", ednum_weight))

        parts.append(self._log_public(features_df["fnlwgt"].to_numpy(), "fnlwgt", cfg.fnlwgt_weight))

        for col in CAPITAL_COLS:
            x = features_df[col].to_numpy().astype(float)
            presence = (x > 0).astype(float).reshape(-1, 1) * cfg.capital_presence_weight
            amount = self._log_public(x, col, cfg.capital_amount_weight)
            parts.append(presence)
            parts.append(amount)

        cat_cols = (CATEGORICAL_COLS if cfg.variant == "robust_numeric"
                    else [c for c in CATEGORICAL_COLS if c != "education"])
        for col in cat_cols:
            parts.append(self._onehot(features_df[col].to_numpy(), col, cfg.categorical_weight))

        if cfg.variant == "adult_semantic":
            parts.append(self._education_penalty(features_df) * cfg.education_consistency_weight)

        return np.concatenate(parts, axis=1)

    # --- pe.Embedding interface ---

    def compute_embedding(self, data):
        uncomputed = self.filter_uncomputed_rows(data)
        if len(uncomputed.data_frame) == 0:
            return data
        feature_columns = data.metadata["feature_columns"]
        features_list = uncomputed.data_frame[TABULAR_DATA_COLUMN_NAME].tolist()
        features_df = pd.DataFrame(features_list, columns=feature_columns)
        vectors = self.compute_vectors(features_df)
        if not np.isfinite(vectors).all():
            raise ValueError("AdultEmbedding: embedding contains NaN/Inf")
        uncomputed.data_frame[self.column_name] = pd.Series(
            list(vectors), index=uncomputed.data_frame.index
        )
        return self.merge_computed_rows(data, uncomputed)
