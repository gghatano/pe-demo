# Official DPSDA Tab-PE implementation research

Deliverable for Task 001 / issue #3. This document records how the official
`microsoft/DPSDA` repository implements and exposes **Tabular Private Evolution
(Tab-PE)**, before any experiment code is written or large demos are run.

Every implementation claim cites a source path or command output. Statements that
are not directly verified from code are marked `UNCONFIRMED` and separated into the
"Interpretation and open questions" section.

## 1. Repository and pinned commit

- Repository: <https://github.com/microsoft/DPSDA> (MIT license).
- Pinned commit SHA: **`9078c67995499e6769113780200bbf1d788d3d60`**
  - Date: `2026-07-01T19:55:27Z`
  - Message: `add clip and raw pixel embeddings for images`
  - Source: `gh api repos/microsoft/DPSDA/commits/main` (latest `main` at time of research, 2026-07-15).
- Tabular support announcement: the top-level `README.md` states tabular
  generation "based on the Tab-PE paper ... has been released in this library"
  (dated 7/1/2026), and notes it "runs entirely on CPUs and requires no GPU,
  model training, or model inference."
- Paper: *Differentially Private Synthetic Data via APIs 4: Tabular Data*,
  arXiv <https://arxiv.org/abs/2606.08259>.

All source paths below are relative to the repository root at this SHA.

## 2. Package layout (`pe/`)

`pe/` top-level modules (from `gh api .../contents/pe`):

```text
pe/
├── api/         # generation APIs (random_api / variation_api)
├── callback/    # per-iteration callbacks: metrics, checkpointing, CSV export
├── constant/    # column-name constants
├── data/        # data loaders incl. tabular CSV loader
├── dp/          # differential privacy mechanism (Gaussian) + accounting
├── embedding/   # embeddings incl. TabularEmbedding
├── histogram/   # nearest-neighbor histogram (the DP-noised statistic)
├── llm/
├── logger/      # CSVPrint, LogPrint
├── logging/
├── metric_item/
├── population/  # PEPopulation, CompositePopulation (selection logic)
├── runner/      # pe.py: the PE main loop
└── util/
```

Tab-PE relevant subtrees:

- `pe/api/tabular/tabular_api.py` — `TabularAPI` (random init + variation/mutation).
- `pe/data/tabular/` — tabular CSV loader (`TabularCSV`), plus `pe/data/data.py`.
- `pe/embedding/` — `TabularEmbedding`.
- `pe/histogram/nearest_neighbors.py` — `NearestNeighbors` histogram.
- `pe/dp/dp.py`, `pe/dp/gaussian.py` — DP base class and Gaussian mechanism.
- `pe/callback/tabular/` — `classifier.py` (`TabClassifier`),
  `compute_wsd.py` (`ComputeWSD`), `compute_tvd.py` (`ComputeTVD`),
  `save_tab_to_csv.py` (`SaveTabToCSV`).
- `pe/runner/pe.py` — `PE` orchestrator (`run()` loop).

> Note: The examples directory (`example/`) is **excluded from the installed
> package** by `pyproject.toml` `[tool.setuptools.packages.find] exclude`
> (`"example*"` is listed). The demo scripts therefore live only in the repo tree,
> not inside the installed `pe` package. See §7 install decision.

## 3. Installation and Python version

Source: `pyproject.toml`.

- Package name: `private-evolution`, version `0.0.1`.
- `requires-python = ">=3.9"`.
- Core dependencies: `matplotlib`, `clean-fid`, `omegaconf`, `pandas`,
  `scikit-learn`, `generalimport`, `fld` (git), `openai`, `tenacity`.
- Tabular extra (`[project.optional-dependencies] tabular`):
  `tabicl`, `tabpfn`, `xgboost`, `numpy`, `POT`.

Official install instructions (`example/tabular/README.md`):

```bash
pip install private-evolution[tabular]
# or, editable from repo root:
pip install -e ".[tabular]"
```

The tabular classifier code additionally prints an install hint pointing at a
**git** install when `xgboost` / `tabicl` / `tabpfn` are missing
(`pe/callback/tabular/classifier.py`):

```text
pip install "private-evolution[tabular] @ git+https://github.com/microsoft/DPSDA.git"
```

`UNCONFIRMED`: Whether the published PyPI `private-evolution` wheel already
contains the tabular `pe.*` code (Tab-PE was released 7/1/2026 but the version
string is still `0.0.1`). Because the demo scripts are not packaged anyway, the
repo must be checked out regardless — see §7.

## 4. Tabular demo script inventory

Directory `example/tabular/` (from `gh api .../contents/example/tabular`):

```text
example/tabular/
├── README.md
├── xor_stress_test.py
├── scm.py
├── adult.py
├── breast_cancer.py
├── artificial_characters.py
└── person_activity.py
```

