# Adult 向け埋め込み・距離の設計メモ（#24）

公式 `TabularEmbedding` を Adult 固有の性質に合わせて精緻化する追加実験
（#24）の設計と、変換に使う公開定数の出典をまとめる。実装は
`pe_demo/embedding/adult.py`（`AdultEmbedding`）、runner は
`scripts/experiments/run_adult_embedding.py`。

これは**公式再現条件の変更**であり、既存 `adult`（`EXECUTED`）結果は置換しない。
`adult_embedding_*` という独立実験として記録する。

## Adult の列

- 数値: `age`, `fnlwgt`, `education-num`, `capital-gain`, `capital-loss`, `hours-per-week`
- カテゴリ: `workclass`, `education`, `marital-status`, `occupation`, `relationship`,
  `race`, `sex`, `native-country`
- label: `income`（埋め込み対象外。クラスごとに PE を実行）

## 公式ベースライン（`official` variant）

`pe.embedding.TabularEmbedding(info)` と同一。数値列は metadata の min/max で 0–1 線形
正規化（`num_weight=1`）、カテゴリ列は active 値を `cat_weight=1/3` とする one-hot、
距離は連結ベクトル上の L2。回帰比較用に `AdultEmbedding(variant="official")` は
これと数値的に一致させる。

## DP 上の約束（重要）

- `robust_numeric` / `adult_semantic` の変換に使う値域は、**秘密データから算出しない**。
  下記の公開 domain bounds（既知の Adult 仕様）を固定定数として使う。
- `official` variant のみ、公式互換のため `info`（metadata 由来の min/max）を使う
  （公式実装がそうしているため、ベースラインとして踏襲）。
- 重み（`fnlwgt_weight` 等）は事前定義した 3 variant で固定し、秘密データの結果を見ながら
  反復調整しない（適応的選択は privacy を消費し得るため）。
- nearest-neighbor histogram・Gaussian noise・privacy accounting は変更しない。

## 公開 domain bounds（固定定数）

UCI Adult / 一般に知られた値域を採用する。範囲外は `[0,1]` に clip する。

| 列 | min | max | 出典・根拠 |
|---|---|---|---|
| `age` | 17 | 90 | UCI Adult の年齢範囲 |
| `fnlwgt` | 0 | 1,500,000 | Census 標本重み。上限は既知の最大付近を丸めた固定値 |
| `education-num` | 1 | 16 | 学歴の順序コード（下表） |
| `capital-gain` | 0 | 99,999 | UCI Adult の上限コード 99999 |
| `capital-loss` | 0 | 4,356 | UCI Adult の観測上限 |
| `hours-per-week` | 1 | 99 | UCI Adult の範囲 |

出典: UCI Machine Learning Repository, Adult (Census Income) データセット仕様
<https://archive.ics.uci.edu/dataset/2/adult>。上限は既知の観測上限・コード値を用い、
秘密データから再計算しない。

## `education` → `education-num` 対応表（`adult_semantic` 用）

UCI Adult で定義された学歴コード。`education` の生 one-hot と `education-num` の
二重計上をやめ、`education-num` の順序表現を主表現とする。合成レコードで両者が
不一致（例: `education=Bachelors` なのに `education-num≠13`）の場合、penalty 次元を立てる。

| education | education-num |
|---|---|
| Preschool | 1 |
| 1st-4th | 2 |
| 5th-6th | 3 |
| 7th-8th | 4 |
| 9th | 5 |
| 10th | 6 |
| 11th | 7 |
| 12th | 8 |
| HS-grad | 9 |
| Some-college | 10 |
| Assoc-voc | 11 |
| Assoc-acdm | 12 |
| Bachelors | 13 |
| Masters | 14 |
| Prof-school | 15 |
| Doctorate | 16 |

出典: 同上 UCI Adult。未知の `education` 値（対応表に無い値）は暗黙にカテゴリ 0 へ
落とさず、明示的にエラーとする。

## variant 定義

### `robust_numeric`

`official` に対し数値変換だけ変更する。カテゴリ列・`age`・`education-num`・
`hours-per-week` は公式と同じ（公開 bounds で min-max）。

- `fnlwgt`: `log1p(x)` を公開 bounds で 0–1 化し、`fnlwgt_weight=0.25` を掛ける。
- `capital-gain`, `capital-loss`: 各列を 2 次元へ展開する。
  - presence: `1[x>0] * capital_presence_weight`（既定 `1/3`）
  - amount: `log1p(x)/log1p(max) * capital_amount_weight`（既定 `1.0`）

### `adult_semantic`

`robust_numeric` に加えて:

- `education` の生 one-hot をやめ、`education-num`（min-max）を主表現とする。
- `education` と `education-num` の不一致に `education_inconsistent=1 * education_consistency_weight`
  （既定 `1/3`）、一致なら 0 の penalty 次元を追加する。
- 元の `education` 列は出力 CSV から削除しない（変更するのは距離計算用埋め込みだけ）。

### `public_fe`（公開 FE、#36）

Adult の一般的な特徴量エンジニアリング（ML 文献の**固定された公開ルール**）に基づく埋め込み。
このデータの正解 `income` も私的統計も一切使わないため、**リークにならない**。

- `fnlwgt` を落とす（個人属性ではなく標本重み。予測に使わないのが定石）。
- `age` を固定公開エッジ `[35, 50]` で 3 分割（young/middle/old）、`hours-per-week` を
  `[30, 40, 60]` で 4 分割（part-time/standard/long/excessive）し、ビン index を順序 min-max で埋め込む。
- `education-num` を公開 bounds の ordinal で保持（`education` one-hot は落とす）。
- capital: `extra_income` の 3 値 one-hot `{none, positive, negative}`（符号）＋ `log1p(gain+loss)` の
  公開 bounds 正規化（量）。生の `capital-gain`/`capital-loss` 数値は落とす。
- `native-country` を `US`/`非US` に集約。他カテゴリ（workclass, marital-status, occupation,
  relationship, race, sex）は one-hot。

**リーク境界（重要）**: ビン境界（35/50、30/40/60）・符号化・地理グループ・fnlwgt 除去は
すべて**公開知識で固定**しており、私的データの分位点・相関・target encoding は使わない。
未知カテゴリは暗黙に写像せず明示エラー。行独立で最近傍 histogram の 1 レコード感度を増やさない。
> 出典（公開 FE の一般的手法）: MachineLearningMastery, Adult census income の各解説記事、
> UCI Adult 仕様。「このデータに特化して正解を覗く特徴量」はリークになるため採用しない。

## 追加評価（最終合成 CSV に対して）

公式の TabICL 評価と分離して計算する（PE 反復中の選択には使わない）。

- `education` と `education-num` の不整合率
- `capital-gain>0` / `capital-loss>0` の実データと合成データの比率差
- `fnlwgt` を除いた特徴で学習した分類器の Accuracy / Macro F1 / AUC
- 各 variant の実行時間

## 仮説

- H1: `capital-gain/loss` を「ゼロか否か」＋「正値の log 量」に分解すると、所得分類に
  関係する差を距離へ反映しやすくなる。
- H2: `education` と `education-num` の重複を整理し不整合へ penalty を与えると、生成
  レコードの意味的一貫性が上がる。
- H3: `fnlwgt` の寄与を下げると、標本重みではなく人物属性に基づく最近傍投票になり、
  下流 utility が改善する。

3 variant × 3 seed 以上で mean±std を集計し、各仮説を支持・不支持・未判定で結論付ける
（3 seed 本実験は #22 の seed 制御と並行。実装先行段階では runner と単一 seed smoke まで）。
