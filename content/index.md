# Tab-PE 公式実装 再現追試

## Abstract

本レポートは、Microsoft の公式実装 [`microsoft/DPSDA`](https://github.com/microsoft/DPSDA)
に含まれる **Tabular Private Evolution (Tab-PE)** の公式デモを、再現可能な環境で
追試した記録である。独自アルゴリズムは実装せず、公式コードをコミット
`9078c67` に固定して利用した。`uv` で環境を固定し、公式デモのうち
Breast Cancer・SCM(rff)・Artificial Characters を実行、XOR は生成のみ実行した。
本フェーズの主眼は「公式デモが再現可能な形で動作すること」であり、
**「実行できた（EXECUTED）」と「論文結果を再現した（REPRODUCED）」を明確に区別する**。

## 1. はじめに

Private Evolution (PE) は、基盤モデルの推論 API のみを用いて差分プライバシー
(DP) 合成データを生成する枠組みである。Tab-PE はその表形式データ版であり、
GPU・モデル学習・モデル推論を必要とせず CPU のみで動作する。

## 2. 目的

1. 公式実装を再現可能な環境で動作させる。
2. 公式 Tab-PE デモを可能な範囲で実行する。
3. 各実験の条件・実行方法・結果を記録する。
4. Tab-PE の処理構造と実験コードの対応を理解する。
5. Markdown を一次成果物として結果を整理し、HTML レポートを生成する。

## 3. Tab-PE概要

Tab-PE は、ランダムな合成データ集団を初期化し、(1) 各合成サンプルと非公開
データの最近傍ヒストグラムを作り、(2) そのヒストグラムに Gaussian ノイズを加えて
DP を保証し、(3) スコアの高いサンプルを選択・変異 (mutation) させて次世代を作る、
という反復進化を行う。詳細と論文↔コード対応は [🧩 Tab-PE](method-tabpe.html) を参照。

## 4. 再現方法

- 公式リポジトリを `9078c67995499e6769113780200bbf1d788d3d60` に固定。
- `private-evolution[tabular]` を当該 SHA の Git 依存として `uv` で導入 (Python 3.12.13)。
- 公式スクリプトは原則無改変で実行。改変が必要な場合は理由と差分を記録
  ([🛠 エンジニアリング](engineering-notes.html))。

## 5. 実験

対象は公式 `example/tabular/` のデモ。実行順・CLI・パラメータは
[🧪 実験](experiments.html)、データセットは [🔬 データ](data-notes.html) を参照。

## 6. 結果

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

反復に伴う精度・距離の推移は [📈 詳細結果](results-detail.html) を参照。

## 7. 考察

- Breast Cancer では synthetic-train→real-test 精度が反復とともに約 52% → **91.86%**
  まで上昇し、PE の進化が有効に機能していることが観察できた。
- SCM は 3 prior で精度が `nn`(**85.48%**) > `tree`(**66.68%**) > `rff`(**61.08%**) と開いた。
  同じ Tab-PE 設定・同じ `epsilon=1.0` でも、元データの生成過程（prior）で下流精度が
  大きく変わる。一方 5/6/7-way の marginal 距離は 3 prior でほぼ同水準だった。
- Artificial Characters は高次 marginal を要する多クラス設定で、精度は約 **52%** で頭打ち。
- Adult は精度 **80.94%** に対し macro F1 は **70.78** と開いた。二値だが不均衡なため、
  accuracy だけでは少数クラスの再現度を測れない。1/2/3-way の marginal 距離は
  0.03/0.05/0.08 と小さく、低次の分布は比較的よく合っている。
- いずれも `epsilon=1.0` の DP 制約下での結果である。

## 8. 再現性評価

本フェーズで比較可能な公式公表値を持つ実験はなく、実行に成功した実験はすべて
`EXECUTED`（再現の可否は未判定）である。`REPRODUCED` と主張できる実験はない。
詳細は [🧪 実験](experiments.html) の判定表を参照。

## 9. 制約

- XOR の分類器精度は `tabpfn` のライセンス取得(要 `TABPFN_TOKEN`)が必要なため
  `NOT_RUN`。生成のみ実行。
- `adult` / `person_activity` / SCM の `tree`・`nn` は本フェーズでは未実行。
- データは第三者リポジトリの `main` から取得しており、データ側の SHA は未固定。

## 10. 結論

公式 Tab-PE 実装を固定コミットで再現実行できる基盤を構築し、少なくとも 3 つの
公式デモを end-to-end で実行、合成データ・チェックポイント・評価指標を保存した。
「実行できた」ことと「論文を再現した」ことは区別して記録している。次フェーズでは
公式公表値との比較、未実行デモ、XOR 分類器の補完を行う。

## References

- Private Evolution 公式実装: <https://github.com/microsoft/DPSDA>
- Tab-PE 論文: *Differentially Private Synthetic Data via APIs 4: Tabular Data*,
  arXiv <https://arxiv.org/abs/2606.08259>
- 参考レポート構成: <https://github.com/gghatano/tpdp2026-binagg>
