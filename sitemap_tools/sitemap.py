import random
import time
import urllib.parse
import urllib.request
import urllib.error
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


def _fetch_url(
    url: str,
    timeout: int,
    user_agent: str,
    retries: int = 3,
    extra_user_agents: Optional[List[str]] = None,
) -> str:
    delay_base = 1.0
    all_agents = [user_agent]
    if extra_user_agents:
        all_agents.extend(extra_user_agents)

    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(delay_base * (2 ** (attempt - 1)) + random.uniform(0, 1))

        current_agent = random.choice(all_agents)
        req = urllib.request.Request(url, headers={"User-Agent": current_agent})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            # 403 Forbidden, 429 Too Many Requests, 5xx Server Error -> Retry
            if e.code in {403, 429, 500, 502, 503, 504}:
                continue
            # For 404 etc, raise immediately
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")


def _read_source(
    source: str,
    timeout: int,
    user_agent: str,
    retries: int = 0,
    extra_user_agents: Optional[List[str]] = None,
) -> str:
    if _is_http_url(source):
        return _fetch_url(source, timeout=timeout, user_agent=user_agent, retries=retries, extra_user_agents=extra_user_agents)
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
    user_agent: str,
    delay: float,
    seen: Set[str],
    retries: int = 0,
    extra_user_agents: Optional[List[str]] = None,
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
        try:
            xml_text = _read_source(
                loc_text,
                timeout=timeout,
                user_agent=user_agent,
                retries=retries,
                extra_user_agents=extra_user_agents,
            )
            entries.extend(
                parse_sitemap_xml(
                    xml_text,
                    timeout,
                    user_agent,
                    delay,
                    seen,
                    retries=retries,
                    extra_user_agents=extra_user_agents,
                )
            )
        except Exception as e:
            # Determine if we should be verbose here? For now just skip
            pass
    return entries


def parse_sitemap_xml(
    xml_text: str,
    timeout: int,
    user_agent: str,
    delay: float,
    seen: Optional[Set[str]] = None,
    retries: int = 0,
    extra_user_agents: Optional[List[str]] = None,
) -> List[SitemapEntry]:
    seen = seen or set()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tag_lower = root.tag.lower()
    if tag_lower.endswith("sitemapindex"):
        return _parse_sitemapindex(
            root,
            timeout=timeout,
            user_agent=user_agent,
            delay=delay,
            seen=seen,
            retries=retries,
            extra_user_agents=extra_user_agents,
        )
    return _parse_urlset(root)


def load_sitemaps(
    sources: Iterable[str],
    timeout: int,
    user_agent: str,
    delay: float,
    retries: int = 0,
    extra_user_agents: Optional[List[str]] = None,
) -> List[SitemapEntry]:
    entries: Dict[str, SitemapEntry] = {}
    seen_sitemaps: Set[str] = set()
    for src in sources:
        try:
            xml_text = _read_source(
                src,
                timeout=timeout,
                user_agent=user_agent,
                retries=retries,
                extra_user_agents=extra_user_agents,
            )
            for entry in parse_sitemap_xml(
                xml_text,
                timeout=timeout,
                user_agent=user_agent,
                delay=delay,
                seen=seen_sitemaps,
                retries=retries,
                extra_user_agents=extra_user_agents,
            ):
                if entry.url not in entries:
                    entries[entry.url] = entry
        except Exception:
            # Skip failed sitemaps in the list
            pass
    return list(entries.values())


def normalize_url(url: str) -> Tuple[str, str]:
    """
    Strip query/fragment, ensure leading slash in path.
    Returns (clean_url, path).
    """
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    
    clean = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    return clean, path


def discover_sitemaps(
    domain_url: str,
    timeout: int = 10,
    user_agent: str = "SitemapTools/0.1",
    retries: int = 3,
    extra_user_agents: Optional[List[str]] = None,
) -> List[str]:
    """
    Attempt to discover sitemaps via robots.txt and common paths.
    """
    discovered: Set[str] = set()
    base = domain_url.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base

    # 1. Check robots.txt
    robots_url = f"{base}/robots.txt"
    try:
        content = _read_source(
            robots_url,
            timeout=timeout,
            user_agent=user_agent,
            retries=retries,
            extra_user_agents=extra_user_agents,
        )
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    sitemap_url = parts[1].strip()
                    if sitemap_url:
                        discovered.add(sitemap_url)
    except Exception:
        pass

    # 2. Check common paths if robots.txt didn't yield results (or always?)
    # Let's always check common paths as a fallback/augment
    common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap.txt"]
    for path in common_paths:
        url = f"{base}{path}"
        if url in discovered:
            continue
        try:
            # We just try to read it; if it fails (404), we skip.
            # _read_source raises on 4xx/5xx usually (via _fetch_url logic we added)
            _read_source(
                url,
                timeout=timeout,
                user_agent=user_agent,
                retries=0, # Don't retry too hard on guesses
                extra_user_agents=extra_user_agents,
            )
            discovered.add(url)
        except Exception:
            pass

    return list(discovered)
