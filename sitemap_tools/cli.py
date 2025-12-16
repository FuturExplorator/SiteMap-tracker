import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .config import load_config
from .intent import (
    IntentRecord,
    apply_heuristics,
    build_intent_records,
    clamp_records,
    enrich_with_llm,
    summarize_by_action_object,
    summarize_by_intent,
)
from .sitemap import SitemapEntry, load_sitemaps, normalize_url


def _ensure_output_dir(path: str) -> Path:
    out_dir = Path(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _write_intent_csv(path: Path, records: Sequence[IntentRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["url", "path", "path_depth", "slug_tokens", "action", "object", "scene", "intent_category", "notes", "lastmod"]
        )
        for rec in records:
            writer.writerow(rec.to_csv_row())


def _write_summary_json(path: Path, records: Sequence[IntentRecord]) -> None:
    summary = {
        "by_intent_category": summarize_by_intent(list(records)),
        "by_action_object": summarize_by_action_object(list(records)),
        "total_urls": len(records),
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)


def _configure_from_args(base_config: dict, args: argparse.Namespace) -> dict:
    cfg = dict(base_config)
    if args.max_urls is not None:
        cfg["max_urls"] = args.max_urls
    if args.sample is not None:
        cfg["sample_strategy"] = args.sample
    if args.timeout is not None:
        cfg["http"]["timeout"] = args.timeout
    if args.delay is not None:
        cfg["http"]["delay"] = args.delay
    if args.user_agent is not None:
        cfg["http"]["user_agent"] = args.user_agent
    if args.llm_model:
        cfg["llm"]["enabled"] = True
        cfg["llm"]["model"] = args.llm_model
    if args.llm_base_url:
        cfg["llm"]["base_url"] = args.llm_base_url
    if args.llm_api_key:
        cfg["llm"]["api_key"] = args.llm_api_key
    if args.llm_batch_size is not None:
        cfg["llm"]["batch_size"] = args.llm_batch_size
    return cfg


def _write_keyword_table_csv(path: Path, records: Sequence[IntentRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "keywords",
                "action",
                "object",
                "scene",
                "intent_category",
                "note",
                "similar_keywords",
                "url",
            ]
        )
        for rec in records:
            tokens = rec.filtered_tokens or []
            similar = rec.similar_keywords or []
            # Skip rows with no meaningful intent signals.
            if not tokens and not rec.action and not rec.object and (rec.intent_category == "unknown"):
                continue
            writer.writerow(
                [
                    " ".join(tokens),
                    rec.action,
                    rec.object,
                    rec.scene,
                    rec.intent_category,
                    rec.notes,
                    " ".join(similar),
                    rec.url,
                ]
            )


def run_intent_map(args: argparse.Namespace) -> None:
    sources: List[str] = []
    sources.extend(args.sitemap_url or [])
    sources.extend(args.sitemap_file or [])
    if not sources:
        raise SystemExit("Provide at least one --sitemap-url or --sitemap-file")

    config = _configure_from_args(load_config(args.config), args)
    entries = load_sitemaps(
        sources=sources,
        timeout=config["http"]["timeout"],
        user_agent=config["http"]["user_agent"],
        delay=config["http"]["delay"],
    )
    records = build_intent_records(entries, config["rules"]["actions"], config["rules"]["objects"])
    limited_records = clamp_records(records, config["max_urls"], config["sample_strategy"])
    if len(records) > len(limited_records):
        print(f"Clamped {len(records)} URLs to {len(limited_records)} using {config['sample_strategy']}", file=sys.stderr)

    enrich_with_llm(limited_records, config["llm"], verbose=args.verbose)
    apply_heuristics(limited_records)

    out_dir = _ensure_output_dir(args.output_dir)
    _write_intent_csv(out_dir / "intent_map_raw.csv", limited_records)
    _write_summary_json(out_dir / "intent_summary.json", limited_records)
    _write_keyword_table_csv(out_dir / "intent_keywords_table.csv", limited_records)
    if args.verbose:
        print(f"Wrote {len(limited_records)} rows to {out_dir}", file=sys.stderr)


def _write_new_urls_csv(path: Path, records: Sequence[IntentRecord], snapshot_label: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["url", "path", "path_depth", "slug_tokens", "action", "object", "scene", "intent_category", "notes", "first_seen_snapshot"]
        )
        for rec in records:
            writer.writerow(
                [
                    rec.url,
                    rec.path,
                    str(rec.path_depth),
                    " ".join(rec.slug_tokens),
                    rec.action,
                    rec.object,
                    rec.scene,
                    rec.intent_category,
                    rec.notes,
                    snapshot_label,
                ]
            )


def _write_removed_urls_csv(path: Path, entries: Sequence[SitemapEntry], snapshot_label: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["url", "path", "last_seen_snapshot"])
        for entry in entries:
            clean_url, clean_path = normalize_url(entry.url)
            writer.writerow([clean_url, clean_path, snapshot_label])


def run_sitemap_diff(args: argparse.Namespace) -> None:
    if not args.old or not args.new:
        raise SystemExit("Provide --old and --new sitemap paths/URLs")

    config = _configure_from_args(load_config(args.config), args)
    old_entries = load_sitemaps(
        sources=[args.old],
        timeout=config["http"]["timeout"],
        user_agent=config["http"]["user_agent"],
        delay=config["http"]["delay"],
    )
    new_entries = load_sitemaps(
        sources=[args.new],
        timeout=config["http"]["timeout"],
        user_agent=config["http"]["user_agent"],
        delay=config["http"]["delay"],
    )

    old_map = {e.url: e for e in old_entries}
    new_map = {e.url: e for e in new_entries}

    new_only_entries = [entry for url, entry in new_map.items() if url not in old_map]
    removed_entries = [entry for url, entry in old_map.items() if url not in new_map]

    new_records = build_intent_records(new_only_entries, config["rules"]["actions"], config["rules"]["objects"])
    enrich_with_llm(new_records, config["llm"], verbose=args.verbose)
    apply_heuristics(new_records)

    out_dir = _ensure_output_dir(args.output_dir)
    _write_new_urls_csv(out_dir / "new_urls.csv", new_records, args.new_label)
    _write_removed_urls_csv(out_dir / "removed_urls.csv", removed_entries, args.old_label)

    summary = {
        "summary": {
            "new_url_count": len(new_records),
            "removed_url_count": len(removed_entries),
            "new_urls_by_intent": summarize_by_intent(new_records),
        },
        "new_urls": [
            {
                "url": rec.url,
                "path": rec.path,
                "first_seen_snapshot": args.new_label,
                "action": rec.action,
                "object": rec.object,
                "scene": rec.scene,
                "intent_category": rec.intent_category,
                "notes": rec.notes,
            }
            for rec in new_records
        ],
        "removed_urls": [
            {
                "url": normalize_url(entry.url)[0],
                "path": normalize_url(entry.url)[1],
                "last_seen_snapshot": args.old_label,
            }
            for entry in removed_entries
        ],
    }
    with (out_dir / "diff_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    if args.verbose:
        print(
            f"New URLs: {len(new_records)}, removed: {len(removed_entries)}. Files written to {out_dir}",
            file=sys.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sitemap intent map and diff tools")
    sub = parser.add_subparsers(dest="command", required=True)

    intent_p = sub.add_parser("intent-map", help="Generate intent map from sitemaps")
    intent_p.add_argument("--sitemap-url", action="append", help="Sitemap URL", default=[])
    intent_p.add_argument("--sitemap-file", action="append", help="Sitemap file path", default=[])
    intent_p.add_argument("--output-dir", required=True, help="Output directory")
    intent_p.add_argument("--config", help="Config file (YAML or JSON)")
    intent_p.add_argument("--max-urls", type=int, help="Max URLs to process (default 500)")
    intent_p.add_argument("--sample", choices=["first", "random"], help="Sampling strategy when clamping")
    intent_p.add_argument("--timeout", type=int, help="HTTP timeout in seconds")
    intent_p.add_argument("--delay", type=float, help="Delay (seconds) between sitemap fetches")
    intent_p.add_argument("--user-agent", help="Custom User-Agent")
    intent_p.add_argument("--llm-model", help="OpenAI-compatible model name to enable LLM enrichment")
    intent_p.add_argument("--llm-base-url", help="OpenAI-compatible base URL")
    intent_p.add_argument("--llm-api-key", help="API key (or set env var)")
    intent_p.add_argument("--llm-batch-size", type=int, help="LLM batch size (default 20)")
    intent_p.add_argument("--verbose", action="store_true", help="Verbose logging")

    diff_p = sub.add_parser("sitemap-diff", help="Diff two sitemap snapshots")
    diff_p.add_argument("--old", required=True, help="Old sitemap URL or file")
    diff_p.add_argument("--new", required=True, help="New sitemap URL or file")
    diff_p.add_argument("--output-dir", required=True, help="Output directory")
    diff_p.add_argument("--config", help="Config file (YAML or JSON)")
    diff_p.add_argument("--timeout", type=int, help="HTTP timeout in seconds")
    diff_p.add_argument("--delay", type=float, help="Delay (seconds) between sitemap fetches")
    diff_p.add_argument("--user-agent", help="Custom User-Agent")
    diff_p.add_argument("--llm-model", help="OpenAI-compatible model name to enable LLM enrichment")
    diff_p.add_argument("--llm-base-url", help="OpenAI-compatible base URL")
    diff_p.add_argument("--llm-api-key", help="API key (or set env var)")
    diff_p.add_argument("--llm-batch-size", type=int, help="LLM batch size (default 20)")
    diff_p.add_argument("--old-label", default="old", help="Label/timestamp for old snapshot")
    diff_p.add_argument("--new-label", default="new", help="Label/timestamp for new snapshot")
    diff_p.add_argument("--verbose", action="store_true", help="Verbose logging")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "intent-map":
        run_intent_map(args)
    elif args.command == "sitemap-diff":
        run_sitemap_diff(args)
    else:  # pragma: no cover
        parser.print_help()


__all__ = ["main"]
