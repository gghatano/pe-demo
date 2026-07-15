# Reproduction log

This log records decisions and execution evidence for the Tab-PE official demo reproduction.

## 2026-07-15: Development preparation

- Created task breakdown under `docs/tasks/` from `docs/spec.md`.
- Defined the initial experiment plan in `docs/plans/experiment-plan.md`.
- Created GitHub orchestration issue #1 and child issues #2 through #6.
- No official DPSDA code has been downloaded or executed yet.
- No Python dependencies have been installed yet.

## GitHub issue map

- #1: Orchestrator priority and dependency map.
- #3: Official DPSDA Tab-PE implementation research.
- #2: uv environment and Smoke Test.
- #5: XOR official reproduction.
- #4: SCM and real-data official demos.
- #6: Aggregation, Markdown, HTML, and final review.

## 2026-07-15: Official implementation research (#3)

- Pinned DPSDA commit SHA `9078c67995499e6769113780200bbf1d788d3d60` (2026-07-01).
- Findings in `docs/research/official-implementation.md`.

## 2026-07-15: Environment build + smoke test (#2)

Environment:

- `pyproject.toml` pins `private-evolution[tabular] @ git+.../DPSDA.git@9078c67...`.
- Python **3.12.13** (uv-managed). `requires-python = ">=3.12"`. DPSDA allows `>=3.9`.
- `uv lock` resolved 98 packages; `uv sync` installed torch/tabpfn/tabicl/xgboost/POT.
- `uv.lock` committed. `uv sync` reconstructs the environment on a clean checkout.
- DPSDA is vendored at the pinned SHA under `external/DPSDA` (gitignored); the demo
  scripts are excluded from the installed package, so the checkout is required.

Minimal fixes applied (non-algorithmic; recorded per spec §13):

1. **`azure-identity` added.** `from pe.api import TabularAPI` (used verbatim by the
   official demos) eagerly imports the text/LLM path
   (`pe/api/__init__.py` → `pe.llm.azure_openai` → `azure.identity`). `pe/__init__.py`
   marks `openai`/`transformers`/etc. optional via `generalimport` but omits `azure`,
   so the import fails with only `[tabular]` installed. `azure-identity` is already
   listed in DPSDA's `[text]`/`[image]` extras; adding it only satisfies an unused
   Azure-OpenAI import path and does not touch Tab-PE, privacy, or evaluation.
