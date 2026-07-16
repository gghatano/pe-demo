# 実験

公式 `example/tabular/` デモの実行条件と再現判定を示す。全スクリプトは
DPSDA `9078c67` から無改変で実行（XOR のみ後述の deviation）。

## 公式デモ一覧と共通設定

全デモ共通: `TabularAPI(mutation_rate_init=0.5, mutation_rate_final=0.01,
decay_type="polynomial", gamma=0.2)`、`NearestNeighbors(mode="L2",
lookahead_degree=0, backend="torch")`、composite population
(`[sample]×5 + [rank]×(num_iterations-5)`)、`epsilon=1.0`、`delta=1/n/ln(n)`。

| スクリプト | CLI | num_iterations | num_samples | 分類器 | WSD degrees |
|---|---|---|---|---|---|
| `xor_stress_test.py` | `--num-features {1..7}` | 20 | 1000 | tabpfn | なし |
| `scm.py` | `--prior-function {tree,nn,rff}` | 15 | 1000 | tabicl | 5,6,7 |
| `breast_cancer.py` | なし | 20 | 150 | tabicl | 1,2,3 |
| `adult.py` | なし | 30 | 1000 | tabicl | 1,2,3 |
| `artificial_characters.py` | なし | 15 | 1000 | tabicl | 5,6,7 |
| `person_activity.py` | なし | 15 | 5000 | tabicl | 5,6,7 |

## 実行順序（本フェーズ）

1. Smoke Test: `breast_cancer.py`（tabicl のため無改変で完走可能）。
2. XOR: `--num-features 1`, `2`（生成のみ。分類器は下記理由で `NOT_RUN`）。
3. SCM: `--prior-function rff`。
4. Artificial Characters。

SCM は `rff`・`tree`・`nn` の 3 prior、実データは Breast Cancer・Artificial Characters・
Adult を実行済み。`person_activity` は実行中。

## 再実行可能なコマンド

```bash
uv sync
# Smoke / 実データ / SCM（無改変・公式）
uv run python scripts/run_experiment.py --script breast_cancer.py
uv run python scripts/run_experiment.py --script scm.py --arg --prior-function rff
uv run python scripts/run_experiment.py --script artificial_characters.py
# XOR（分類器を除いた deviation。生成のみ）
uv run python scripts/experiments/xor_no_classifier.py --num-features 1
```

## 再現判定

判定は `REPRODUCED / PARTIALLY_REPRODUCED / EXECUTED / FAILED / NOT_RUN` を用いる。
本フェーズは公式公表値との比較を行っていないため、成功実験はすべて `EXECUTED`。

<!-- AUTO:experiments_table START -->

| 実験 | データ | 判定 | 実行時間(s) | 分類器 | acc | F1 | AUC | WSD | ε | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adult | Adult (real) | EXECUTED | 2864.62 | tabicl | 80.94 | 70.78 | 84.94 | 1-way=0.0292; 2-way=0.0527; 3-way=0.0758 | 1.0 | – |
| artificial_characters | Artificial Characters (real) | EXECUTED | 224.23 | tabicl | 51.6 | 50.92 | – | 5-way=0.1519; 6-way=0.1862; 7-way=0.2175 | 1.0 | – |
| breast_cancer | Breast Cancer (real) | EXECUTED | 230.53 | tabicl | 91.86 | 91.44 | 98.73 | 1-way=0.1644; 2-way=0.2767; 3-way=0.3749 | 1.0 | – |
| scm_nn | SCM (simulated) | EXECUTED | 745.5 | tabicl | 85.48 | 85.46 | 93.8 | 5-way=0.1432; 6-way=0.1817; 7-way=0.2174 | 1.0 | – |
| scm_rff | SCM (simulated) | EXECUTED | 739.31 | tabicl | 61.08 | 61.03 | 64.14 | 5-way=0.1460; 6-way=0.1860; 7-way=0.2243 | 1.0 | – |
| scm_tree | SCM (simulated) | EXECUTED | 742.1 | tabicl | 66.68 | 66.66 | 72.61 | 5-way=0.1424; 6-way=0.1828; 7-way=0.2210 | 1.0 | – |
| xor_stress_test_1_features | XOR stress test (1 feature) | EXECUTED | 5.41 | – | – | – | – | – | 1.0 | classifier: NOT_RUN (tabpfn requires interactive license/TABPFN_TOKEN) \| deviation: TabClassifier(model_name='tabpfn') removed; generation/DP unchanged. |
| xor_stress_test_2_features | XOR stress test (2 feature) | EXECUTED | 5.67 | – | – | – | – | – | 1.0 | classifier: NOT_RUN (tabpfn requires interactive license/TABPFN_TOKEN) \| deviation: TabClassifier(model_name='tabpfn') removed; generation/DP unchanged. |
| xor_stress_test | XOR stress test (simulated) | FAILED | 7.82 | tabpfn | – | – | – | – | 1.0 | tabpfn.errors.TabPFNLicenseError: TabPFN requires a one-time license acceptance to download |

<!-- AUTO:experiments_table END -->

- **XOR (`tabpfn`)**: `FAILED`（`TabPFNLicenseError`。要 `TABPFN_TOKEN`）。
  生成のみの deviation 実行は `EXECUTED`、分類器精度は `NOT_RUN`。
- 数値はすべて `results/summaries/experiments.csv` から生成している。
