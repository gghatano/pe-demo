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

## Pending decisions

- ~~Official DPSDA commit SHA.~~ `9078c67995499e6769113780200bbf1d788d3d60`.
- ~~Python version.~~ 3.12.13 (works for the full tabular stack).
- ~~Package source.~~ Pinned Git dependency at the SHA + vendored checkout.
- ~~First smoke-test script.~~ `breast_cancer.py` (tabicl); XOR needs `TABPFN_TOKEN`.

## Execution records

| Date | Experiment | Command | Status | Runtime | Key result |
|---|---|---|---|---|---|
| 2026-07-15 | Breast Cancer (smoke) | `python breast_cancer.py` | EXECUTED | 230.5 s | acc 91.86%, F1 91.44, AUC 98.73 |
| 2026-07-15 | XOR (1 feature) | `python xor_stress_test.py --num-features 1` | FAILED | 7.8 s | `TabPFNLicenseError` (needs `TABPFN_TOKEN`) |
