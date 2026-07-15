# Tab-PE の方法

本ページは公式コード (`microsoft/DPSDA` @ `9078c67`) と論文
([arXiv:2606.08259](https://arxiv.org/abs/2606.08259)) の対応を整理する。
コードから確認できた事実と解釈を区別し、未確認事項は明記する。

## Private Evolution の概要

PE は、基盤モデルの推論 API のみを用いて DP 合成データを生成する。学習は行わず、
「合成データ集団を、非公開データに近づくよう反復的に進化させる」枠組みである。

## Tab-PE の反復構造（コード対応）

反復本体は `pe/runner/pe.py` の `PE.run()`。1 反復は以下から成る。

| 論文上の処理 | 公式コード上の class / function |
|---|---|
| 初期集団生成 (Initialization) | `TabularAPI.random_api` (`pe/api/tabular/tabular_api.py`) |
| 埋め込み | `TabularEmbedding` (`pe/embedding/`) |
| 最近傍ヒストグラム (Scoring) | `NearestNeighbors.compute_histogram` (`pe/histogram/nearest_neighbors.py`) |
| DP ノイズ付与 | `Gaussian.add_noise` (`pe/dp/gaussian.py`) |
| 選択 (Selection) | `PEPopulation.next` / `CompositePopulation` (`pe/population/`) |
| 変異 (Variation / Mutation) | `TabularAPI.variation_api` (`pe/api/tabular/tabular_api.py`) |
| チェックポイント保存 | `SaveCheckpoints` (`pe/callback/`) |

### Initialization

`TabularAPI.random_api` は列ごとにランダム生成する。categorical は
`np.random.choice(categories)`、integer は `np.random.randint(min, max+1)`、
float は `np.random.uniform(min, max)`（`tabular_api.py:48-84`）。

### Scoring（最近傍ヒストグラム）

`NearestNeighbors`（`mode="L2"`, `lookahead_degree=0`, `backend="torch"`）で、
各合成サンプルに対して最近傍の非公開サンプル数を数え上げてヒストグラムを作る。
これが DP 保護対象の統計量である。

### DP（差分プライバシー）

`Gaussian.add_noise` がヒストグラムに `np.random.normal(scale=noise_multiplier)`
を加える（`gaussian.py:165-178`）。`noise_multiplier` は `(epsilon, delta, num_steps)`
から `get_noise_multiplier` で解析的に決定される（`gaussian.py:45-108`）。合成は
`mu = sqrt(num_steps) / noise_multiplier` の √合成（Gaussian-DP 系）で、per-step の
ε 分割ではない。会計に渡る `num_steps` は `len(num_samples_schedule) - 1`
（`pe.py:157-162`）で、公式デモでは設定 `num_iterations` から 1 引いた値になる
（例: XOR 20→19、SCM 15→14）。全デモ共通で `epsilon=1.0`、
`delta = 1/n/ln(n)`（`n` は非公開データ行数）。

### Selection

`PEPopulation` は `selection_mode="sample"`（前半 5 反復）と `"rank"`（残り）を
`CompositePopulation` で組み合わせる（各デモの `__main__`）。`keep_selected` と
`initial/next_variation_api_fold` の意味づけの論文対応は **UNCONFIRMED**。

### Variation / Mutation

`TabularAPI.variation_api` が、反復ごとに減衰する mutation rate
（`mutation_rate_init=0.5` → `mutation_rate_final=0.01`, `decay_type="polynomial"`,
`gamma=0.2`）で各列を摂動する（`tabular_api.py:86-158`）。categorical は確率的に
再サンプリング、数値列は `±mutation_rate × range` の一様摂動＋クリップ。

### Crossover

`CompositePopulation` による複数集団の合成が論文の crossover に相当するかは
**UNCONFIRMED**（コードの `fold` 概念と論文の対応要確認）。

## 評価指標（コード対応）

- **Utility**: `TabClassifier`（`pe/callback/tabular/classifier.py`）。合成データで
  学習し実テストで評価する synthetic-train→real-test。accuracy・macro F1、二値は AUC。
- **Statistical similarity**: `ComputeWSD`（`pe/callback/tabular/compute_wsd.py`）。
  k-way marginal の Wasserstein 距離。degree=1 は 1 次元 Wasserstein、degree≥2 は
  最適輸送 (`ot.emd2`)。全列を非公開データのレンジで [0,1] 正規化し、全 k 列組合せの
  平均を取る。サンプリングは `seed=42`（ただし PE 生成自体はシードされない）。

## 従来 PE との差分

画像・テキスト PE が基盤モデルの生成 API を variation に使うのに対し、Tab-PE は
列単位のランダム摂動 (`variation_api`) を variation とし、モデル推論を要しない。
この差分の詳細な位置づけは論文本文の確認が必要（一部 **UNCONFIRMED**）。