### 4.1 CLI options

| Script | Flag | Type | Default | Choices |
|---|---|---|---|---|
| `xor_stress_test.py` | `--num-features` | int | `1` | 1–7 (per README) |
| `scm.py` | `--prior-function` | str | `tree` | `tree`, `nn`, `rff` |
| `adult.py` | — | — | — | no CLI args |
| `breast_cancer.py` | — | — | — | no CLI args |
| `artificial_characters.py` | — | — | — | no CLI args |
| `person_activity.py` | — | — | — | no CLI args |

Source: `argparse` blocks in each script (e.g.
`xor_stress_test.py:25`, `scm.py:26`). Real-dataset scripts hard-code all
parameters in `__main__` and take no arguments.

### 4.2 Per-script hyperparameters (from `__main__`)

| Script | `num_iterations` | `num_samples` (schedule) | Classifier `model_name` | `ComputeWSD` degrees |
|---|---|---|---|---|
| `xor_stress_test.py` | 20 | 1000 | `tabpfn` | none (no WSD callback) |
| `scm.py` | 15 | 1000 | `tabicl` | 5, 6, 7 |
| `breast_cancer.py` | 20 | 150 | `tabicl` | 1, 2, 3 |
| `adult.py` | 30 | 1000 | `tabicl` | 1, 2, 3 |
| `artificial_characters.py` | 15 | 1000 | `tabicl` | 5, 6, 7 |
| `person_activity.py` | 15 | 5000 | `tabicl` | 5, 6, 7 |

Sources: line references — `xor_stress_test.py:47-48,81`; `scm.py:48-49,82,86-100`;
`breast_cancer.py:41-42,75,79-93`; `adult.py:42-43,75,79-93`;
`artificial_characters.py:42-43,76,80-94`; `person_activity.py:41-42,75,79-93`.

All six scripts share the same PE configuration block:

- `TabularAPI(mutation_rate_init=0.5, mutation_rate_final=0.01,
  decay_type="polynomial", gamma=0.2, num_iterations=num_iterations)`
  (`pe/api/tabular/tabular_api.py:15`).
- `TabularEmbedding(info=priv_info)`.
- `NearestNeighbors(embedding=embedding, mode="L2", lookahead_degree=0,
  backend="torch")` (`pe/histogram/nearest_neighbors.py`).
- Two populations combined by `CompositePopulation`:
  - `population1` (`initial_variation_api_fold=0, next_variation_api_fold=1,
    keep_selected=False, selection_mode="sample", histogram_threshold=0`) used for
    the first 5 iterations,
  - `population2` (`initial_variation_api_fold=3, next_variation_api_fold=3,
    keep_selected=True, selection_mode="rank"`) for the remaining
    `num_iterations - 5` iterations.
  - Combined as `populations=[population1]*5 + [population2]*(num_iterations-5)`
    (e.g. `xor_stress_test.py:76`).

### 4.3 Callbacks and loggers (shared)

- `SaveCheckpoints(<exp>/checkpoint)` — per-iteration checkpoints; runs resume from here.
- `SaveTabToCSV(output_folder=<exp>/synthetic_tab)` — writes synthetic CSVs.
- `TabClassifier(test_data=test_data, model_name=..., filter_criterion={VARIATION_API_FOLD_ID_COLUMN_NAME: -1})`.
- `ComputeWSD(...)` for the degrees listed above (all except XOR).
- Loggers: `CSVPrint(output_folder=<exp>)` and `LogPrint()`.

Source: e.g. `breast_cancer.py:72-100`.

## 5. Input data sources and download behavior

- All datasets are fetched at runtime by `TabularCSV(csv_path=..., metadata_path=...)`
  from **raw GitHub URLs** under
  `https://raw.githubusercontent.com/toan-vt/cloud-data-store/refs/heads/main/tabular/...`
  (the README links `https://github.com/toan-vt/cloud-data-store/tree/main/tabular`).
- Each experiment loads a `data_train.csv`, a `data_test.csv`, and a `metadata.json`.
- Simulated data paths: `tabular/sim/xor-stress-test/<n>_feature_xor/`,
  `tabular/sim/scm/<prior>/`.
- Real data paths: `tabular/real/breast-cancer/breast-cancer_{train,test,metadata}...`,
  and analogous paths for adult / artificial-characters / person-activity.
- Source: URL string literals, e.g. `xor_stress_test.py:33-45`, `scm.py:34-46`,
  `breast_cancer.py:27-39`.

`UNCONFIRMED`: exact row/column counts, categorical vs numerical split, and target
column per dataset — these come from each dataset's `metadata.json` and must be read
during environment/run tasks (task-003/007), not inferred here.

