# 詳細結果

数値はすべて `results/summaries/`（`experiments.csv` と
`iterations/*.csv`）から生成しており、手入力していない。

## 実験別サマリ

<!-- AUTO:experiments_table START -->

| 実験 | データ | 判定 | 実行時間(s) | 分類器 | acc | F1 | AUC | WSD | ε | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adult | Adult (real) | EXECUTED | 2864.62 | tabicl | 80.94 | 70.78 | 84.94 | 1-way=0.0292; 2-way=0.0527; 3-way=0.0758 | 1.0 | – |
| artificial_characters | Artificial Characters (real) | EXECUTED | 224.23 | tabicl | 51.6 | 50.92 | – | 5-way=0.1519; 6-way=0.1862; 7-way=0.2175 | 1.0 | – |
| breast_cancer | Breast Cancer (real) | EXECUTED | 230.53 | tabicl | 91.86 | 91.44 | 98.73 | 1-way=0.1644; 2-way=0.2767; 3-way=0.3749 | 1.0 | – |
| person_activity | Person Activity (real) | EXECUTED | 4497.71 | tabicl | 64.04 | 36.52 | – | 5-way=0.1175; 6-way=0.1526; 7-way=0.1868 | 1.0 | – |
| scm_nn | SCM (simulated) | EXECUTED | 745.5 | tabicl | 85.48 | 85.46 | 93.8 | 5-way=0.1432; 6-way=0.1817; 7-way=0.2174 | 1.0 | – |
| scm_rff | SCM (simulated) | EXECUTED | 739.31 | tabicl | 61.08 | 61.03 | 64.14 | 5-way=0.1460; 6-way=0.1860; 7-way=0.2243 | 1.0 | – |
| scm_tree | SCM (simulated) | EXECUTED | 742.1 | tabicl | 66.68 | 66.66 | 72.61 | 5-way=0.1424; 6-way=0.1828; 7-way=0.2210 | 1.0 | – |
| xor_stress_test_1_features | XOR stress test (1 feature) | EXECUTED | 5.41 | – | – | – | – | – | 1.0 | classifier: NOT_RUN (tabpfn requires interactive license/TABPFN_TOKEN) \| deviation: TabClassifier(model_name='tabpfn') removed; generation/DP unchanged. |
| xor_stress_test_1_features_tabicl | XOR stress test (1 feature) | EXECUTED | 461.6 | tabicl | 99.8 | 99.8 | 100.0 | – | 1.0 | deviation: classifier tabpfn -> tabicl (tabpfn is license-gated); generation/DP unchanged. |
| xor_stress_test_2_features | XOR stress test (2 feature) | EXECUTED | 5.67 | – | – | – | – | – | 1.0 | classifier: NOT_RUN (tabpfn requires interactive license/TABPFN_TOKEN) \| deviation: TabClassifier(model_name='tabpfn') removed; generation/DP unchanged. |
| xor_stress_test_2_features_tabicl | XOR stress test (2 feature) | EXECUTED | 963.38 | tabicl | 99.01 | 99.01 | 99.96 | – | 1.0 | deviation: classifier tabpfn -> tabicl (tabpfn is license-gated); generation/DP unchanged. |
| xor_stress_test_3_features_tabicl | XOR stress test (3 feature) | EXECUTED | 1001.12 | tabicl | 96.85 | 96.85 | 99.67 | – | 1.0 | deviation: classifier tabpfn -> tabicl (tabpfn is license-gated); generation/DP unchanged. |
| xor_stress_test | XOR stress test (simulated) | FAILED | 7.82 | tabpfn | – | – | – | – | 1.0 | tabpfn.errors.TabPFNLicenseError: TabPFN requires a one-time license acceptance to download |

<!-- AUTO:experiments_table END -->

> 本ページの数値はいずれも各実験 1 run の値である。PE の生成はシードされず非決定的
> なので、run 間の揺れ（mean±std）は本フェーズでは測っていない。数値は「傾向」として
> 読み、単一 run の一致を過大に解釈しない。

## 反復に伴う精度の推移

図 1 に、synthetic-train → real-test の分類器精度の反復推移を示す。Breast Cancer は
約 52% から 91.86% まで改善し、本実験条件では反復が精度を押し上げている。SCM(rff) と
Artificial Characters は高次 marginal を要する設定で、それぞれ約 61%・52% で頭打ちに
なった。

![PE反復に伴う synthetic-train→real-test 精度](results/figures/accuracy_vs_iteration.png)

*図 1: PE 反復ごとの分類器テスト精度（3 デモ、各 1 run）。*

## 反復に伴う marginal 距離の推移

