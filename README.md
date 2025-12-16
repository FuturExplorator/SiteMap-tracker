Sitemap tools MVP
=================

Two small CLI tools for sitemap analysis:

- Intent Map: parse one or more sitemaps, tag each URL with action/object/scene/intent and emit a raw CSV plus a summary JSON.
- Sitemap Diff: compare an old and new sitemap, list new/removed URLs, and classify intents for the new URLs.

Quick start
-----------

- Python 3.9+.
- Optional deps if you want YAML config or LLM calls: `pip install pyyaml openai`.

Run the CLI:

```bash
python -m sitemap_tools intent-map --sitemap-url https://example.com/sitemap.xml --output-dir out
python -m sitemap_tools sitemap-diff --old https://example.com/old.xml --new https://example.com/new.xml --output-dir out_diff
```

Inputs
------

- `--sitemap-url` or `--sitemap-file` (paths) for intent-map; you can pass multiple.
- For diff: `--old` and `--new` each accept a URL or file path.
- The parser supports sitemap indexes recursively.

Outputs
-------

- Intent map:
  - `intent_map_raw.csv`: url, path, depth, tokens, action, object, scene, intent_category, notes, lastmod.
  - `intent_summary.json`: grouped by intent_category and by action+object (with sample URLs).
  - `intent_keywords_table.csv`: keywords first (tokens), action/object/scene/intent, heuristic note, related keywords, url.
- Diff:
  - `new_urls.csv`, `removed_urls.csv`.
  - `diff_summary.json`: counts and new URLs grouped by intent_category.

Config and knobs
----------------

- Default action/object dictionaries are built in. Override via `--config config.yml|json`.
- `--max-urls` and `--sample {first,random}` to cap big sitemaps (default max 500, take first).
- HTTP fetch: `--user-agent`, `--timeout`, `--delay` (seconds) between fetches; or skip fetching by using files.
- LLM enrichment is optional: set `--llm-model gpt-4o-mini` (or any OpenAI-compatible name), plus `--llm-base-url`/`--llm-api-key` as needed. If not set, rule-only tagging runs and unknowns stay empty.

Notes
-----

- Classification is URL/slug based; unknown or noisy slugs are marked `unknown` instead of hallucinated.
- No crawling of page content, no reliance on `<lastmod>` for diff—diff uses set difference.
- The code is modular (`sitemap`, `intent`, `llm`) so you can later wire a UI or other runners easily.
