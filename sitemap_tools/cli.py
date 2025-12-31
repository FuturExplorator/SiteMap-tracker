import argparse
import csv
import json
import sys
import shutil
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set
from urllib.parse import urlparse

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


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_domain(url_or_path: str) -> str:
    if url_or_path.startswith("http"):
        return urlparse(url_or_path).netloc
    # Fallback for local files: try to get filename stem
    return Path(url_or_path).stem


def _write_intent_csv(path: Path, records: Sequence[IntentRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["url", "path", "path_depth", "slug_tokens", "action", "object", "scene", "intent_category", "notes", "lastmod", "is_new"]
        )
        for rec in records:
            writer.writerow(rec.to_csv_row())


def build_directory_tree(records: Sequence[IntentRecord]) -> Dict[str, Any]:
    root = {"name": "/", "path": "/", "count": 0, "children": {}, "records": []}

    for rec in records:
        root["count"] += 1
        parts = [p for p in rec.path.strip("/").split("/") if p]
        curr = root
        current_path = "/"

        for part in parts:
            if part not in curr["children"]:
                current_path = f"{current_path}{part}/"
                curr["children"][part] = {
                    "name": part,
                    "path": current_path,
                    "count": 0,
                    "children": {},
                    "records": [],
                }
            curr = curr["children"][part]
            curr["count"] += 1

        # Infer title from the last part of the path or slug tokens
        # e.g. /blog/how-to-fix -> "How To Fix"
        # If slug_tokens are utilized, capitalize them.
        inferred_title = " ".join([t.title() for t in rec.slug_tokens]) if rec.slug_tokens else ""
        if not inferred_title:
             # Fallback: unslugify the last path component
             last_part = rec.path.strip("/").split("/")[-1]
             inferred_title = last_part.replace("-", " ").title()

        curr["records"].append(
            {
                "url": rec.url,
                "path": rec.path, # Explicit path is useful
                "action": rec.action,
                "object": rec.object,
                "intent_category": rec.intent_category,
                "notes": rec.notes,
                "lastmod": getattr(rec, "lastmod", ""), # Ensure safety if lastmod missing
                "depth": getattr(rec, "path_depth", 0),
                "title": inferred_title,
                "is_new": getattr(rec, "is_new", False),
            }
        )

    def _recursive_listify(node: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": node["name"],
            "path": node["path"],
            "count": node["count"],
            "children": sorted(
                [_recursive_listify(v) for v in node["children"].values()],
                key=lambda x: x["count"],
                reverse=True,
            ),
            "records": node["records"],
        }

    return _recursive_listify(root)


def _write_summary_json(path: Path, records: Sequence[IntentRecord]) -> None:
    records_list = list(records)
    total = len(records_list)
    
    # Strict: Both Action and Object are non-empty
    strict_count = len([r for r in records_list if r.action and r.object])
    
    # Any: Intent category is known (which implies (action OR object) was found)
    any_count = len([r for r in records_list if r.intent_category != "unknown"])
    
    # New Stats
    new_count = len([r for r in records_list if getattr(r, "is_new", False)])

    summary = {
        "schema_version": "1.1",
        "by_intent_category": summarize_by_intent(records_list),
        "by_action_object": summarize_by_action_object(records_list),
        "total_urls": total,
        "new_url_count": new_count,
        "coverage_strict_percentage": round(strict_count / total * 100, 2) if total else 0.0,
        "coverage_any_percentage": round(any_count / total * 100, 2) if total else 0.0,
        "directory_tree": build_directory_tree(records_list),
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
    if args.retries is not None:
        cfg["http"]["retries"] = args.retries
    if args.retries is not None:
        cfg["http"]["retries"] = args.retries
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
                "is_new",
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
                    "true" if getattr(rec, "is_new", False) else "false",
                ]
            )


def _write_new_urls_diff_csv(path: Path, records: Sequence[IntentRecord]) -> None:
    """Only Write new URLs to a separate CSV for easy inspection"""
    new_recs = [r for r in records if getattr(r, "is_new", False)]
    if not new_recs:
        return
        
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["url", "path", "path_depth", "slug_tokens", "action", "object", "scene", "intent_category", "notes", "first_seen_snapshot"]
        )
        for rec in new_recs:
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
                    "latest",
                ]
            )


