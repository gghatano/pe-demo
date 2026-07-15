"""content/*.md → htmls/ を ark ビルダーで生成する（#6 レポート）。

ビルダー本体（`ark/`）は gghatano/synth-report-kit（MIT）から取り込んだ汎用の
「論文体レポート＋補助タブ」HTML ジェネレータ。ヒーロー＋タブ＋目次サイドバー、
本文中の PNG を base64 埋め込み、mermaid 描画、MathJax、出典チップ／バッジに対応する。

`PAGES` が単一の真実（ページ構成）。存在しない md は自動スキップされる。

実行:
    uv run python scripts/collect_results.py   # 表を content に注入 + summaries 生成
    uv run python scripts/make_figures.py      # results/figures/*.png を生成
    uv run python scripts/build_site.py        # htmls/*.html を生成
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ark import build_html, context as ctx  # noqa: E402

# ページ構成（単一の真実）。out 名は content 内の相互リンクと一致させる。
PAGES = [
    {"md": "content/index.md", "out": "index.html", "key": "report",
     "nav": "📄 レポート", "subtitle": "Tab-PE 公式デモ 再現追試"},
    {"md": "content/method-tabpe.md", "out": "method-tabpe.html", "key": "method",
     "nav": "🧩 Tab-PE", "subtitle": "手法・論文↔コード対応"},
    {"md": "content/experiments.md", "out": "experiments.html", "key": "experiments",
     "nav": "🧪 実験", "subtitle": "公式デモ・条件・再現判定"},
    {"md": "content/data-notes.md", "out": "data-notes.html", "key": "data",
     "nav": "🔬 データ", "subtitle": "データセット・取得元・前処理"},
    {"md": "content/results-detail.md", "out": "results-detail.html", "key": "results",
     "nav": "📈 詳細結果", "subtitle": "実験別の指標と反復推移"},
    {"md": "content/engineering-notes.md", "out": "engineering-notes.html", "key": "engineering",
     "nav": "🛠 エンジニアリング", "subtitle": "環境構築・再現手順・実装メモ"},
    {"md": "content/faq.md", "out": "faq.html", "key": "faq",
     "nav": "❓ QA", "subtitle": "よくある疑問と設計判断"},
]


def main() -> int:
    rep = ctx.load_config(REPO_ROOT)["report"]
    site_cfg = {
        "repo_url": rep.get("repo_url", "https://github.com/gghatano/pe-demo"),
        "upstream_url": rep.get("upstream_url", "https://github.com/microsoft/DPSDA"),
        "hero_title": rep.get("hero_title", "Tab-PE 公式実装 再現追試"),
        "outdir": "htmls",
        "pages": PAGES,
    }
    written = build_html.build(REPO_ROOT, site_cfg)
    if not written:
        print("content/*.md が見つかりません。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
