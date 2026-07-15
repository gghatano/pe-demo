"""Build the HTML report from the Markdown source (issue #6).

Converts each page in ``content/*.md`` to ``htmls/*.html`` using a single ``PAGES``
configuration. HTML is generated from Markdown only — never edit the HTML by hand.

Features (spec sec.10): UTF-8, GitHub-Pages ready, Markdown tables, fenced code,
MathJax, auto TOC from h2/h3, top tabs with active state, responsive 2→1 column
layout, and base64-embedded figures so the report is self-contained.

Include markers handled in the Markdown before conversion:
- ``<!-- INCLUDE:experiments_table -->`` → Markdown table from results/summaries/experiments.csv
- ``<!-- INCLUDE:figure:NAME -->``        → base64 <img> from results/figures/NAME.png

Usage:
    uv run python scripts/build_html.py
"""

from __future__ import annotations

import base64
import csv
import re
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT = REPO_ROOT / "content"
HTMLS = REPO_ROOT / "htmls"
SUMMARIES = REPO_ROOT / "results" / "summaries"
FIGURES = REPO_ROOT / "results" / "figures"

# Single source of page structure: (markdown stem, tab label, emoji).
PAGES = [
    ("index", "レポート", "📄"),
    ("method-tabpe", "Tab-PE", "🧩"),
    ("experiments", "実験", "🧪"),
    ("data-notes", "データ", "🔬"),
    ("results-detail", "詳細結果", "📈"),
    ("engineering-notes", "エンジニアリング", "🛠"),
    ("faq", "QA", "❓"),
]

# Columns of experiments.csv to show, with display headers.
TABLE_COLS = [
    ("experiment", "実験"), ("dataset", "データ"), ("status", "判定"),
    ("runtime_s", "実行時間(s)"), ("classifier", "分類器"),
    ("test_acc", "acc"), ("test_f1", "F1"), ("test_auc", "AUC"),
    ("wsd", "WSD"), ("epsilon", "ε"), ("notes", "備考"),
]


def experiments_table_md() -> str:
    csv_path = SUMMARIES / "experiments.csv"
    if not csv_path.exists():
        return "_（`experiments.csv` が未生成です。`collect_results.py` を実行してください）_"
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    header = "| " + " | ".join(h for _, h in TABLE_COLS) + " |"
    sep = "| " + " | ".join("---" for _ in TABLE_COLS) + " |"
    body = []
    for r in rows:
        cells = []
        for key, _ in TABLE_COLS:
            v = (r.get(key) or "").replace("|", "\\|")
            cells.append(v if v else "–")
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


def figure_img_html(name: str) -> str:
    png = FIGURES / f"{name}.png"
    if not png.exists():
        return f'<p class="missing-figure">［図 {name} は未生成（make_figures.py を実行）］</p>'
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return f'<figure><img alt="{name}" src="data:image/png;base64,{b64}"></figure>'


FIG_TOKEN = "@@FIGURE:{name}@@"


def preprocess(md_text: str) -> str:
    md_text = md_text.replace("<!-- INCLUDE:experiments_table -->", experiments_table_md())

    def _fig(m: re.Match) -> str:
        return "\n\n" + FIG_TOKEN.format(name=m.group(1)) + "\n\n"

    return re.sub(r"<!--\s*INCLUDE:figure:([\w\-]+)\s*-->", _fig, md_text)


def postprocess_figures(html: str) -> str:
    def _sub(m: re.Match) -> str:
        return figure_img_html(m.group(1))
    # The token may be wrapped in <p>…</p> by the Markdown converter.
    html = re.sub(r"<p>\s*@@FIGURE:([\w\-]+)@@\s*</p>", lambda m: _sub(m), html)
    return re.sub(r"@@FIGURE:([\w\-]+)@@", lambda m: _sub(m), html)


TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script>
window.MathJax = {{ tex: {{ inlineMath: [['$','$'],['\\\\(','\\\\)']] }} }};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
:root {{ --fg:#1b1f24; --bg:#ffffff; --muted:#57606a; --accent:#0969da;
  --border:#d0d7de; --code-bg:#f6f8fa; --tab-bg:#f6f8fa; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; color:var(--fg); background:var(--bg); font-family:-apple-system,
  BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,"Hiragino Sans","Noto Sans JP",sans-serif;
  line-height:1.65; }}
