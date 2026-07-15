# データ

各デモは実行時にデータを自動ダウンロードする。取得元は第三者リポジトリ
[`toan-vt/cloud-data-store`](https://github.com/toan-vt/cloud-data-store/tree/main/tabular)
の `main`（`raw.githubusercontent.com/.../refs/heads/main/tabular/...`）。各実験は
`data_train.csv` / `data_test.csv` / `metadata.json` を読み込む
（`pe.data.TabularCSV`）。

> 再現性メモ: データは `main`（未固定参照）から取得している。厳密な再現には
> データ側のコミット SHA も固定・記録することが望ましい（本フェーズでは未固定）。

## データセット一覧

| データセット | 種別 | パス配下 | 分類 | 備考 |
|---|---|---|---|---|
| XOR stress test | 模擬 | `sim/xor-stress-test/{n}_feature_xor/` | 二値 | 高次相関のストレステスト。1feature で非公開 35,000 行 |
| SCM | 模擬 | `sim/scm/{tree,nn,rff}/` | 多クラス | 構造的因果モデル。prior により生成過程が異なる |
| Breast Cancer | 実 | `real/breast-cancer/` | 二値 | 30 数値特徴 + `diagnosis`。本フェーズの Smoke Test |
| Adult | 実 | `real/adult/` | 二値 | 本フェーズ未実行 |
| Artificial Characters | 実 | `real/artificial-characters/` | 多クラス | 5/6/7-way WSD 評価 |
| Person Activity | 実 | `real/person-activity/` | 多クラス | 本フェーズ未実行（5000 samples） |

## train/test と前処理

- 各実験は公式が用意した train/test split を `data_train.csv` / `data_test.csv`
  としてそのまま利用する。
- 分類器評価では、合成 train と実 test を結合した上で categorical を `LabelEncoder`、
  数値を `MinMaxScaler` で符号化する（`classifier.py:86-97`）。
- WSD では全列を非公開データのレンジで [0,1] 正規化する（`compute_wsd.py:97-104`）。

## 列構成（実測）

- **Breast Cancer**: 30 数値特徴 + target `diagnosis`（合成 CSV ヘッダより確認）。
- **SCM (rff)** / **Artificial Characters**: 特徴 + label 合わせて計 8 列
  （5/6/7-way の組合せを取れる次元数）。

> 各データセットの正確な行数・categorical/numerical の内訳・target は
> `metadata.json` に依存する。詳細な metadata の網羅は後続フェーズで補完する
> （一部 **UNCONFIRMED**）。
