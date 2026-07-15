# Task 009: Build Markdown and HTML reports

## Source

- `docs/spec.md`, sections 2.3, 9, 10, and 12 Steps 10 and 11
- Depends on `task-008`

## Objective

Create a report system where Markdown is the source of truth and HTML is generated reproducibly.

## Scope

- Create all required `content/*.md` pages.
- Implement `scripts/build_html.py`.
- Generate all required pages under `htmls/`.
- Support Markdown tables, fenced code, MathJax, h2/h3 table of contents, active tabs, responsive layout, and relative image paths.
- Base64-embed figures when required by the final design.
- Ensure page configuration is centralized.

## Deliverables

- `content/index.md`
- `content/method-tabpe.md`
- `content/experiments.md`
- `content/data-notes.md`
- `content/results-detail.md`
- `content/engineering-notes.md`
- `content/faq.md`
- `scripts/build_html.py`
- `htmls/*.html`
- `htmls/.nojekyll`

## Validation

- `uv run python scripts/build_html.py` succeeds.
- HTML pages are generated from Markdown in the same run.
- No manual edits are required under `htmls/`.
- Navigation works with relative paths.
- The report distinguishes execution success from reproduction.

## Out of scope

- Publishing to GitHub Pages unless requested separately.
- Directly editing generated HTML.