2. **Smoke target switched from XOR to Breast Cancer.** `xor_stress_test.py` hardcodes
   the `tabpfn` classifier, which requires a one-time **interactive license
   acceptance + `TABPFN_TOKEN`** (account registration at ux.priorlabs.ai) to download
   weights — not possible in this non-interactive/autonomous context. The other five
   demos use `tabicl`, which downloads weights from the HuggingFace Hub with no license
   gate and runs CPU-only. `breast_cancer.py` (the lightest `tabicl` demo, and Phase 4
   priority #1) was used as the smoke test. XOR reproduction (#5) is **blocked** on a
   `TABPFN_TOKEN` unless its classifier is changed — flagged for #5.

Smoke test result (`results/summaries/smoke_breast_cancer.json`):

- Command: `python breast_cancer.py` (unmodified), run via `scripts/run_smoke.py`.
- Status: **EXECUTED** (returncode 0), runtime **230.5 s** on AMD Ryzen 5 7640HS,
  Windows 11 (10.0.26200), 25.8 GB RAM.
- Confirmed end-to-end: dataset download, 20 PE iterations, 22 checkpoints,
  20 synthetic CSVs, classifier + WSD evaluation.
- Final-iteration metrics (from official `log.txt`): classifier test accuracy
  **91.86%**, macro F1 **91.44**, AUC **98.73**; 1/2/3-way WSD =
  **0.1644 / 0.2767 / 0.3749**.
- DP accounting (logged): `epsilon=1.0, delta=0.00041971, noise_multiplier=12.266,
  num_iterations=19` (accounted steps = configured `num_iterations` − 1, as noted in
  the research doc).
- Status is `EXECUTED`, **not** `REPRODUCED`: no official published Breast Cancer
  number was compared against (that comparison belongs to #4).

## 2026-07-16: XOR reproduction with classifier NOT_RUN (#5)

Decision (from the user): do **not** obtain a `TABPFN_TOKEN` and do **not** swap
the classifier; run XOR generation and record the tabpfn classifier utility as
`NOT_RUN`.

- Ran `scripts/experiments/xor_no_classifier.py --num-features 1` and `2`. This is
  a **documented deviation** from `xor_stress_test.py`: the sole change is removal
  of the `TabClassifier(model_name="tabpfn")` callback (license-gated). The Tab-PE
  algorithm, composite population, embedding, NN histogram, and the `epsilon=1.0` /
  `delta=1/n/ln(n)` Gaussian mechanism are byte-for-byte the official settings.
- Both runs completed generation end-to-end: 20 iterations, 22 checkpoints,
  20 synthetic CSVs each. Runtimes 5.4 s / 5.7 s. XOR 1-feature has 35 000 private
  rows → `delta≈2.73e-6`, `noise_multiplier≈17.5`, accounted `num_iterations=19`.
- Classifier accuracy: **NOT_RUN** (blocked on `TABPFN_TOKEN`). WSD: not part of the
  official XOR script. So XOR has **no comparable utility number** in this phase.
- Status: generation `EXECUTED`; classifier metric `NOT_RUN`. Records in
  `results/summaries/xor_xor_stress_test_{1,2}_features.json`.

## 2026-07-16: SCM + artificial_characters demos (#4, lighter subset)

Decision (from the user): run only the lighter demos now; defer heavier
`adult.py` (30 iterations) and `person_activity.py` (5000 samples).

- Ran the *unmodified* official `scm.py --prior-function rff` and
  `artificial_characters.py` (both `tabicl`) via `scripts/run_experiment.py`.
- **SCM (rff):** `EXECUTED`, 739 s. 15 synthetic CSVs, 17 checkpoints. Final
  metrics — classifier acc **61.08%**, macro F1 **61.03**, AUC **64.14**; 5/6/7-way
  WSD = **0.1460 / 0.1860 / 0.2243**. DP `epsilon=1.0, delta=2.73e-6,
  noise_multiplier=15.02, num_iterations=14`.
- **Artificial Characters:** `EXECUTED`, 224 s. 15 synthetic CSVs, 17 checkpoints.
  Multiclass, so no AUC. Final metrics — classifier acc **51.60%**, macro F1
  **50.92**; 5/6/7-way WSD = **0.1519 / 0.1862 / 0.2175**. DP `epsilon=1.0,
  delta=1.58e-5, noise_multiplier=13.57, num_iterations=14`.
- Both are `EXECUTED`, **not** `REPRODUCED`: no official published number was
  compared against yet.
- Records: `results/summaries/experiment_scm_rff.json`,
  `results/summaries/experiment_artificial_characters.json`.
- Performance note: high-degree WSD (5/6/7-way) dominates SCM runtime — it evaluates
  ~92 optimal-transport problems per iteration. `tabicl` inference adds ~30 s/iter.

## Deferred (follow-up)

- SCM `tree` and `nn` prior functions.
- `adult.py` (30 iterations) and `person_activity.py` (5000 samples).
- XOR classifier accuracy (needs `TABPFN_TOKEN`).

## Pending decisions

- ~~Official DPSDA commit SHA.~~ `9078c67995499e6769113780200bbf1d788d3d60`.
- ~~Python version.~~ 3.12.13 (works for the full tabular stack).
- ~~Package source.~~ Pinned Git dependency at the SHA + vendored checkout.
- ~~First smoke-test script.~~ `breast_cancer.py` (tabicl); XOR needs `TABPFN_TOKEN`.
- ~~XOR classifier under the tabpfn license gate.~~ Recorded as `NOT_RUN`; generation
  run via a documented deviation (classifier removed).

## Execution records

| Date | Experiment | Command | Status | Runtime | Key result |
|---|---|---|---|---|---|
| 2026-07-15 | Breast Cancer (smoke) | `python breast_cancer.py` | EXECUTED | 230.5 s | acc 91.86%, F1 91.44, AUC 98.73 |
| 2026-07-15 | XOR (1 feature) | `python xor_stress_test.py --num-features 1` | FAILED | 7.8 s | `TabPFNLicenseError` (needs `TABPFN_TOKEN`) |
| 2026-07-16 | XOR (1 feature) | `xor_no_classifier.py --num-features 1` | EXECUTED | 5.4 s | generation OK; classifier NOT_RUN |
| 2026-07-16 | XOR (2 features) | `xor_no_classifier.py --num-features 2` | EXECUTED | 5.7 s | generation OK; classifier NOT_RUN |
| 2026-07-16 | SCM (rff) | `python scm.py --prior-function rff` | EXECUTED | 739 s | acc 61.08%, F1 61.03, AUC 64.14; WSD 0.146/0.186/0.224 |
| 2026-07-16 | Artificial Characters | `python artificial_characters.py` | EXECUTED | 224 s | acc 51.60%, F1 50.92; WSD 0.152/0.186/0.217 |
