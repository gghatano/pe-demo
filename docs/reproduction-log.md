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

## 2026-07-16: Aggregation + Markdown/HTML report (#6)

- `scripts/collect_results.py` → `results/summaries/experiments.{csv,json}` (6 rows)
  and `results/summaries/iterations/*.csv` (per-iteration series parsed from the
  official `log.txt`, because `CSVPrint`'s per-metric files are empty on Windows —
  metric names embed a `:` that is illegal in Windows filenames).
- `scripts/make_figures.py` → `results/figures/{accuracy,wsd}_vs_iteration.png`
  (regenerated from the tracked iteration CSVs; not committed).
- Authored `content/*.md` (7 pages) as the report source of truth. Result numbers are
  injected from `experiments.csv` and figures embedded as base64 via include markers,
  so no numbers are hand-typed into the report body.
- `scripts/build_html.py` → `htmls/*.html` (single `PAGES` config, top tabs with
  active state, auto TOC from h2/h3, responsive 2→1 column, MathJax, base64 figures).
  HTML is generated from Markdown only and is gitignored (regenerated on build).
- Report pipeline (clean checkout): `uv sync` → run experiments (or reuse tracked
  summaries) → `collect_results.py` → `make_figures.py` → `build_html.py`.

## 2026-07-16: Report kit integration + GitHub Pages (feature-007)

