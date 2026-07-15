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

`adult` / `person_activity` / SCM `tree`・`nn` は計算コストの都合で本フェーズ未実行。

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

<!-- INCLUDE:experiments_table -->

- **XOR (`tabpfn`)**: `FAILED`（`TabPFNLicenseError`。要 `TABPFN_TOKEN`）。
  生成のみの deviation 実行は `EXECUTED`、分類器精度は `NOT_RUN`。
- 数値はすべて `results/summaries/experiments.csv` から生成している。
