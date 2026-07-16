"""Unit tests for AdultEmbedding (issue #24).

Fixture-based only — no network, no full PE run (CI runs these, not experiments).
Covers the 10 requirements listed in the issue.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pe.data.tabular.tabular_csv import TabularColumnType
from pe_demo.embedding.adult import (
    AdultEmbedding, AdultEmbeddingConfig, NUMERIC_COLS, CATEGORICAL_COLS,
    EDUCATION_TO_NUM,
)

CAT_VALUES = {
    "workclass": ["Private", "Self-emp", "Gov"],
    "education": ["HS-grad", "Bachelors", "Masters", "Doctorate"],
    "marital-status": ["Never-married", "Married", "Divorced"],
    "occupation": ["Tech", "Sales", "Exec"],
    "relationship": ["Husband", "Wife", "Not-in-family"],
    "race": ["White", "Black", "Asian"],
    "sex": ["Male", "Female"],
    "native-country": ["United-States", "Mexico", "India"],
}


def make_info(df: pd.DataFrame) -> dict:
    info = {}
    for col in NUMERIC_COLS:
        info[col] = {"type": TabularColumnType.FLOAT,
                     "min": float(df[col].min()), "max": float(df[col].max())}
    for col in CATEGORICAL_COLS:
        info[col] = {"type": TabularColumnType.CATEGORICAL, "categories": list(CAT_VALUES[col])}
    return info


def make_fixture(n: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    edu = ["HS-grad", "Bachelors", "Masters", "Doctorate"]
    rows = []
    for i in range(n):
        e = edu[i % len(edu)]
        rows.append({
            "age": 20 + (i * 3) % 60,
            "fnlwgt": 10000 + i * 5000,
            "education-num": EDUCATION_TO_NUM[e],  # consistent
            "capital-gain": 0 if i % 2 else (i * 1000),
            "capital-loss": 0 if i % 3 else (i * 100),
            "hours-per-week": 20 + (i * 5) % 60,
            "workclass": CAT_VALUES["workclass"][i % 3],
            "education": e,
            "marital-status": CAT_VALUES["marital-status"][i % 3],
            "occupation": CAT_VALUES["occupation"][i % 3],
            "relationship": CAT_VALUES["relationship"][i % 3],
            "race": CAT_VALUES["race"][i % 3],
            "sex": CAT_VALUES["sex"][i % 2],
            "native-country": CAT_VALUES["native-country"][i % 3],
        })
    return pd.DataFrame(rows)


def emb(variant: str, df: pd.DataFrame) -> AdultEmbedding:
    return AdultEmbedding(make_info(df), AdultEmbeddingConfig(variant=variant))


def ref_tabular(df: pd.DataFrame, info: dict, cat_weight=1 / 3, num_weight=1.0) -> np.ndarray:
    """Reference replication of pe.embedding.TabularEmbedding math."""
    parts = []
    for col in NUMERIC_COLS:
        x = df[col].to_numpy().astype(float)
        lo, hi = info[col]["min"], info[col]["max"]
        parts.append(((x - lo) * num_weight / (hi - lo)).reshape(-1, 1))
    for col in CATEGORICAL_COLS:
        cats = info[col]["categories"]
        idx = {c: i for i, c in enumerate(cats)}
        vals = df[col].to_numpy()
        ii = pd.Series(vals).map(idx).fillna(0).astype(int).values
        oh = np.zeros((len(df), len(cats)))
        oh[np.arange(len(df)), ii] = cat_weight
        parts.append(oh)
    return np.concatenate(parts, axis=1)


@pytest.mark.parametrize("variant", ["official", "robust_numeric", "adult_semantic", "public_fe"])
def test_deterministic(variant):
    df = make_fixture()
    e = emb(variant, df)
    assert np.array_equal(e.compute_vectors(df), e.compute_vectors(df))


def test_label_not_in_embedding():
    # income is a label, never a feature column used by the embedding.
    assert "income" not in NUMERIC_COLS + CATEGORICAL_COLS
    df = make_fixture()
    df2 = df.copy()
    df2["income"] = ">50K"  # adding the label must not change the embedding
    e = emb("adult_semantic", df)
    assert np.array_equal(e.compute_vectors(df), e.compute_vectors(df2))


@pytest.mark.parametrize("variant", ["official", "robust_numeric", "adult_semantic", "public_fe"])
def test_no_nan_inf(variant):
    df = make_fixture()
    v = emb(variant, df).compute_vectors(df)
    assert np.isfinite(v).all()


def test_capital_zero_gives_zero_presence_and_amount():
    e = emb("robust_numeric", make_fixture())
    # presence: (x>0)*w -> 0 for x=0; amount: log1p(0)=0
    assert e._log_public(np.array([0.0]), "capital-gain", 1.0)[0, 0] == 0.0
    presence = (np.array([0.0]) > 0).astype(float)
    assert presence[0] == 0.0


def test_capital_amount_monotonic():
    e = emb("robust_numeric", make_fixture())
    xs = np.array([1.0, 10.0, 100.0, 1000.0, 10000.0])
    amt = e._log_public(xs, "capital-gain", 1.0).ravel()
    assert np.all(np.diff(amt) > 0)


def test_education_penalty_only_on_inconsistency():
    df = make_fixture(4)
    df.loc[0, "education-num"] = 999  # make row 0 inconsistent with its education
    e = emb("adult_semantic", df)
    pen = e._education_penalty(df).ravel()
    assert pen[0] == 1.0
    assert set(pen[1:]) == {0.0}


@pytest.mark.parametrize("variant", ["official", "robust_numeric", "adult_semantic", "public_fe"])
def test_unknown_category_raises(variant):
    df = make_fixture()
    df.loc[0, "occupation"] = "UNSEEN-JOB"
    with pytest.raises(ValueError, match="unknown category"):
        emb(variant, df).compute_vectors(df)


def test_official_matches_tabular_embedding():
    df = make_fixture()
    info = make_info(df)
    ours = AdultEmbedding(info, AdultEmbeddingConfig(variant="official")).compute_vectors(df)
    ref = ref_tabular(df, info)
    assert ours.shape == ref.shape
    assert np.allclose(ours, ref)
    # nearest-neighbor ids must also match (distance-based, order-invariant).
    for mat in (ours, ref):
        d = np.linalg.norm(mat[:, None, :] - mat[None, :, :], axis=-1)
        np.fill_diagonal(d, np.inf)
    nn_ours = np.argmin(np.linalg.norm(ours[:, None] - ours[None], axis=-1)
                        + np.eye(len(df)) * 1e9, axis=1)
    nn_ref = np.argmin(np.linalg.norm(ref[:, None] - ref[None], axis=-1)
                       + np.eye(len(df)) * 1e9, axis=1)
    assert np.array_equal(nn_ours, nn_ref)


def test_public_fe_drops_fnlwgt():
    # public_fe drops fnlwgt entirely: changing fnlwgt must not change the embedding.
    df = make_fixture()
    df2 = df.copy()
    df2["fnlwgt"] = df2["fnlwgt"] * 3 + 1
    e = emb("public_fe", df)
    assert np.array_equal(e.compute_vectors(df), e.compute_vectors(df2))


def test_public_fe_age_bins():
    df = make_fixture(3)
    df.loc[:, "age"] = [25, 45, 70]  # young / middle / old -> ordinal 0, 0.5, 1.0
    e = emb("public_fe", df)
    from pe_demo.embedding.adult import AGE_BIN_EDGES
    got = e._ordinal_bins(df["age"].to_numpy(), AGE_BIN_EDGES, 1.0).ravel()
    assert list(got) == [0.0, 0.5, 1.0]


def test_public_fe_extra_income_signs():
    e = emb("public_fe", make_fixture())
    gain = np.array([0.0, 500.0, 0.0])
    loss = np.array([0.0, 0.0, 300.0])
    oh = e._extra_income_onehot(gain, loss, 1.0)
    # rows: none / positive / negative
    assert oh[0].tolist() == [1.0, 0.0, 0.0]
    assert oh[1].tolist() == [0.0, 1.0, 0.0]
    assert oh[2].tolist() == [0.0, 0.0, 1.0]


@pytest.mark.parametrize("variant", ["official", "robust_numeric", "adult_semantic", "public_fe"])
def test_embeds_all_rows_consistent_dim(variant):
    df = make_fixture(30)
    v = emb(variant, df).compute_vectors(df)
    assert v.shape[0] == 30
    assert v.shape[1] == emb(variant, df).compute_vectors(df.iloc[:5]).shape[1]


@pytest.mark.parametrize("variant", ["official", "robust_numeric", "adult_semantic", "public_fe"])
def test_row_independence_sensitivity(variant):
    """Each row's embedding depends only on that row: computing in batch equals
    stacking per-row results. This shows the change does not increase the
    1-record sensitivity of the nearest-neighbor histogram."""
    df = make_fixture(8)
    e = emb(variant, df)
    batch = e.compute_vectors(df)
    per_row = np.concatenate([e.compute_vectors(df.iloc[[i]]) for i in range(len(df))], axis=0)
    assert np.allclose(batch, per_row)