- Adopted the report builder from
  [gghatano/synth-report-kit](https://github.com/gghatano/synth-report-kit) (MIT):
  vendored `ark/` (`build_html.py`, `context.py`) and drive it from
  `scripts/build_site.py` (single `PAGES` config). Replaces the earlier
  `scripts/build_html.py` (removed). The builder adds a hero header + tab bar,
  TOC sidebar, base64 image embedding, mermaid, MathJax, and citation/badge styling.
- `content/*.md` figures now use standard Markdown image links (base64-embedded by
  the builder). The experiments table is injected by `collect_results.py` between
  `<!-- AUTO:experiments_table -->` markers, so report numbers stay CSV-sourced.
- Applied report-quality skills brought from the kit
  (`.claude/skills/{stop-ai-slop-jp,report-review,report-skeleton,publish-check,
  repro-engineering-review}` + `.claude/docs/documentation-conventions.md`):
  added numbered figure captions, a single-run (non-deterministic) caveat, and
  "本実験条件では" scoping in the discussion.
- `.github/workflows/deploy-pages.yml`: on push to `main`, builds HTML from Markdown
  with light deps only (`uv run --no-project --with ...`, no torch/tabpfn) and
  deploys `htmls/` to GitHub Pages. **Requires** Settings → Pages → Source =
  "GitHub Actions".
- Report pipeline (clean checkout): `collect_results.py` → `make_figures.py`
  → `build_site.py`. The Actions workflow runs these three and deploys.

## 2026-07-16: SCM tree/nn priors (#14)

- Ran the unmodified official `scm.py --prior-function tree` and `nn`
  (`scripts/run_experiment.py`). Both `EXECUTED` (~742 s / ~745 s).
- Final metrics — SCM(tree): acc **66.68%**, F1 66.66, AUC 72.61; 5/6/7-way WSD
  0.1424/0.1828/0.2210. SCM(nn): acc **85.48%**, F1 85.46, AUC 93.80; WSD
  0.1432/0.1817/0.2174. DP `epsilon=1.0, delta=2.73e-6, noise_multiplier=15.02`.
- Observation: across SCM priors, downstream accuracy differs a lot
  (nn 85% > tree 67% > rff 61%) while 5/6/7-way marginal distance stays within
  ~0.01. All `EXECUTED`, not `REPRODUCED` (no official comparison number).
- SCM prior set (rff/tree/nn) is now complete.

## 2026-07-16: Adult (#15)

- Ran the unmodified official `adult.py`. `EXECUTED`, 2865 s (~48 min; 30 iterations
  over 1000 samples with tabicl each iteration).
- Final metrics — acc **80.94%**, macro F1 **70.78**, AUC **84.94**; 1/2/3-way WSD
  0.0292/0.0527/0.0758. DP `epsilon=1.0, delta=2.88e-6, noise_multiplier=21.56,
  accounted num_iterations=29`. 30 synthetic CSVs, 32 checkpoints.
- Observation: acc (80.94%) and macro F1 (70.78) diverge — Adult is an imbalanced
  binary task, so accuracy alone overstates minority-class fidelity. Low-degree
  (1/2/3-way) marginal distances are small (≤0.08), i.e. low-order distributions
  match reasonably well. `EXECUTED`, not `REPRODUCED`.

## 2026-07-16: Person Activity (#16)

- Ran the unmodified official `person_activity.py` (heaviest: 5000 samples/iteration).
  `EXECUTED`, 4498 s (~75 min).
- Final metrics — acc **64.04%**, macro F1 **36.52** (multiclass, no AUC); 5/6/7-way
  WSD 0.1175/0.1526/0.1868. DP `epsilon=1.0, delta=7.43e-7, noise_multiplier=16.03,
  accounted num_iterations=14`. 15 synthetic CSVs, 17 checkpoints.
- Observation: acc (64.04%) far exceeds macro F1 (36.52). Many imbalanced classes —
  majority classes are predicted but minority classes reproduce poorly. `EXECUTED`,
  not `REPRODUCED`.
- With this, all official tabular demos in scope have been run: XOR (generation),
  SCM (rff/tree/nn), and the four real datasets (Breast Cancer, Adult, Artificial
  Characters, Person Activity).

## 2026-07-16: XOR classification with tabicl deviation (#21)

Decision (from the user): complete the XOR classification by substituting the
license-gated `tabpfn` with `tabicl` (a documented deviation).

- `scripts/experiments/xor_with_classifier.py` — the official `xor_stress_test.py`
  pipeline with the sole change `TabClassifier(model_name="tabpfn" → "tabicl")`.
  Generation, populations, NN histogram, and `epsilon=1.0` Gaussian mechanism
  unchanged.
- Ran num-features 1/2/3 (`EXECUTED`; 462 s / 963 s / 1001 s).
  acc/F1/AUC: 1f = **99.80% / 99.80 / 100.0**; 2f = **99.01% / 99.01 / 99.96**;
  3f = **96.85% / 96.85 / 99.67**.
- Observation: as XOR order (num-features) rises, synthetic-train→real-test accuracy
  and macro F1 fall (99.80% → 96.85%) while AUC stays ≥99.67 — Tab-PE handles the
  high-order XOR correlation, but higher order is progressively harder to reproduce.
- Status `EXECUTED` (classifier differs from the official tabpfn), not `REPRODUCED`.
- Figure: `results/figures/xor_accuracy_vs_features.png` (score vs num-features).
- Records: `results/summaries/xor_clf_{1,2,3}f_tabicl.json`.

## 2026-07-16: AdultEmbedding implementation (#24, implementation-first)

Decision (from the user): implement #24's code first; defer the full 3-variant ×
3-seed experiment until #22 (seed control) lands.

- `pe_demo/embedding/adult.py` — `AdultEmbedding(Embedding)` + `AdultEmbeddingConfig`
  with 3 variants (`official` / `robust_numeric` / `adult_semantic`). Non-official
  numeric transforms use fixed **public** Adult domain bounds (never learned from the
  private data); unknown categories raise instead of silently mapping to index 0; the
  embedding is row-independent (no added 1-record sensitivity). Design + public
  constants (bounds, education→num table with source) in `docs/research/adult-embedding.md`.
- `scripts/experiments/run_adult_embedding.py` — Adult PE with a swappable embedding,
  seed control, and `--num-iterations` (default 30 = official; small for smoke). Records
  full config/seed/provenance + additional evals (education inconsistency rate, capital
  presence ratio diff). Writes `adult_embedding_*` (additional experiment, not a
  replacement for the official `adult` result).
- `tests/test_adult_embedding.py` — 20 tests (determinism, label excluded, no NaN/Inf,
  capital zero → 0, log monotonic, education penalty, unknown-category raises, official
  == TabularEmbedding, dim consistency, row-independence). `uv run pytest` → 20 passed.
- Wiring verified by a single-seed 2-iteration smoke (`robust_numeric`, dim=110,
  end-to-end OK). The 2-iteration smoke numbers are not results and were not kept.

**Deferred to #22 / rest of #24**: full runs (3 variants × ≥3 seeds × 30 iterations),
`content/adult-embedding.md`, and the utility/fidelity/consistency figures.

## 2026-07-16: Seed control + SCM stability (#22)

- Randomness audit: the entire tabular generation path uses NumPy's global RNG —
  `TabularAPI` (`np.random.choice/randint/uniform/rand`), `pe.dp.gaussian.add_noise`
  (`np.random.normal`), `PEPopulation` sample selection (`np.random.choice`). The NN
  histogram (torch, `lookahead_degree=0`) is a deterministic argmin and `tabicl`
  inference is deterministic; `ComputeWSD` uses its own fixed `random_state=42`. So
  `np.random.seed` fully determinizes generation + DP noise (no torch RNG seeding needed).
- `scripts/experiments/run_scm_seeded.py` — official `scm.py` + `np.random/random/torch`
  seeding; algorithm unchanged. `--prior-function --seed --num-iterations` CLI; seed saved
  in each summary.
- Same-seed reproducibility verified: two runs at seed 0 gave **bit-identical**
  acc/F1/AUC/WSD; only runtime (wall-clock) varies.
- Ran SCM `rff`/`tree`/`nn` × seeds `0,1,2` (9 full runs). Aggregated with
  `scripts/aggregate_seeds.py` → `results/summaries/scm_seed_aggregate.{csv,json}` and
  `results/figures/scm_seed_stability.png`.
  - acc mean±std: **nn 86.01 ± 0.16**, **tree 67.58 ± 0.16**, **rff 61.08 ± 0.90**.
  - 5/6/7-way WSD std ≤ 0.001 (prior-insensitive).
- **Conclusion**: the prior gaps (nn−tree ≈ 18, tree−rff ≈ 6.5) dwarf the seed std
  (0.16–0.90), so `nn > tree > rff` is stable against random variation — the single-run
  ordering was not a fluke. Report distinguishes single-trial (§実験別サマリ) from the
  3-seed mean±std section. Pages workflow now runs `aggregate_seeds.py`.

## 2026-07-17: Adult embedding experiment (#24, full)

- Ran the Adult-embedding comparison (`run_adult_embedding.py`, seed control from #22):
  `official` / `robust_numeric` / `adult_semantic` × seeds `0,1,2` = 9 runs (~48 min each).
  Aggregated with `aggregate_seeds.py` → `adult_embedding_seed_aggregate.{csv,json}` +
  accuracy and fidelity figures.
- `official` reproduced the earlier single-run Adult (acc 79.89 ± 0.58 vs 80.94) —
  confirms `AdultEmbedding(official)` == `TabularEmbedding` on real data.
- Utility (mean±std): official acc **79.89 ± 0.58**, robust **81.01 ± 1.30**,
  semantic **77.78 ± 1.84** (semantic F1 62.58 ± 9.33 — collapses at seed 1).
- Fidelity (lower better): capital-gain ratio diff official **0.760** → robust **0.498**
  / semantic **0.519**; capital-loss **0.805** → **0.521 / 0.535**; education inconsistency
  official 0.549, robust **0.711** (worse), semantic 0.502.
- **Hypotheses**: H1 (capital split → fidelity) **supported** (0.76→0.50, gap ≫ std);
  H2 (education penalty → consistency) **未判定/weak** (0.549→0.502, within std, and semantic
  hurts utility); H3 (lower fnlwgt → utility) **未判定** (+1.1 pt within std).
- **Takeaway**: a more thoughtful embedding clearly improves the targeted distributional
  fidelity (capital) but does **not** reliably improve downstream classifier utility;
  the aggressive semantic variant even hurts utility and is seed-sensitive. Reported as a
  utility/fidelity/consistency trade-off, not a single-metric win. New report page
  `content/adult-embedding.md`.
- Minor deferral: the fnlwgt-excluded classifier (an extra lens on H3) was not implemented;
  the required completion metrics (acc/F1/AUC/WSD/inconsistency) are covered.

## 2026-07-17: public_fe embedding (#36)

- Measured the Adult downstream ceiling on the same test set: majority baseline
  75.77%; real-1000→real-test (tabicl) **acc 84.01 / macroF1 77.77 / AUC 90.42**;
  real-FULL→real-test (xgboost) **acc 86.44 / macroF1 80.48 / AUC 92.65**. Our DP
  synthetic (~80 / ~70) is ~4 acc and ~7 macroF1 points below the same-size ceiling.
- Added `public_fe` variant: generic **public** feature engineering (drop fnlwgt;
  age/hours ordinal-binned with fixed public edges; capital → extra_income
  {none/positive/negative} + public log-magnitude; native-country → US/non-US;
  education-num ordinal, education one-hot dropped). No private target/statistics —
  documented leak boundary. Ran 3 seeds.
- Result (counterintuitive): `public_fe` **underperforms** official on utility
  (acc 78.61 ± 0.81, macroF1 63.28 ± 7.72) and wrecks education consistency
  (0.549 → **0.939**), though it fixes capital fidelity (0.52 like robust).
- **Lesson**: feature engineering that helps a *classifier* (binning, grouping,
  dropping columns) is counterproductive for the Tab-PE *embedding/distance* — it
  removes signal the nearest-neighbor selection needs. Dropping a column from the
  embedding also breaks that column's joint consistency (education 0.94). Of the 4
  variants, `robust_numeric` (fix capital scale only, drop nothing) was best.
- Upper-bound rows added to `content/adult-embedding.md`; conclusion is a
  utility/fidelity/consistency trade-off, no strong claim.

## 2026-07-17: Adult epsilon sweep (#38)

- `scripts/experiments/run_adult_epsilon.py` (official `TabularEmbedding`, seeded,
  `--epsilon`; `inf` = noise_multiplier 0 = PE upper bound). Ran ε ∈ {0.5,1,2,4,8,∞}
  × seed 0 (6 runs, ~48 min each).
- Utility vs ε (single seed): acc 79.98/80.67/81.27/81.84/82.61/82.47;
  macroF1 68.68/71.43/73.04/73.43/73.04/72.79; AUC 82.05/84.53/86.29/87.26/88.02/87.46.
- **ε is a real lever** (unlike the embedding): ε 0.5→8 lifts acc ~2.6, AUC ~6, macroF1
  ~4.8. Minority discrimination (AUC/F1) benefits most. Diminishing returns; plateaus at
  ε≈8/∞ (acc ~82.5%).
- **Gap decomposition**: the ~3.3-pt gap at ε=1 (real-1000 84.01 vs 80.67) splits into
  ~1.8 pt DP-noise (closable by raising ε) + ~1.5 pt PE-generation residual (ε=∞ PE reaches
  only 82.47, still below the same-size real ceiling 84.01). Neither ε nor the embedding
  closes the generation residual.
- Figure `results/figures/adult_epsilon_sweep.png`; report section added to
  `content/adult-embedding.md`. Single-seed caveat noted (ε=8 vs ∞ non-monotonicity is
  seed noise). Does not overwrite the official `adult` (ε=1) result.

## 2026-07-18: robust_numeric epsilon sweep — noise did NOT hide the embedding (#40)

- Ran `robust_numeric` at ε ∈ {0.5,1,2,4,8,∞} × seed 0 (via `run_adult_epsilon.py`,
  now `--variant`-aware) to test whether DP noise had masked an embedding benefit.
- Result is the opposite of that hypothesis. official vs robust acc: 0.5 → 79.98/81.49
  (+1.5), 1.0 → 80.67/81.59 (+0.9), 2.0 → 81.27/78.36 (−2.9), 4.0 → 81.84/78.21 (−3.6),
  8.0 → 82.61/79.34 (−3.3), ∞ → **82.47/77.63 (−4.84)**. robust's curve is non-monotonic
  with volatile macro F1 (single-seed caveat), but the ε=∞ gap is clear.
- **Conclusion**: DP noise did not hide an embedding advantage. At ε=∞ (no noise)
  official clearly beats robust; robust's slight ε=1 edge (#24) was a low-ε artifact
  (noise masking the embedding's coarser geometry). Higher ε → sharper NN selection →
  robust's engineered distance selects worse. Reinforces "embedding is not a utility lever".
- Review fix folded in: `parse_final_metrics` now stores `dp.epsilon = "inf"` (string)
  instead of `float('inf')` (which json.dumps serialized as the invalid token `Infinity`);
  sanitized the two tracked `adult_eps*inf*` records — all summary JSONs are now strict-valid.
- Figure `adult_epsilon_sweep.png` now overlays official vs robust accuracy; report/caption
  updated. Does not overwrite the official `adult` result.

## Deferred (follow-up)

- fnlwgt-excluded classifier as an extra H3 check (optional; #24 core done) — #33.
- Multi-seed epsilon sweep (single seed done) — extends #38/#40 if the trend warrants.
- Review-derived backlog: pipeline tests #45, ceiling provenance #42, seed-control
  consistency #43, POSIX provenance paths #44.
- XOR with the official `tabpfn` classifier (needs `TABPFN_TOKEN`) — #21 done via
  a tabicl deviation; the verbatim-official run remains open.
- Trace results to source logs / audit — #19.
- Comparison against official published numbers → `REPRODUCED` — #20.
- Seed control + multiple trials for stability (mean±std) — #22.

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
| 2026-07-16 | SCM (tree) | `python scm.py --prior-function tree` | EXECUTED | 742 s | acc 66.68%, F1 66.66, AUC 72.61; WSD 0.142/0.183/0.221 |
| 2026-07-16 | SCM (nn) | `python scm.py --prior-function nn` | EXECUTED | 745 s | acc 85.48%, F1 85.46, AUC 93.80; WSD 0.143/0.182/0.217 |
| 2026-07-16 | Adult | `python adult.py` | EXECUTED | 2865 s | acc 80.94%, F1 70.78, AUC 84.94; WSD 0.029/0.053/0.076 |
| 2026-07-16 | Person Activity | `python person_activity.py` | EXECUTED | 4498 s | acc 64.04%, F1 36.52; WSD 0.118/0.153/0.187 |
| 2026-07-16 | XOR 1f (tabicl※) | `xor_with_classifier.py --num-features 1` | EXECUTED | 462 s | acc 99.80%, F1 99.80, AUC 100.0 |
| 2026-07-16 | XOR 2f (tabicl※) | `xor_with_classifier.py --num-features 2` | EXECUTED | 963 s | acc 99.01%, F1 99.01, AUC 99.96 |
| 2026-07-16 | XOR 3f (tabicl※) | `xor_with_classifier.py --num-features 3` | EXECUTED | 1001 s | acc 96.85%, F1 96.85, AUC 99.67 |

※ XOR は公式 tabpfn を tabicl に差し替えた deviation。