Reproducibility risk: data is pulled from a third-party GitHub account
(`toan-vt/cloud-data-store`) on `main`, i.e. an unpinned moving reference. To make
runs reproducible we should record the data-repo commit SHA at fetch time (open
item for task-002/003 contracts).

## 6. Outputs, metrics, and privacy accounting

### 6.1 Output layout (per experiment)

Each script writes to `results/tabular/<experiment>/` (README + `exp_folder`
literals):

```text
results/tabular/<experiment>/
├── log.txt          # setup_logging(log_file=...)
├── checkpoint/      # SaveCheckpoints — per-iteration, resumable
├── synthetic_tab/   # SaveTabToCSV — synthetic CSVs
└── <CSV metrics>    # CSVPrint(output_folder=<exp>)
```

Experiment folder names (from each `exp_folder`):
`xor_stress_test_<n>_features`, `scm_<prior>`,
`breast-cancer_composite_population`, `adult_composite_population`,
`artificial-characters_composite_population`, `person-activity_composite_population`.

### 6.2 Utility metric — `TabClassifier` (`pe/callback/tabular/classifier.py`)

- Trains a classifier on **synthetic** data, evaluates on the **real test set**
  (synthetic-train → real-test / TSTR). `X_train,y_train` come from `syn_df`;
  `X_test,y_test` from `test_data` (`classifier.py:120-123`).
- Models: `xgboost` (default), `tabicl`, or `tabpfn` (`classifier.py:37-70`).
  The demos use `tabpfn` (XOR) or `tabicl` (all others).
- Encoding: `LabelEncoder` for categorical + label columns, `MinMaxScaler` for
  numerical, fit on the concatenation of synthetic+test (`classifier.py:86-97`).
- Reported metrics (each ×100): `test_acc` (accuracy), macro `test_f1`; for binary
  tasks also `test_auc` (ROC-AUC). Multi-class AUC is set to `-1` / omitted
  (`classifier.py:124-141`).
- Only rows with `VARIATION_API_FOLD_ID_COLUMN_NAME == -1` are used
  (`filter_criterion` in each script), i.e. the final selected synthetic rows.

### 6.3 Statistical similarity — `ComputeWSD` (`pe/callback/tabular/compute_wsd.py`)

- Computes **k-way Wasserstein-style marginal distance** between private and
  synthetic data. `degree` = k (script-specified).
- For each combination of `degree` columns over all feature+label columns
  (`itertools.combinations`, `compute_wsd.py:106`):
  - `degree == 1`: 1-D `scipy.stats.wasserstein_distance` (`compute_wsd.py:127-128`).
  - `degree >= 2`: optimal-transport EMD via `ot.emd2` with a euclidean cost
    matrix and uniform marginals (`compute_wsd.py:130-133`).
- Categorical/label columns are `LabelEncoder`-encoded; all columns normalized to
  `[0,1]` using the **private** data's per-column range (`compute_wsd.py:89-104`).
- The final metric is the **mean** over all column-combinations
  (`compute_wsd.py:140`).
- Sampling: at most `num_samples` rows are used, sampled with `seed=42`
  (`ComputeWSD(..., seed=42)` in every script; `random_split`/`sample` at
  `compute_wsd.py:59-60,82-83`). This seed makes the WSD computation deterministic
  given fixed inputs, but does **not** seed PE generation itself.
- Metric name embeds config, e.g. `5way-wsd_1000samples_42seed_{...}`.

### 6.4 Privacy parameters and accounting

Run entry (`pe/runner/pe.py:122` `PE.run`) is called by every script with:

- `epsilon = 1.0` (all six scripts, e.g. `xor_stress_test.py:104`).
- `delta = 1.0 / num_private_samples / np.log(num_private_samples)`, where
  `num_private_samples = len(priv_data.data_frame)` (e.g. `xor_stress_test.py:87-88`).
  δ is therefore dataset-size dependent and computed at runtime.
- `num_samples_schedule = [num_samples] * num_iterations`.

Mechanism (`pe/dp/gaussian.py`, `class Gaussian(DP)`):

- The DP-protected statistic is the **nearest-neighbor histogram** of synthetic
  samples over private samples. Noise is added in `Gaussian.add_noise`:
  `CLEAN_HISTOGRAM + np.random.normal(scale=noise_multiplier, size=...)`
  (`gaussian.py:165-178`).
- `noise_multiplier` is derived from `(epsilon, delta, num_steps)` by
  `get_noise_multiplier` → `compute_epsilon` → `eps_Gaussian`/`delta_Gaussian`,
  i.e. an analytic Gaussian mechanism where the composed noise scale is
  `mu = sqrt(num_steps) / noise_multiplier` (`gaussian.py:45-108`). This is
  √-composition (Gaussian-DP / zCDP-style), not per-step ε splitting.