図 2 に k-way Wasserstein marginal 距離の推移を示す。次数が上がるほど距離は大きく、
高次相関ほど一致が難しい。反復を通じては概ね横ばいから微減で推移した。

![PE反復に伴う k-way Wasserstein marginal 距離](results/figures/wsd_vs_iteration.png)

*図 2: PE 反復ごとの k-way Wasserstein marginal 距離（実験別サブプロット、各 1 run）。*

## XOR: 高次相関ストレス（tabicl 代替）

公式 XOR デモは分類器に `tabpfn` を固定するが、これはライセンス取得（`TABPFN_TOKEN`）が
必要で本環境では動かせない。そこで **分類器のみ `tabicl` に差し替えた documented deviation**
（生成・DP・population は公式のまま）で、XOR の分類評価を num-features 1〜3 で実施した。

図 3 に、XOR の特徴数（相関の次数）に対する synthetic-train→real-test スコアを示す。
特徴数が増える（高次の XOR 相関になる）ほど accuracy と macro F1 が下がった
（1→3 で 99.80% → 96.85%）。AUC は 100.0 → 99.67 と高止まりで、順位付けは保てている。
Tab-PE が高次相関を扱えているが、次数が上がると再現がわずかに難しくなる傾向が見える。

![XOR 特徴数に対する分類スコア](results/figures/xor_accuracy_vs_features.png)

*図 3: XOR 特徴数（相関の次数）に対する分類スコア（分類器=tabicl、公式は tabpfn。各 1 run）。*

> これは公式 `tabpfn` からの deviation のため `EXECUTED` 扱いで、公式条件そのものの
> `REPRODUCED` とはしない。生成のみ（分類器なし）の run は [🧪 実験](experiments.html) 参照。

## 最終反復の指標

| 実験 | test acc (%) | macro F1 | AUC | 1/2/3-way WSD | 5/6/7-way WSD |
|---|---|---|---|---|---|
| Breast Cancer | 91.86 | 91.44 | 98.73 | 0.1644 / 0.2767 / 0.3749 | — |
| SCM (nn) | 85.48 | 85.46 | 93.80 | — | 0.1432 / 0.1817 / 0.2174 |
| Adult | 80.94 | 70.78 | 84.94 | 0.0292 / 0.0527 / 0.0758 | — |
| SCM (tree) | 66.68 | 66.66 | 72.61 | — | 0.1424 / 0.1828 / 0.2210 |
| Person Activity | 64.04 | 36.52 | —(多クラス) | — | 0.1175 / 0.1526 / 0.1868 |
| SCM (rff) | 61.08 | 61.03 | 64.14 | — | 0.1460 / 0.1860 / 0.2243 |
| Artificial Characters | 51.60 | 50.92 | —(多クラス) | — | 0.1519 / 0.1862 / 0.2175 |
| XOR (1 feature, tabicl※) | 99.80 | 99.80 | 100.00 | — | —(WSD なし) |
| XOR (2 features, tabicl※) | 99.01 | 99.01 | 99.96 | — | — |
| XOR (3 features, tabicl※) | 96.85 | 96.85 | 99.67 | — | — |

※ XOR は公式 `tabpfn` を `tabicl` に差し替えた deviation。公式 tabpfn は `NOT_RUN`。

SCM は 3 つの prior function（`nn`・`tree`・`rff`）で生成過程が異なる。同じ Tab-PE 設定・
同じ `epsilon=1.0` でも、synthetic-train→real-test 精度は `nn`(85.48%) > `tree`(66.68%)
> `rff`(61.08%) と大きく開いた。marginal 距離は 3 prior でほぼ同水準（差は 0.01 未満）で、
分類器精度ほどの差は出ていない。

## SCM: seed 制御による安定性（#22）

上の「実験別サマリ」の SCM 値は**単一試行**である。prior の効果と乱数変動を分離するため、
`scripts/experiments/run_scm_seeded.py`（公式 `scm.py` と同一設定＋`np.random.seed` による
seed 制御。アルゴリズムは不変）で 3 prior × seed `0,1,2` の **9 試行**を実行した。

同一 seed での再実行は分類精度・F1・AUC・WSD が**完全一致**する（runtime のみ非決定）。
tabular 生成経路の乱数はすべて NumPy グローバル RNG に集約されており、`np.random.seed` で
生成と DP ノイズが決定化されるためである（tabicl 推論・NN histogram は決定的）。

3 試行の平均±標準偏差（`results/summaries/scm_seed_aggregate.csv`）:

| prior | test acc (%) | macro F1 | AUC | 5-way WSD | n |
|---|---|---|---|---|---|
| nn | 86.01 ± 0.16 | 86.01 ± 0.17 | 93.75 ± 0.09 | 0.1428 ± 0.0004 | 3 |
| tree | 67.58 ± 0.16 | 67.57 ± 0.16 | 73.22 ± 0.35 | 0.1438 ± 0.0010 | 3 |
| rff | 61.08 ± 0.90 | 61.02 ± 0.87 | 65.10 ± 1.13 | 0.1462 ± 0.0009 | 3 |

![SCM prior 別の精度 mean±std（seed 3 試行）](results/figures/scm_seed_stability.png)

*図 4: SCM prior 別の分類精度 mean±std（seed 0,1,2）。誤差バーは標準偏差。*

**結論（prior 差の安定性）**: prior 間の精度差（nn−tree ≈ 18 点、tree−rff ≈ 6.5 点）は、
seed による標準偏差（0.16〜0.90 点）よりはるかに大きい。したがって
`nn > tree > rff` の順位は**乱数変動に対して安定**しており、単一試行の順位が偶然でない
ことを確認した。5/6/7-way の marginal 距離は 3 prior でほぼ同水準（std ≤ 0.001）で、
prior を分離しない。下流 utility の差は距離ではなく元データの生成過程に起因する。

## DP 会計（ログ実測値）

| 実験 | epsilon | delta | noise_multiplier | 会計上の num_iterations |
|---|---|---|---|---|
| Breast Cancer | 1.0 | 4.1971e-4 | 12.266 | 19 |
| Adult | 1.0 | 2.8806e-6 | 21.558 | 29 |
| Person Activity | 1.0 | 7.4341e-7 | 16.034 | 14 |
| SCM (rff/tree/nn) | 1.0 | 2.7307e-6 | 15.021 | 14 |
| Artificial Characters | 1.0 | 1.5754e-5 | 13.573 | 14 |
| XOR (1 feature) | 1.0 | 2.7307e-6 | 17.499 | 19 |

> 図はビルド時に `results/figures/*.png` を base64 で埋め込んでいる。図は
> `results/summaries/iterations/*.csv`（追跡対象）から `make_figures.py` で
> 再生成でき、公式ログに存在しない値は推測生成していない。

## Bank Marketing（新規データ適用、#49）

公式デモ外のデータへ [新規データ適用チェックリスト](https://github.com/gghatano/pe-demo/blob/main/docs/guides/new-dataset-checklist.md)（#25）を適用した最初の例。UCI Bank Marketing
（定期預金の申込予測、二値）。`duration`（結果後にしか分からないリーク列）を除外し、層化
80/20 分割。official `TabularEmbedding`・ε=1・30 iter（Adult と同条件）で実行。準備は
`scripts/datasets/bank/preprocess.py`、実行は `scripts/experiments/run_bank.py`。

Bank は **88% が「no」** と Adult(76%) より強く不均衡なため、accuracy はほぼ多数派で頭打ち。
意味のある指標は **macro F1・AUC**（少数クラス＝申込者の再現）。上限は
`scripts/datasets/bank/measure_ceiling.py` で実測（`results/summaries/bank_ceiling.json`）。

| | acc | macro F1 | AUC |
|---|---|---|---|
| 多数派ベースライン | 88.3 | — | — |
| **DP 合成 ε=1（tabicl）** | 88.19 | **58.71** | 72.75 |
| real-1000 → real-test（同サイズ上限） | 88.61 | 58.43 | 77.09 |
| real-full → real-test（xgboost、絶対上限） | 89.55 | 66.68 | 79.42 |

DP 合成の WSD 1/2/3-way = 0.048/0.089/0.128。所見:

- **accuracy は無意味**（88.19 ≈ 多数派 88.3 ≈ 同サイズ上限 88.6）。不均衡データでは予想どおり。
- **macro F1 は DP 合成が同サイズ実データに一致**（58.71 vs 58.43）。少数クラスのハード分類を、
  1000 件の実データと同等に保てている。full-data 上限（66.7）との差はデータ量・モデルの差であり
  DP 由来ではない。
- **AUC のみ ~4 点下**（72.8 vs 77.1）。ハード分類は並ぶが、ランキング品質は DP で落ちる。

Adult（同サイズ上限に accuracy で ~4 点届かない）と対照的に、Bank では metric で結論が変わる
（macro F1 は一致、AUC のみ差）。**不均衡データでは accuracy を見ず、macro F1・AUC で評価すべき**、
という一般的な教訓の裏付けになった。判定は `EXECUTED`（公式公表値との比較ではない）。