header.top {{ position:sticky; top:0; z-index:10; background:var(--bg);
  border-bottom:1px solid var(--border); padding:.6rem 1rem; }}
header.top h1 {{ font-size:1.05rem; margin:.2rem 0 .6rem; }}
nav.tabs {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
nav.tabs a {{ text-decoration:none; color:var(--fg); background:var(--tab-bg);
  border:1px solid var(--border); border-radius:999px; padding:.3rem .8rem; font-size:.9rem; }}
nav.tabs a.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
.layout {{ display:grid; grid-template-columns:260px minmax(0,1fr); gap:2rem;
  max-width:1200px; margin:0 auto; padding:1.5rem 1rem; }}
aside.toc {{ position:sticky; top:5.2rem; align-self:start; max-height:calc(100vh - 6rem);
  overflow:auto; font-size:.9rem; border-left:2px solid var(--border); padding-left:1rem; }}
aside.toc .toctitle {{ font-weight:600; color:var(--muted); }}
aside.toc ul {{ list-style:none; padding-left:.8rem; margin:.3rem 0; }}
aside.toc a {{ text-decoration:none; color:var(--muted); }}
aside.toc a:hover {{ color:var(--accent); }}
main {{ min-width:0; }}
main h2 {{ border-bottom:1px solid var(--border); padding-bottom:.3rem; margin-top:2rem; }}
main table {{ border-collapse:collapse; width:100%; display:block; overflow-x:auto; font-size:.92rem; }}
main th, main td {{ border:1px solid var(--border); padding:.4rem .6rem; text-align:left; vertical-align:top; }}
main th {{ background:var(--code-bg); }}
main pre {{ background:var(--code-bg); padding:.8rem 1rem; overflow-x:auto; border-radius:6px; }}
main code {{ background:var(--code-bg); padding:.1rem .3rem; border-radius:4px; }}
main pre code {{ background:none; padding:0; }}
figure {{ margin:1rem 0; }} figure img {{ max-width:100%; height:auto; border:1px solid var(--border); border-radius:6px; }}
.missing-figure {{ color:var(--muted); font-style:italic; }}
a {{ color:var(--accent); }}
@media (max-width:820px) {{ .layout {{ grid-template-columns:1fr; }} aside.toc {{ position:static; max-height:none; border-left:none; padding-left:0; }} }}
@media (prefers-color-scheme:dark) {{ :root {{ --fg:#e6edf3; --bg:#0d1117; --muted:#8b949e;
  --accent:#58a6ff; --border:#30363d; --code-bg:#161b22; --tab-bg:#161b22; }} }}
</style>
</head>
<body>
<header class="top">
  <h1>Tab-PE 公式実装 再現追試</h1>
  <nav class="tabs">{tabs}</nav>
</header>
<div class="layout">
  <aside class="toc">{toc}</aside>
  <main>{body}</main>
</div>
</body>
</html>
"""


def build_page(stem: str, title: str) -> str:
    md_text = (CONTENT / f"{stem}.md").read_text(encoding="utf-8")
    md_text = preprocess(md_text)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    body = md.convert(md_text)
    body = postprocess_figures(body)
    toc = md.toc or ""

    tabs = "".join(
        f'<a class="{"active" if s == stem else ""}" href="{s}.html">{emoji} {label}</a>'
        for s, label, emoji in PAGES
    )
    return TEMPLATE.format(title=title, tabs=tabs, toc=toc, body=body)


def main() -> int:
    HTMLS.mkdir(parents=True, exist_ok=True)
    (HTMLS / ".nojekyll").write_text("", encoding="utf-8")
    for stem, label, _ in PAGES:
        title = "Tab-PE 再現追試" if stem == "index" else f"{label} — Tab-PE 再現追試"
        html = build_page(stem, title)
        (HTMLS / f"{stem}.html").write_text(html, encoding="utf-8")
        print(f"wrote htmls/{stem}.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