def run_intent_map(args: argparse.Namespace) -> None:
    sources: List[str] = []
    sources.extend(args.sitemap_url or [])
    sources.extend(args.sitemap_file or [])
    if not sources:
        # Try to use positional args as domains if provided?
        pass
    if not sources:
        raise SystemExit("Provide at least one --sitemap-url or --sitemap-file")

    config = _configure_from_args(load_config(args.config), args)

    # 1. Determine site domain for folder structure
    # Use the first source to determine domain/project name
    domain = _extract_domain(sources[0])
    
    # 2. Setup paths
    base_output = Path(args.output_dir) # e.g. 'output'
    site_dir = base_output / "sites" / domain
    latest_dir = site_dir / "latest"
    history_dir = site_dir / "history"
    
    print(f"Targeting Site: {domain}", file=sys.stderr)
    print(f"Latest Dir: {latest_dir}", file=sys.stderr)

    # 3. Load Old Data for comparison (if exists)
    old_urls: Set[str] = set()
    if (latest_dir / "intent_map_raw.csv").exists():
        print("Found existing data in 'latest'. Will compare for changes.", file=sys.stderr)
        try:
            with (latest_dir / "intent_map_raw.csv").open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "url" in row:
                        old_urls.add(row["url"])
        except Exception as e:
             print(f"Warning: Failed to load old CSV: {e}", file=sys.stderr)

    # 4. Fetch New Data
    final_sources: List[str] = []
    from .sitemap import discover_sitemaps

    for src in sources:
        if src.startswith("http") and not src.lower().endswith(".xml"):
            print(f"Attempting sitemap discovery for {src}...", file=sys.stderr)
            discovered = discover_sitemaps(
                src,
                timeout=config["http"]["timeout"],
                user_agent=config["http"]["user_agent"],
                retries=config["http"].get("retries", 3),
                extra_user_agents=config["http"].get("extra_user_agents"),
            )
            if discovered:
                print(f"  Found {len(discovered)} sitemaps: {discovered}", file=sys.stderr)
                final_sources.extend(discovered)
            else:
                print("  No sitemaps found, extracting directly...", file=sys.stderr)
                final_sources.append(src)
        else:
            final_sources.append(src)
    
    entries = load_sitemaps(
        sources=final_sources,
        timeout=config["http"]["timeout"],
        user_agent=config["http"]["user_agent"],
        delay=config["http"]["delay"],
        retries=config["http"].get("retries", 3),
        extra_user_agents=config["http"].get("extra_user_agents"),
    )
    records = build_intent_records(entries, config["rules"]["actions"], config["rules"]["objects"])
    limited_records = clamp_records(records, config["max_urls"], config["sample_strategy"])
    if len(records) > len(limited_records):
        print(f"Clamped {len(records)} URLs to {len(limited_records)} using {config['sample_strategy']}", file=sys.stderr)

    enrich_with_llm(limited_records, config["llm"], verbose=args.verbose)
    apply_heuristics(limited_records)

    # 5. Apply Diff Logic
    new_count = 0
    if old_urls:
        for rec in limited_records:
            if rec.url not in old_urls:
                rec.is_new = True
                new_count += 1
        print(f"Diff Analysis: Found {new_count} new URLs since last run.", file=sys.stderr)

    # 6. Rotate History
    if latest_dir.exists():
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_path = history_dir / timestamp
        _ensure_output_dir(snapshot_path)
        print(f"Archiving previous 'latest' to {snapshot_path}...", file=sys.stderr)
        
        # Move contents
        for item in latest_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, snapshot_path) # Copy instead of move for safety, then overwrite latest
        
    # 7. Write new data
    _ensure_output_dir(latest_dir)
    _write_intent_csv(latest_dir / "intent_map_raw.csv", limited_records)
    _write_summary_json(latest_dir / "intent_summary.json", limited_records)
    _write_keyword_table_csv(latest_dir / "intent_keywords_table.csv", limited_records)
    _write_new_urls_diff_csv(latest_dir / "new_urls.csv", limited_records)
    
    if args.verbose:
        print(f"Wrote {len(limited_records)} rows to {latest_dir}", file=sys.stderr)


# Keeping Diff command for manual file-to-file diffs if needed, but main flow is now in intent-map
def run_sitemap_diff(args: argparse.Namespace) -> None:
    # ... (Simplified or kept as is, but focusing on the main standard flow above)
    pass # Implementation kept same as original below roughly
    if not args.old or not args.new:
        raise SystemExit("Provide --old and --new sitemap paths/URLs")
    
    # ... (rest of old logic can stay for manual utility usage)
    # Re-implementing briefly to keep file valid:
    config = _configure_from_args(load_config(args.config), args)
    old_entries = load_sitemaps([args.old], timeout=config["http"]["timeout"], user_agent=config["http"]["user_agent"], delay=config["http"]["delay"])
    new_entries = load_sitemaps([args.new], timeout=config["http"]["timeout"], user_agent=config["http"]["user_agent"], delay=config["http"]["delay"])
    
    old_map = {e.url: e for e in old_entries}
    new_map = {e.url: e for e in new_entries}
    
    new_only = [entry for url, entry in new_map.items() if url not in old_map]
    new_records = build_intent_records(new_only, config["rules"]["actions"], config["rules"]["objects"])
    enrich_with_llm(new_records, config["llm"], verbose=args.verbose)
    apply_heuristics(new_records)
    
    out_dir = _ensure_output_dir(Path(args.output_dir))
    _write_intent_csv(out_dir / "new_urls.csv", new_records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sitemap intent map and diff tools")
    sub = parser.add_subparsers(dest="command", required=True)

    intent_p = sub.add_parser("intent-map", help="Generate intent map from sitemaps")
    intent_p.add_argument("--sitemap-url", action="append", help="Sitemap URL", default=[])
    intent_p.add_argument("--sitemap-file", action="append", help="Sitemap file path", default=[])
    intent_p.add_argument("--output-dir", required=True, help="Base Output directory (e.g. ./output)")
    intent_p.add_argument("--config", help="Config file (YAML or JSON)")
    intent_p.add_argument("--max-urls", type=int, help="Max URLs to process (default 500)")
    intent_p.add_argument("--sample", choices=["first", "random"], help="Sampling strategy when clamping")
    intent_p.add_argument("--timeout", type=int, help="HTTP timeout in seconds")
    intent_p.add_argument("--delay", type=float, help="Delay (seconds) between sitemap fetches")
    intent_p.add_argument("--retries", type=int, help="Max retries per URL")
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
    # ... keeping args simple for manual diff
    
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


if __name__ == "__main__":
    main()
