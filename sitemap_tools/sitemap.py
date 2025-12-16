import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass
class SitemapEntry:
    url: str
    lastmod: Optional[str] = None


def _is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlsplit(value)
    return parsed.scheme in {"http", "https"}


def _fetch_url(url: str, timeout: int, user_agent: Optional[str]) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent or "SitemapTools/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _read_source(source: str, timeout: int, user_agent: Optional[str]) -> str:
    if _is_http_url(source):
        return _fetch_url(source, timeout=timeout, user_agent=user_agent)
    with open(source, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_urlset(root: ET.Element) -> List[SitemapEntry]:
    entries: List[SitemapEntry] = []
    for url_el in root.findall(".//{*}url"):
        loc_el = url_el.find("{*}loc")
        if loc_el is None or not loc_el.text:
            continue
        loc_text = loc_el.text.strip()
        lastmod_el = url_el.find("{*}lastmod")
        lastmod = lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None
        entries.append(SitemapEntry(url=loc_text, lastmod=lastmod))
    return entries


def _parse_sitemapindex(
    root: ET.Element,
    timeout: int,
    user_agent: Optional[str],
    delay: float,
    seen: Set[str],
) -> List[SitemapEntry]:
    entries: List[SitemapEntry] = []
    for sm_el in root.findall(".//{*}sitemap"):
        loc_el = sm_el.find("{*}loc")
        if loc_el is None or not loc_el.text:
            continue
        loc_text = loc_el.text.strip()
        if loc_text in seen:
            continue
        seen.add(loc_text)
        time.sleep(delay)
        xml_text = _read_source(loc_text, timeout=timeout, user_agent=user_agent)
        entries.extend(parse_sitemap_xml(xml_text, timeout, user_agent, delay, seen))
    return entries


def parse_sitemap_xml(
    xml_text: str,
    timeout: int,
    user_agent: Optional[str],
    delay: float,
    seen: Optional[Set[str]] = None,
) -> List[SitemapEntry]:
    seen = seen or set()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tag_lower = root.tag.lower()
    if tag_lower.endswith("sitemapindex"):
        return _parse_sitemapindex(root, timeout=timeout, user_agent=user_agent, delay=delay, seen=seen)
    return _parse_urlset(root)


def load_sitemaps(
    sources: Iterable[str],
    timeout: int,
    user_agent: Optional[str],
    delay: float,
) -> List[SitemapEntry]:
    entries: Dict[str, SitemapEntry] = {}
    seen_sitemaps: Set[str] = set()
    for src in sources:
        xml_text = _read_source(src, timeout=timeout, user_agent=user_agent)
        for entry in parse_sitemap_xml(xml_text, timeout=timeout, user_agent=user_agent, delay=delay, seen=seen_sitemaps):
            if entry.url not in entries:
                entries[entry.url] = entry
    return list(entries.values())


def normalize_url(url: str) -> Tuple[str, str]:
    """
    Strip query/fragment, ensure leading slash in path.
    Returns (clean_url, path).
    """
    parsed = urllib.parse.urlsplit(url)
    clean = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return clean, path
