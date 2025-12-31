import json
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .sitemap import SitemapEntry, normalize_url


@dataclass
class IntentRecord:
    url: str
    path: str
    path_depth: int
    slug_tokens: List[str]
    action: str = ""
    object: str = ""
    scene: str = ""
    intent_category: str = ""
    notes: str = ""
    lastmod: Optional[str] = None
    similar_keywords: List[str] = field(default_factory=list)
    filtered_tokens: List[str] = field(default_factory=list)
    is_new: bool = False

    def to_csv_row(self) -> List[str]:
        return [
            self.url,
            self.path,
            str(self.path_depth),
            " ".join(self.slug_tokens),
            self.action,
            self.object,
            self.scene,
            self.intent_category,
            self.notes,
            self.lastmod or "",
            "true" if self.is_new else "false",
        ]


def path_depth(path: str) -> int:
    return len([seg for seg in path.split("/") if seg])


def tokenize_slug(path: str) -> List[str]:
    # Use all segments, not just the last one
    segments = [s for s in path.strip("/").split("/") if s]
    tokens = []
    for seg in segments:
        tokens.extend(re.split(r"[-_]+", seg))
    return [t.lower() for t in tokens if t]


STOPWORDS = {
    "login",
    "log",
    "signin",
    "sign-in",
    "signup",
    "sign-up",
    "account",
    "profile",
    "dashboard",
    "pricing",
    "price",
    "prices",
    "plan",
    "plans",
    "faq",
    "help",
    "support",
    "contact",
    "blog",
    "blogs",
    "tag",
    "tags",
    "category",
    "categories",
    "news",
    "about",
    "docs",
    "doc",
    "documentation",
    "api",
    "developer",
    "developers",
    "status",
    "privacy",
    "policy",
    "terms",
    "changelog",
    "roadmap",
    "careers",
    "jobs",
    "download",
    "downloads",
    "guide",
    "guides",
    "tutorial",
    "tutorials",
    "template",
    "templates",
    "example",
    "examples",
    "sample",
    "samples",
    "home",
    "landing",
    "app",
    "apps",
    "www",
    "ai",
}


def filter_tokens(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in STOPWORDS]


def _stem(token: str) -> str:
    """
    Lightweight Porter-like stemmer.
    Removes common suffixes to improve matching recall.
    """
    # Step 1: Plurals and simple suffixes
    if token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    
    # Step 2: Common endings
    suffixes = [
        ("ing", ""),
        ("ed", ""),
        ("ment", ""),
        ("ness", ""),
        ("ers", ""),
        ("er", ""),
        ("able", ""),
        ("ible", ""),
        ("ion", ""),
    ]
    for suff, repl in suffixes:
        if token.endswith(suff):
             # Basic constraint: don't reduce too short (e.g., "ring" -> "r")
            if len(token) - len(suff) > 2:
                return token[: -len(suff)] + repl
            
    return token


def rule_infer(tokens: Iterable[str], actions: List[str], objects: List[str]) -> Tuple[str, str]:
    token_list = list(tokens)
    
    # Stemming map: token -> stem
    stems = {t: _stem(t) for t in token_list}
    stem_set = set(stems.values())

    # Pre-stem actions and objects for comparison
    action_stems = {a: _stem(a) for a in actions}
    object_stems = {o: _stem(o) for o in objects}
    
    found_action = ""
    found_obj = ""

    # 1. Look for matches using stems
    
    # Check Actions
    # Direct match first (unstemmed)
    found_action = next((a for a in actions if a.lower() in token_list), "")
    if not found_action:
        # Stemmed match
        for a, astem in action_stems.items():
            if astem in stem_set:
                found_action = a
                break
    
    # Check Objects
    found_obj = next((o for o in objects if o.lower() in token_list), "")
    if not found_obj:
        for o, ostem in object_stems.items():
            if ostem in stem_set:
                found_obj = o
                break

    # 2. Synonym match (Reverse lookup with stemming)
    if not found_action:
        for canon, syns in ACTION_SYNONYMS.items():
            # Check unstemmed synonyms
            if any(s in token_list for s in syns):
                found_action = canon
                break
            # Check stemmed synonyms
            syn_stems = {_stem(s) for s in syns}
            if not set(syn_stems).isdisjoint(stem_set):
                found_action = canon
                break

    if not found_obj:
        for canon, syns in OBJECT_SYNONYMS.items():
            if any(s in token_list for s in syns):
                found_obj = canon
                break
            syn_stems = {_stem(s) for s in syns}
            if not set(syn_stems).isdisjoint(stem_set):
                found_obj = canon
                break

    return found_action, found_obj


