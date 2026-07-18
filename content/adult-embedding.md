# 追加分析：下流 utility のレバー（詳細）

このページは要約レポート（[📄 レポート](index.html) §3）の詳細な裏付けである。Adult を軸に、
(1) 埋め込みの精緻化、(2) 下流の実測上限、(3) ε スイープ、(4) 「なぜ埋め込みが効かないか」の
診断、を順に示す。結論は「utility のレバーは埋め込みではなく ε、ただし ε も頭打ち」で、
その根拠がここにある。

## 埋め込みの精緻化

公式 Adult デモは既定の `TabularEmbedding`（数値は metadata の min-max、カテゴリは
one-hot、距離は L2）を使う。Adult 固有の性質——`capital-gain/loss` のゼロ集中、
`fnlwgt` が標本重みであること、`education` と `education-num` の重複——を距離へ反映すると
下流 utility や統計的 fidelity が改善するかを追加実験した。

> これは**公式再現条件の変更**である。公式 `adult`（`EXECUTED`）結果は置換せず、
> `adult_embedding_*` として独立に記録した。判定はすべて `EXECUTED`。設計と公開定数
> （domain bounds、`education→education-num` 対応表）は
> [`docs/research/adult-embedding.md`](https://github.com/gghatano/pe-demo/blob/main/docs/research/adult-embedding.md) 参照。

## variant

- `official`: 公式 `TabularEmbedding` と数値一致（ベースライン）。
- `robust_numeric`: `fnlwgt` を log 化（重み 0.25）、`capital-gain/loss` を「ゼロか否か」＋
  「正値の log 量」に分解。数値変換の値域は**公開 domain bounds を固定使用**（秘密データから
  学習しない）。カテゴリ・`age`・`education-num`・`hours-per-week` は公式と同じ。
- `adult_semantic`: `robust_numeric` に加え、`education` の one-hot をやめ `education-num` を
  主表現とし、`education`/`education-num` の不整合に penalty 次元を追加。
- `public_fe`（#36）: Adult の一般的な公開 FE に基づく。`fnlwgt` 除去、`age`/`hours` を
  **固定公開エッジ**でビン化、`capital` を `extra_income` 3 値＋log 量に、`native-country` を
  US/非US に集約、`education-num` を順序保持（`education` one-hot は落とす）。**正解 `income` も
  私的統計も使わない**ので、リークにならない（境界は設計文書参照）。

生成・DP・population・分類器（`tabicl`）・WSD の定義は公式 `adult` と同一。変えたのは
埋め込みだけ。各 variant を seed `0,1,2` の **3 試行**（#22 の seed 制御）で実行した。

## Utility（下流分類）

平均±標準偏差（`results/summaries/adult_embedding_seed_aggregate.csv`）:

| variant | test acc (%) | macro F1 | AUC |
|---|---|---|---|
| official | 79.89 ± 0.58 | 70.58 ± 1.18 | 83.33 ± 0.86 |
| robust_numeric | 81.01 ± 1.30 | 71.19 ± 0.54 | 84.61 ± 1.34 |
| adult_semantic | 77.78 ± 1.84 | 62.58 ± 9.33 | 80.90 ± 2.84 |
| public_fe | 78.61 ± 0.81 | 63.28 ± 7.72 | 80.20 ± 4.28 |
| （参考）実データ1000→実test | 84.01 | 77.77 | 90.42 |
| （参考）実データ全量→実test（xgboost） | 86.44 | 80.48 | 92.65 |

![variant 別の精度 mean±std（seed 3 試行）](results/figures/adult_embedding_seed_stability.png)

*図 5: Adult 埋め込み variant 別の分類精度 mean±std（seed 0,1,2）。*

参考として、同じテストセットでの上限を実測した（`scripts/datasets/adult/measure_ceiling.py`、
`results/summaries/adult_ceiling.json` に provenance を保存、#42）。同サイズ実データ
（実1000→実test、tabicl）は acc **84.01%** / macro F1 77.77、全量 xgboost は acc **86.44%** /
macro F1 80.48。多数派ベースラインは 75.77%。→ 我々の DP 合成（acc ~80%、macro F1 ~70）は
上限まで **accuracy で ~4 点、macro F1 で ~7 点**の余地があるが、埋め込みの選択でその差は
ほとんど動かない。

`official`(79.89%) と `robust_numeric`(81.01%) の差は約 1.1 点で標準偏差（0.58〜1.30）と同程度で
**有意ではない**。`adult_semantic`(77.78%) と `public_fe`(78.61%) はむしろ official を下回った。
気を利かせた埋め込みでも下流 utility は**改善せず、やり方によっては悪化する**。

## Fidelity・意味的一貫性

最終合成 CSV に対する追加評価（低いほど良い。公式 TabICL 評価とは分離）:

| variant | capital-gain>0 比率差 | capital-loss>0 比率差 | education 不整合率 |
|---|---|---|---|
| official | 0.760 ± 0.012 | 0.805 ± 0.012 | 0.549 ± 0.044 |
| robust_numeric | 0.498 ± 0.008 | 0.521 ± 0.016 | 0.711 ± 0.024 |
| adult_semantic | 0.519 ± 0.012 | 0.535 ± 0.016 | 0.502 ± 0.072 |
| public_fe | 0.516 ± 0.013 | 0.531 ± 0.019 | 0.939 ± 0.014 |

![variant 別の fidelity/一貫性 mean±std](results/figures/adult_embedding_seed_fidelity.png)

*図 6: capital 比率差と education 不整合率（低いほど良い）。誤差バーは標準偏差。*

公式埋め込みは capital のゼロ集中を全く再現できていない（capital-gain>0 が実データ 9% に対し
合成 83%、比率差 0.76）。`robust_numeric`/`adult_semantic`/`public_fe` はこれを **0.50 前後**まで
下げた（差 ≫ std、**明確な改善**）。一方 education 不整合は、`robust_numeric` で 0.71、`public_fe`
では **0.94** まで悪化した。`public_fe` は埋め込みから `education` 列を落とし `education-num` だけを
残したため、生成時に両者を揃える力が働かず、education と education-num がほぼ無関係になった。
列を埋め込みから外すと、その列の同時整合は保証されなくなる。

## 仮説の判定

- **H1（capital をゼロ判定＋log 量に分解すると fidelity 改善）: 支持。**
  capital-gain/loss の比率差が 0.76/0.80 → 0.50/0.52 と、標準偏差を大きく超えて改善した。
- **H2（education 整合 penalty で意味的一貫性向上）: 未判定（弱い）。**
  `adult_semantic` の education 不整合は 0.549→0.502 と下がったが、改善幅は標準偏差（0.04〜0.07）
  の範囲内で有意とは言えない。しかも `adult_semantic` は utility を犠牲にし不安定。
- **H3（fnlwgt の寄与を下げると下流 utility 改善）: 未判定。**
  `robust_numeric` の精度は +1.1 点だが標準偏差内で、有意な改善ではない。

## 公開 FE（`public_fe`）: 分類器に良い FE は埋め込みには逆効果

一般的な公開特徴量エンジニアリング（fnlwgt 除去、age/hours の固定エッジ・ビン化、capital の
符号 3 値化、education-num 順序化、native-country を US/非US に集約。正解を覗かない・リークしない）
に基づく `public_fe` を試した。狙いは「分類器に効く良い特徴量なら fidelity/utility が上がるはず」。

結果は逆だった。`public_fe` は utility が official を下回り（acc 78.61、macro F1 63.28）、
education 不整合は **0.94** まで悪化した。capital 忠実度だけは改善した（0.52）。

理由は、**分類器向けの「良い FE」（ビン化・グループ化・列の削除）が、Tab-PE の距離にとっては
情報の削減**だからである。Tab-PE は埋め込み上の最近傍で「非公開データに近い合成サンプル」を
選ぶ。ビンで解像度を落とし、native-country を 2 値に潰し、fnlwgt や生の capital 額や education
列を落とすと、最近傍が使える手掛かりが減り、選択の質——ひいては下流 utility——が下がる。
過学習を防ぐための粗い特徴量は、生成の距離としてはむしろ有害だった。

## ε を振ると（DP 予算がレバー、ただし頭打ち）（#38）

埋め込みがレバーでないなら、残るギャップの主因は DP ノイズ（ε）か生成機構のはず。これを直接
確かめるため、公式 `TabularEmbedding` を固定して ε ∈ {0.5, 1, 2, 4, 8, ∞} を振った（単一 seed、
∞ は noise_multiplier=0＝ノイズなしの PE 上限）。

| ε | acc (%) | macro F1 | AUC | noise_multiplier |
|---|---|---|---|---|
| 0.5 | 79.98 | 68.68 | 82.05 | 40.9 |
| 1.0 | 80.67 | 71.43 | 84.53 | 21.6 |
| 2.0 | 81.27 | 73.04 | 86.29 | 11.4 |
| 4.0 | 81.84 | 73.43 | 87.26 | 6.2 |
| 8.0 | 82.61 | 73.04 | 88.02 | 3.4 |
| ∞ | 82.47 | 72.79 | 87.46 | 0.0 |

![Adult utility vs ε（official と robust_numeric）](results/figures/adult_epsilon_sweep.png)

*図 7: Adult の分類精度を ε で振った曲線（単一 seed）。青が official、橙が robust_numeric 埋め込み。
破線は同サイズ実データの acc 上限 84.01%、点線は多数派ベースライン 75.77%。*

観察（official 埋め込み）:

- **ε は埋め込みと違って実際のレバー**。ε 0.5→8 で acc は 79.98→82.6、AUC は 82.0→88.0、
  macro F1 は 68.7→73.4 と上がる。少数クラスの識別（AUC・F1）ほど ε の恩恵が大きい。
- **収穫逓減し、ε≈8/∞ で頭打ち**（acc ~82.5%）。ノイズを完全に切っても（∞）それ以上は伸びない。
  ε=8 と ∞ の差は単一 seed の揺れの範囲。
- **ε=∞（ノイズなし）でも実データ上限に届かない**。PE 上限 82.47% は同サイズ実データ 84.01% より
  ~1.5 点低い。つまり ε=1 での ~3.3 点差は、**DP ノイズ分（ε で埋まる）~1.8 点**＋**PE 生成機構分
  （ε でも埋まらない）~1.5 点**に分解できる。

結論: ε は DP ノイズ分のギャップを（収穫逓減しつつ）埋めるレバーだが、生成機構由来の残差は ε でも
埋め込みでも消えない。ギャップを本気で詰めるなら、埋め込みより ε（プライバシーとの引き換え）か、
生成機構・反復数・サンプル数・少数クラス対応の方が筋がよい。

### robust_numeric 埋め込みで ε を振る（#40）：ノイズは埋め込み効果を隠していなかった

#24 の「埋め込みは効かない」は ε=1（ノイズ大）での結論だった。**DP ノイズが埋め込みの差を覆い
隠していた可能性**を確かめるため、最良 variant `robust_numeric` でも ε を振って official と比べた。

| ε | official acc | robust acc | Δ(robust−official) |
|---|---|---|---|
| 0.5 | 79.98 | 81.49 | +1.51 |
| 1.0 | 80.67 | 81.59 | +0.92 |
| 2.0 | 81.27 | 78.36 | −2.91 |
| 4.0 | 81.84 | 78.21 | −3.63 |
| 8.0 | 82.61 | 79.34 | −3.27 |
| ∞ | 82.47 | 77.63 | **−4.84** |

結果は仮説の**逆**だった（図 7 の橙）。低 ε（0.5,1）では robust がわずかに上回るが、ε≥2 では
official が明確に上回り、**ノイズを切った ε=∞ では official 82.47% に対し robust 77.63%（−4.84）**。
robust の曲線は非単調で macro F1 も大きく振れる（単一 seed の不安定さを含むため形状は過信しない）。

つまり **DP ノイズが埋め込みの利点を覆い隠していたのではない。むしろ逆で、ノイズが無いほど
official（デフォルト）が優勢**。ε=1 で robust がわずかに良く見えたのは低 ε の産物で、ノイズが
埋め込みの粗さを覆っていたと解釈できる。高 ε ほど最近傍選択が鋭くなり、robust の作り込んだ距離
幾何がむしろ選択を悪くしていると考えられる。→ 埋め込みは utility のレバーでない、が一層強まった。

**診断（なぜ robust が悪いのか）**: 「capital のバイナリ presence 次元が幾何を支配している」という
仮説を、capital の重みを段階的に落として ε=∞ で切り分けた（`--capital-presence-weight` /
`--capital-amount-weight`）。

| ε=∞ の埋め込み | acc | macro F1 | AUC | WSD 1/2/3 |
|---|---|---|---|---|
| official | 82.47 | 72.79 | 87.46 | 0.025/0.045/0.065 |
| robust（全部） | 77.63 | 63.30 | 79.13 | 0.037/0.072/0.107 |
| robust（presence=0） | 80.94 | 72.15 | 82.42 | 0.031/0.060/0.089 |
| robust（capital=0：presence＋amount 0） | 80.98 | 73.32 | 84.12 | 0.134/0.254/0.366 |

分解すると:

- **presence 次元が accuracy の主犯**。消すだけで acc 77.6→80.9（差の約 2/3 を回復）、macro F1 は
  official 並みに戻る。10% の capital 保有者を空間上で強く隔離し、最近傍マッチをそこに支配させて
  他の列を潰していた。amount も消しても acc はほぼ不変（80.9→81.0）。
- **amount（capital の log 量）は AUC を下げていた**。消すと AUC 82.4→84.1 と一段回復。
- **capital を完全に外すと accuracy は保つが、capital の marginal 忠実度が崩れる**（WSD が
  0.03→**0.13** に悪化）。埋め込みが capital を見ないと、生成される capital 値が実分布から自由に
  離れるため。→ official が capital を min-max で**薄く**使うのは、accuracy を落とさずに capital を
  そこそこ合わせる**バランス点**だった。過大（robust）でも無視（capital=0）でも WSD は悪化する。
- **残差 ~1.5 acc / ~3.3 AUC**（capital=0 でも official に届かない分）は、robust に残る唯一の違い＝
  fnlwgt の log 圧縮（＋official が薄く使う capital 信号を失った分）が担う。

要するに、**plain な min-max（評価空間と一致）から離れる工夫はどれも代償を伴う**。presence 次元は
最大の逸脱なので accuracy への害が最も大きく、log 量は AUC を、capital 除去は忠実度を、fnlwgt 圧縮は
残差を、それぞれ削っていた。

## 総括

- 埋め込みの精緻化は、**狙った列（capital）の分布忠実度は明確に改善する**が、**下流分類 utility は
  改善しない**。`robust_numeric` は誤差内の微増、`adult_semantic`/`public_fe` はむしろ悪化。
- ε は**レバーになる**が収穫逓減し、ノイズを切っても（ε=∞）PE 上限 ~82.5% で頭打ちで、同サイズ
  実データ上限 84% には届かない（残差は生成機構由来）。
- **埋め込み × ε**: robust の ε=1 での微増はノイズが埋め込みの粗さを覆った低 ε の産物で、ノイズを
  切ると official が明確に勝つ（ε=∞: official 82.5% > robust 77.6%）。DP ノイズは埋め込みの利点を
  隠していなかった。埋め込みが utility のレバーでないことが強まった。
- 実測した上限（同サイズ実データ acc 84%、全量 86.4%）まで accuracy で ~4 点、macro F1 で ~7 点の
  余地はあるが、その差は**埋め込みでは動かない**。残差は DP ノイズ・生成機構・少数クラスの弱さに
  由来すると考えられ、埋め込みはレバーではない。
- **教訓**: Tab-PE の埋め込みは「分類器に効く良い特徴量」を目指すのではなく、**列の情報を粗くせず、
  必要な列を落とさず、スケールだけを素直に整える**方向が良い。`robust_numeric`（capital の
  スケールだけ直し、他は落とさない）が 4 variant 中で **ε=1 では**最良だったのはこのためと解釈
  できる（ただし高 ε では official が勝つ。上記 #40）。
  列を埋め込みから外すと（`public_fe` の education、`adult_semantic` の education one-hot）、
  その列の同時整合が壊れる副作用も出る。

強い主張はしない。単一指標での優劣ではなく、utility・fidelity・意味的一貫性の trade-off として
読むべき結果である。tabicl が強力なため、埋め込みの改良が下流精度に表れにくい可能性も残る
（未確認）。