- `num_steps` passed to accounting is `len(num_samples_schedule) - 1`
  (`pe.py:157-162`). Since the schedule length equals `num_iterations`, the
  accounted step count is `num_iterations - 1` (e.g. 19 for XOR's 20). This is a
  precise code fact worth flagging for the reproduction write-up.
- The computed `epsilon`, `delta`, `noise_multiplier`, and `num_iterations` are
  logged via `execution_logger.info` (`gaussian.py:160-163`), so they land in
  `log.txt`.
- Default DP algorithm is `Gaussian()` when `PE(dp=None)` (`pe/runner/pe.py:33-35`);
  none of the tabular scripts override it.

## 7. Installation decision (recommendation)

- **The example scripts are not part of the installed package** (`example*`
  excluded in `pyproject.toml`). Running the official demos requires a **repo
  checkout at the pinned SHA** regardless of how `pe` is installed.
- To satisfy the reproducibility policy (`docs/spec.md` §2.2), pin the DPSDA
  dependency to the SHA rather than tracking `main`.
- Recommended for task-003: install `pe` from the pinned Git SHA and run the
  scripts from that same checkout, e.g.

  ```bash
  uv add "private-evolution[tabular] @ git+https://github.com/microsoft/DPSDA.git@9078c67995499e6769113780200bbf1d788d3d60"
  ```

  and separately clone/checkout the repo at the same SHA to execute
  `example/tabular/*.py`. Verify `uv sync` reconstructs the environment
  (task-003 validation).
- Python: `>=3.9` is declared, so the spec's default `3.12` is *permitted by
  DPSDA itself*. The binding constraint is likely the tabular extras
  (`tabpfn`, `tabicl`, `xgboost`, `POT`) — their own Python/OS support must be
  verified during environment build (open item, §8).

## 8. Interpretation and open questions

Marked `UNCONFIRMED` — resolve in later tasks, do not assume:

1. `UNCONFIRMED` — whether the PyPI wheel of `private-evolution==0.0.1` already
   includes the tabular `pe.*` modules, or whether the Git SHA is mandatory for the
   library code as well (it is mandatory for the example scripts either way). §3.
2. `UNCONFIRMED` — `tabpfn` / `tabicl` Python-version and platform constraints
   (these often require specific torch builds and may download model weights on
   first use). Blocks the Python-version decision in task-003.
3. `UNCONFIRMED` — whether `tabpfn`/`tabicl` perform network/model-weight downloads
   at runtime and whether they run acceptably CPU-only on Windows (the target OS).
4. `UNCONFIRMED` — per-dataset shape/target/column-type details (live in each
   dataset's `metadata.json` on `toan-vt/cloud-data-store`). Read during task-007.
5. `UNCONFIRMED` — the upstream data repo `toan-vt/cloud-data-store` is referenced
   at `main` (unpinned). Its content could change; record the fetched data SHA for
   reproducibility.
6. `UNCONFIRMED` — mapping of `initial_variation_api_fold` / `next_variation_api_fold`
   / `selection_mode` ("sample" vs "rank") / `keep_selected` to the paper's
   selection & crossover steps. Verify against `pe/population/*` and the paper in
   task for `content/method-tabpe.md`.
7. `UNCONFIRMED` — the exact NN-histogram construction and sensitivity assumption
   backing the Gaussian noise scale (read `pe/histogram/nearest_neighbors.py` in
   full and cross-check the paper before making privacy claims).
8. `UNCONFIRMED` — role of `ComputeTVD` (`pe/callback/tabular/compute_tvd.py`); it
   exists but is not used by the demo scripts.

## 9. Smoke-test candidate (input to task-003)

Confirmed lightest configuration for the first smoke test:
`python xor_stress_test.py --num-features 1` — smallest feature count, 20
iterations × 1000 samples, no WSD callbacks, single CLI knob, uses `tabpfn`.
`breast_cancer.py` is the next-lightest real dataset (150 samples/iteration).
Final choice depends on the `tabpfn` vs `tabicl` install/runtime cost, which
task-003 must measure.

## 10. Source-command appendix

```text
gh api repos/microsoft/DPSDA/commits/main
gh api repos/microsoft/DPSDA/contents/example/tabular?ref=<SHA>
gh api repos/microsoft/DPSDA/contents/pe?ref=<SHA>
gh api repos/microsoft/DPSDA/contents/pe/dp?ref=<SHA>
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/pyproject.toml
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/example/tabular/*.py
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/pe/dp/gaussian.py
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/pe/runner/pe.py
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/pe/api/tabular/tabular_api.py
raw.githubusercontent.com/microsoft/DPSDA/<SHA>/pe/callback/tabular/{classifier,compute_wsd}.py
```

SHA = `9078c67995499e6769113780200bbf1d788d3d60`.