def derive_intent_category(action: str, obj: str) -> str:
    if action and obj:
        return f"{action}-{obj}"
    if action:
        return f"{action}-general"
    if obj:
        return f"general-{obj}"
    return "unknown"


def build_intent_records(
    entries: Iterable[SitemapEntry],
    rule_actions: List[str],
    rule_objects: List[str],
) -> List[IntentRecord]:
    records: List[IntentRecord] = []
    for entry in entries:
        clean_url, path = normalize_url(entry.url)
        tokens = tokenize_slug(path)
        filtered_tokens = filter_tokens(tokens)
        action, obj = rule_infer(tokens, rule_actions, rule_objects)
        intent_category = derive_intent_category(action, obj) if action or obj else "unknown"
        records.append(
            IntentRecord(
                url=clean_url,
                path=path,
                path_depth=path_depth(path),
                slug_tokens=tokens,
                filtered_tokens=filtered_tokens,
                action=action,
                object=obj,
                scene="",
                intent_category=intent_category,
                notes="",
                lastmod=entry.lastmod,
            )
        )
    return records


def _render_batch_prompt(batch: List[IntentRecord]) -> str:
    items = []
    for rec in batch:
        items.append(
            {
                "url": rec.url,
                "path": rec.path,
                "slug_tokens": rec.slug_tokens,
                "rule_action": rec.action,
                "rule_object": rec.object,
            }
        )
    return json.dumps(items, ensure_ascii=False)


def enrich_with_llm(
    records: List[IntentRecord],
    llm_config: Dict[str, Any],
    verbose: bool = False,
) -> None:
    if not llm_config.get("enabled") or not llm_config.get("model"):
        return
    try:
        from openai import OpenAI
    except ImportError:
        print("openai package not installed; skipping LLM enrichment", file=sys.stderr)
        return

    client = OpenAI(
        api_key=llm_config.get("api_key") or None,
        base_url=llm_config.get("base_url") or None,
    )
    batch_size = max(1, int(llm_config.get("batch_size") or 20))

    for idx in range(0, len(records), batch_size):
        batch = records[idx : idx + batch_size]
        user_content = _render_batch_prompt(batch)
        messages = [
            {
                "role": "system",
                "content": (
                    "You classify sitemap URLs into action, object, scene, intent_category, and notes. "
                    "Only use URL/slug clues; avoid hallucinating meaning. "
                    'If uncertain, return "unknown". Respond with JSON array matching the input order.'
                ),
            },
            {
                "role": "user",
                "content": (
                    "Input items (JSON): "
                    + user_content
                    + " Return JSON like "
                    '[{"action":"enhance","object":"image","scene":"linkedin","intent_category":"linkedin-headshot","notes":"..."}]'
                ),
            },
        ]
        try:
            completion = client.chat.completions.create(
                model=llm_config["model"],
                messages=messages,
                temperature=0,
            )
        except Exception as exc:  # pragma: no cover - network
            print(f"LLM request failed: {exc}", file=sys.stderr)
            return

        content = completion.choices[0].message.content
        try:
            parsed = json.loads(content)
        except Exception as exc:  # pragma: no cover - parsing
            print(f"Failed to parse LLM response: {exc}", file=sys.stderr)
            if verbose:
                print(content, file=sys.stderr)
            return

        if not isinstance(parsed, list):
            print("LLM response is not a list; skipping this batch", file=sys.stderr)
            if verbose:
                print(content, file=sys.stderr)
            continue

        for rec, llm_item in zip(batch, parsed):
            if not isinstance(llm_item, dict):
                continue
            rec.action = llm_item.get("action") or rec.action
            rec.object = llm_item.get("object") or rec.object
            rec.scene = llm_item.get("scene") or rec.scene
            rec.intent_category = llm_item.get("intent_category") or rec.intent_category
            rec.notes = llm_item.get("notes") or rec.notes
            if not rec.intent_category:
                rec.intent_category = derive_intent_category(rec.action, rec.object)
            if not rec.intent_category:
                rec.intent_category = "unknown"


def clamp_records(records: List[IntentRecord], max_urls: int, sample_strategy: str) -> List[IntentRecord]:
    if len(records) <= max_urls:
        return records
    if sample_strategy == "random":
        return random.sample(records, max_urls)
    return records[:max_urls]


def summarize_by_intent(records: List[IntentRecord]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        key = rec.intent_category or "unknown"
        bucket = buckets.setdefault(key, {"intent_category": key, "url_count": 0, "sample_urls": []})
        bucket["url_count"] += 1
        if len(bucket["sample_urls"]) < 3:
            bucket["sample_urls"].append(rec.path)
    return sorted(buckets.values(), key=lambda x: x["url_count"], reverse=True)


# Heuristic helpers to make the table more readable without heavy LLM use.
ACTION_SYNONYMS = {
    "unblur": ["deblur", "sharpen", "clarify", "clear"],
    "enhance": ["improve", "boost", "refine", "enhancement", "enhancer"],
    "upscale": ["enlarge", "increase-resolution", "rescale", "upscaler", "resize"],
    "remove": ["erase", "delete", "strip", "remover", "removal"],
    "denoise": ["reduce-noise", "clean-noise", "clean"],
    "restore": ["repair", "fix", "recover", "restoration"],
    "convert": ["transform", "turn-into", "converter", "change"],
    "generate": ["create", "make", "produce", "generator", "creation", "maker"],
    "colorize": ["add-color", "recolor", "colour"],
    "blur": ["soften", "apply-blur", "blurred"],
    "fix": ["repair", "correct"],
    "sharpen": ["enhance-edges", "clarify"],
    "compress": ["shrink", "reduce-size", "compression"],
    "edit": ["editor", "modify", "change"],
}

OBJECT_SYNONYMS = {
    "image": ["photo", "picture", "pic", "images", "photos", "pictures", "pics", "jpg", "png"],
    "photo": ["image", "picture", "images", "photos", "pictures"],
    "picture": ["image", "photo", "images", "photos", "pictures"],
    "video": ["clip", "footage", "movie", "videos", "clips", "mp4"],
    "text": ["document", "copy", "txt", "pdf", "word"],
    "audio": ["sound", "voice", "mp3", "wav", "speech"],
    "background": ["bg", "backdrop"],
    "noise": ["grain"],
    "watermark": ["stamp", "logo-mark"],
    "headshot": ["portrait", "avatar", "face", "selfie"],
    "logo": ["brand-mark", "icon"],
    "resume": ["cv", "curriculum-vitae"],
}


def _heuristic_note(action: str, obj: str) -> str:
    tgt = obj or "content"
    action = action or ""
    if action == "unblur":
        return f"Make blurry {tgt} clear and readable."
    if action == "enhance":
        return f"Improve quality of the {tgt} (sharpness, contrast, detail)."
    if action == "upscale":
        return f"Increase resolution/size of the {tgt} without losing quality."
    if action == "remove":
        if obj == "background":
            return "Remove background for reuse/compositing the subject."
        return f"Remove unwanted parts or artifacts from the {tgt}."
    if action == "denoise":
        return f"Reduce noise/grain in the {tgt}."
    if action == "restore":
        return f"Restore damaged or old {tgt}."
    if action == "convert":
        return f"Convert the {tgt} between formats."
    if action == "generate":
        return f"Generate new {tgt} from prompts or source assets."
    if action == "colorize":
        return f"Add or fix color in the {tgt}."
    if action == "blur":
        return f"Apply blur to the {tgt} for focus or privacy."
    if action == "fix":
        return f"Fix defects in the {tgt}."
    if action == "sharpen":
        return f"Sharpen edges/details in the {tgt}."
    if obj:
        return f"{obj} related utility."
    return ""


def _related_keywords(action: str, obj: str, tokens: List[str]) -> List[str]:
    related: List[str] = []
    if action in ACTION_SYNONYMS:
        related.extend(ACTION_SYNONYMS[action])
    if obj in OBJECT_SYNONYMS:
        related.extend(OBJECT_SYNONYMS[obj])
    related.extend([t for t in tokens if t not in related])
    related = filter_tokens(related)
    seen = set()
    deduped = []
    for term in related:
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
    return deduped


def apply_heuristics(records: List[IntentRecord]) -> None:
    """
    Fill notes and related keywords heuristically if they are empty.
    """
    for rec in records:
        if not rec.notes:
            rec.notes = _heuristic_note(rec.action, rec.object)
        if not rec.filtered_tokens:
            rec.filtered_tokens = filter_tokens(rec.slug_tokens)
        rec.similar_keywords = _related_keywords(rec.action, rec.object, rec.filtered_tokens or rec.slug_tokens)


def summarize_by_action_object(records: List[IntentRecord]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for rec in records:
        key = (rec.action or "unknown", rec.object or "unknown")
        bucket = buckets.setdefault(
            key, {"action": key[0], "object": key[1], "url_count": 0, "sample_urls": []}
        )
        bucket["url_count"] += 1
        if len(bucket["sample_urls"]) < 3:
            bucket["sample_urls"].append(rec.path)
    return sorted(buckets.values(), key=lambda x: x["url_count"], reverse=True)
