import json
import base64
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from queue import Empty, Queue
from typing import Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, parse_qsl, quote_plus, unquote, urlencode, urlparse, urlunparse
from urllib.request import ProxyHandler, Request, build_opener
from xml.etree import ElementTree

from models import SearchResult

try:
    import trafilatura
except ImportError:
    trafilatura = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

NOISE_PATTERNS = [
    r"Atlas Copco homepage",
    r"Your browser is not supported.*?main content",
    r"\u60a8\u7684\u6d4f\u89c8\u5668\u4e0d\u53d7\u652f\u6301.*?Skip to main content",
    r"Skip to main content",
    r"Google Chrome Mozilla Firefox Microsoft Edge",
    r"Continue to main content",
    r"Cookie[s]? policy",
    r"Privacy Policy",
    r"\u6700\u65b0\u63a8\u8350\u6587\u7ae0.*?\u53d1\u5e03",
    r"CC\s*4\.0.*?\u7248\u6743\u58f0\u660e",
    r"\u786e\u5b9a\u4e0d\u518d\u5173\u6ce8\u6b64\u4eba\u5417",
    r"\u67e5\u770bTA\u7684\u6587\u7ae0",
    r"\u9996\u9875\s+\u767b\u5f55\s+\u6ce8\u518c",
]

SKIP_READ_DOMAINS = [
    "zhihu.com",
    "zhuanlan.zhihu.com",
]

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "spm",
    "utm",
}

HVAC_QUERY_TRANSLATIONS = {
    "\u70ed\u6cf5": "heat pump",
    "\u592a\u9633\u80fd": "solar energy",
    "\u7a7a\u8c03": "air conditioning HVAC",
    "\u5efa\u7b51\u8282\u80fd": "building energy efficiency",
    "\u70ed\u56de\u6536": "heat recovery",
    "\u51b7\u5374\u5854": "cooling tower",
    "\u5730\u70ed": "geothermal",
    "\u65b0\u98ce": "fresh air ventilation",
}

HVAC_INNOVATION_QUERY_HINTS = [
    "product innovation case study 2024 2025 2026",
    "commercial product pilot project datasheet 2024 2025 2026",
    "technology roadmap performance energy savings product launch",
]

HVAC_SPECIALIZED_QUERY_VARIANTS = [
    "HVAC AI predictive control product 2024 2025 2026",
    "heat recovery ventilation innovative product case study 2024 2025 2026",
    "solar thermal HVAC new product commercial building 2024 2025 2026",
    "renewable energy HVAC heat pump product launch 2024 2025 2026",
    "building energy management system AI product 2024 2025 2026",
    "hydronic transport smart pump HVAC product 2024 2025 2026",
    "building envelope adaptive facade energy saving product 2024 2025 2026",
]

HEAT_PUMP_QUERY_VARIANTS = [
    '"\u7a7a\u6c14\u6e90\u70ed\u6cf5" "\u9ad8\u6e29\u70ed\u6cf5" \u5de5\u4e1a\u4f59\u70ed \u4ea7\u54c1 \u6848\u4f8b 2024 2025 2026',
    '"\u9ad8\u6e29\u70ed\u6cf5" "\u5de5\u4e1a\u70ed\u6cf5" \u4ea7\u54c1\u624b\u518c \u6027\u80fd\u53c2\u6570 \u8282\u80fd',
    '"industrial heat pump" "waste heat recovery" product datasheet COP 2024 2025 2026',
    '"natural refrigerant heat pump" product case study 2024 2025 2026',
]

DEFAULT_SEARCH_VARIANT_LIMIT = 8
SEARCH_CANDIDATE_POOL_LIMIT = 50
SEARCH_WORKER_LIMIT = 4
SEARCH_SOURCE_WORKER_LIMIT = 4
DUCKDUCKGO_TIMEOUT_SECONDS = 4
BING_RSS_TIMEOUT_SECONDS = 5
BING_HTML_TIMEOUT_SECONDS = 8
SOGOU_TIMEOUT_SECONDS = 8
READ_ATTEMPT_LIMIT = 24
READ_WORKER_LIMIT = 6


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"}:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"}:
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            text = re.sub(r"\s+", " ", data).strip()
            if len(text) >= 8:
                self.parts.append(text)


@dataclass
class PageExtraction:
    content: str = ""
    content_length: int = 0
    title: str = ""
    published_at: str = ""
    author: str = ""
    read_status: str = "extract_failed"


def fetch_url(url: str, timeout: int = 12) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="ignore")


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_client_redirect_url(html: str) -> str:
    patterns = [
        r'window\.location\.replace\(["\']([^"\']+)["\']\)',
        r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            target = unescape(match.group(1)).strip()
            if target.startswith("http"):
                return target
    return ""


def remove_template_noise(text: str) -> str:
    cleaned = clean_text(text)
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def looks_like_template_noise(text: str) -> bool:
    lowered = text.lower()
    bad_hits = [
        "browser is not supported",
        "\u6d4f\u89c8\u5668\u4e0d\u53d7\u652f\u6301",
        "skip to main content",
        "google chrome mozilla firefox microsoft edge",
    ]
    return any(hit in lowered for hit in bad_hits)


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def normalize_ddg_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return unquote(target)
    return url


def normalize_bing_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "bing.com" not in parsed.netloc or not parsed.path.startswith("/ck/"):
        return url
    encoded = parse_qs(parsed.query).get("u", [""])[0]
    if not encoded:
        return url
    if encoded.startswith("a1"):
        encoded = encoded[2:]
    try:
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(encoded + padding).decode("utf-8", errors="ignore")
    except Exception:
        return url
    return decoded if decoded.startswith("http") else url


def expand_query(query: str) -> str:
    if "\u592a\u9633\u80fd" in query:
        return (
            "solar energy air conditioning HVAC building energy efficiency "
            "2024 2025 2026 product innovation case study commercial building"
        )
    extra = [
        quote_search_phrase(english)
        for word, english in HVAC_QUERY_TRANSLATIONS.items()
        if word in query
    ]
    return (
        f"{query} {' '.join(extra)} HVAC building energy efficiency "
        f"{' '.join(HVAC_INNOVATION_QUERY_HINTS)}"
    )


def quote_search_phrase(value: str) -> str:
    if " " in value and not (value.startswith('"') and value.endswith('"')):
        return f'"{value}"'
    return value


ProgressCallback = Callable[[str, int, int, int], None]


def search_web(
    query: str,
    search_top_n: int = 20,
    progress_callback: Optional[ProgressCallback] = None,
) -> List[SearchResult]:
    variants = build_query_variants(query)
    candidate_limit = max(search_top_n, SEARCH_CANDIDATE_POOL_LIMIT)
    per_query_limit = max(10, min(candidate_limit, 20))
    groups = search_query_variants_parallel(
        variants,
        per_query_limit,
        progress_callback,
        search_top_n,
    )
    merged_results = dedupe_results(merge_result_groups(groups))
    candidate_results = select_relevant_search_results(
        merged_results,
        query,
        candidate_limit,
    )
    results = stratified_sample_results(candidate_results, search_top_n)
    if progress_callback:
        progress_callback("search_done", len(variants), len(variants), len(results))
    return results


def search_query_variants_parallel(
    variants: List[str],
    per_query_limit: int,
    progress_callback: Optional[ProgressCallback] = None,
    progress_limit: Optional[int] = None,
) -> List[List[SearchResult]]:
    if not variants:
        return []

    groups: List[List[SearchResult]] = [[] for _ in variants]
    started_count = 0
    completed_count = 0
    event_queue: Queue = Queue()
    worker_count = min(SEARCH_WORKER_LIMIT, len(variants))

    def run_search(index: int, variant: str) -> List[SearchResult]:
        if progress_callback:
            event_queue.put(("search_start", index))
        return search_single_query(variant, per_query_limit)

    def drain_progress_events() -> None:
        nonlocal started_count
        if not progress_callback:
            return
        while True:
            try:
                phase, _index = event_queue.get_nowait()
            except Empty:
                return
            if phase == "search_start":
                started_count += 1
                active_count = min(started_count - completed_count, worker_count)
                progress_callback("search_start", started_count, len(variants), active_count)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {
            executor.submit(run_search, index, variant): index
            for index, variant in enumerate(variants)
        }
        pending = set(future_to_index)
        while pending:
            drain_progress_events()
            done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
            drain_progress_events()
            for future in done:
                index = future_to_index[future]
                try:
                    groups[index] = future.result()
                except Exception:
                    groups[index] = []
                completed_count += 1
                if progress_callback:
                    found_count = len(dedupe_results(merge_result_groups(groups)))
                    if progress_limit is not None:
                        found_count = min(found_count, progress_limit)
                    progress_callback("search", completed_count, len(variants), found_count)
        drain_progress_events()
    return groups


def build_query_variants(query: str) -> List[str]:
    clean_query = clean_text(query) or "\u70ed\u6cf5"
    variants = [clean_query, expand_query(clean_query)]

    is_hvac_query = (
        "HVAC" in clean_query.upper()
        or "\u6696\u901a" in clean_query
        or "\u7a7a\u8c03" in clean_query
    )
    if is_hvac_query:
        variants.extend(
            [
                f"{clean_query} \u6696\u901a \u7a7a\u8c03 \u6280\u672f \u6587\u7ae0 \u6848\u4f8b",
                f"site:zhileng.com {clean_query} \u6696\u901a \u7a7a\u8c03 \u6280\u672f \u6587\u7ae0",
            ]
        )

    english_terms = [
        english for word, english in HVAC_QUERY_TRANSLATIONS.items() if word in clean_query
    ]
    if english_terms:
        english_query = " ".join(quote_search_phrase(term) for term in english_terms)
        variants.extend(
            [
                f"{clean_query} \u521b\u65b0\u6280\u672f \u4ea7\u54c1 \u6848\u4f8b 2024 2025 2026",
                f"{clean_query} \u4f01\u4e1a \u4ea7\u54c1\u624b\u518c \u6027\u80fd\u6307\u6807 \u8282\u80fd\u6548\u679c",
                f"{english_query} product launch case study 2024 2025 2026",
                f"{english_query} commercial product datasheet energy savings HVAC",
            ]
        )
    else:
        variants.extend(
            [
                f"{clean_query} HVAC product innovation case study 2024 2025 2026",
                f"{clean_query} commercial product performance energy savings",
            ]
        )

    if "\u592a\u9633\u80fd" in clean_query:
        variants.append("solar thermal HVAC new product commercial building 2024 2025 2026")
    if is_hvac_query:
        variants.append("HVAC AI predictive control product 2024 2025 2026")
    if "\u70ed\u56de\u6536" in clean_query or "recovery" in clean_query.lower():
        variants.append("heat recovery ventilation innovative product case study 2024 2025 2026")
    if "\u8f93\u9001" in clean_query or "\u8f93\u914d" in clean_query or "\u51b7\u70ed\u5a92" in clean_query:
        variants.append("hydronic transport smart pump HVAC product 2024 2025 2026")
    if "\u56f4\u62a4" in clean_query or "\u7ef4\u62a4\u7ed3\u6784" in clean_query:
        variants.append("building envelope adaptive facade energy saving product 2024 2025 2026")
    if "\u7cfb\u7edf\u7ba1\u7406" in clean_query or "\u7ba1\u7406" in clean_query:
        variants.append("building energy management system AI product 2024 2025 2026")
    if "\u53ef\u518d\u751f" in clean_query:
        variants.append("renewable energy HVAC heat pump product launch 2024 2025 2026")

    is_heat_pump_query = "\u70ed\u6cf5" in clean_query or "heat pump" in clean_query.lower()
    if is_heat_pump_query:
        variants.extend(HEAT_PUMP_QUERY_VARIANTS)
    else:
        variants.extend(HVAC_SPECIALIZED_QUERY_VARIANTS[:2])
    return unique_strings(variants)[:DEFAULT_SEARCH_VARIANT_LIMIT]


def unique_strings(values: List[str]) -> List[str]:
    kept = []
    seen = set()
    for value in values:
        cleaned = clean_text(value)
        key = cleaned.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(cleaned)
    return kept


def search_single_query(search_query: str, search_top_n: int) -> List[SearchResult]:
    source_tasks = [
        lambda: search_bing_rss(search_query, search_top_n),
        lambda: search_bing_html(search_query, search_top_n),
        lambda: search_sogou_html(search_query, search_top_n),
        lambda: search_duckduckgo_html(search_query, search_top_n),
    ]
    groups = []
    worker_count = min(SEARCH_SOURCE_WORKER_LIMIT, len(source_tasks))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(task) for task in source_tasks]
        for future in as_completed(futures):
            try:
                groups.append(future.result())
            except Exception:
                groups.append([])
    return merge_results(groups, search_top_n)


def search_duckduckgo_html(search_query: str, search_top_n: int) -> List[SearchResult]:
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(search_query)
    try:
        html = fetch_url(url, timeout=DUCKDUCKGO_TIMEOUT_SECONDS)
        return parse_duckduckgo_html(html, search_top_n)
    except Exception:
        return []


def select_relevant_search_results(
    results: List[SearchResult],
    query: str,
    limit: int,
) -> List[SearchResult]:
    if limit <= 0:
        return []

    from ranker import (
        calculate_topic_relevance,
        has_hvac_context,
        is_homepage_url,
        is_invalid,
        query_requires_hvac_context,
    )

    classify_results(results)
    requires_hvac = query_requires_hvac_context(query)
    scored = []
    for index, result in enumerate(results):
        if is_invalid(result):
            continue
        topic_score = calculate_topic_relevance(result, query)
        has_context = has_hvac_context(result)
        if requires_hvac and not has_context and topic_score < 4.0:
            continue
        if not requires_hvac and not has_context and topic_score < 1.5:
            continue

        score = (
            topic_score * 2.0
            + result.source_reliability_score
            + (2.0 if has_context else 0.0)
            - (1.5 if is_homepage_url(result.url) else 0.0)
            - (0.5 * result.source_tier)
        )
        scored.append((score, index, result))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [result for _, _, result in scored[:limit]]


def merge_result_groups(groups: List[List[SearchResult]]) -> List[SearchResult]:
    merged = []
    for group in groups:
        merged.extend(group)
    return merged


def merge_results(groups: List[List[SearchResult]], limit: int) -> List[SearchResult]:
    return dedupe_results(merge_result_groups(groups))[:limit]


def normalize_result_url(url: str) -> str:
    normalized = normalize_ddg_url(url).strip()
    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        return normalized.split("#", 1)[0]

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_PARAMS:
            continue
        query_items.append((key, value))

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query_items, doseq=True),
            "",
        )
    )


def dedupe_results(results: List[SearchResult]) -> List[SearchResult]:
    deduped = []
    seen = set()
    for result in results:
        key = normalize_result_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def stratified_sample_results(
    results: List[SearchResult],
    limit: int,
    tier_minimums: Optional[Dict[int, int]] = None,
) -> List[SearchResult]:
    if limit <= 0:
        return []
    if len(results) <= limit:
        classify_results(results)
        return results

    classify_results(results)
    tier_minimums = tier_minimums or default_tier_minimums(limit)
    buckets = {1: [], 2: [], 3: []}
    for result in results:
        buckets.get(result.source_tier, buckets[3]).append(result)

    selected = []
    selected_ids = set()
    weak_cap = max(1, limit // 4)

    def add(result: SearchResult) -> None:
        if id(result) in selected_ids or len(selected) >= limit:
            return
        selected.append(result)
        selected_ids.add(id(result))

    for tier in [1, 2, 3]:
        for result in buckets[tier][: tier_minimums.get(tier, 0)]:
            add(result)

    for result in results:
        if result.source_tier != 3:
            add(result)

    weak_count = sum(1 for result in selected if result.source_tier == 3)
    for result in results:
        if result.source_tier != 3 or weak_count >= weak_cap:
            continue
        before = len(selected)
        add(result)
        if len(selected) > before:
            weak_count += 1

    for result in results:
        add(result)

    return selected


def default_tier_minimums(limit: int) -> Dict[int, int]:
    if limit >= 10:
        return {1: 3, 2: 3, 3: 1}
    if limit >= 5:
        return {1: 2, 2: 2, 3: 1}
    if limit >= 3:
        return {1: 1, 2: 1, 3: 1}
    return {1: 1, 2: 1, 3: 0}


def classify_results(results: List[SearchResult]) -> None:
    from ranker import classify_source

    for result in results:
        classify_source(result)


def parse_duckduckgo_html(html: str, search_top_n: int) -> List[SearchResult]:
    blocks = re.findall(
        r'<div class="result results_links.*?</div>\s*</div>\s*</div>',
        html,
        re.S,
    )
    if not blocks:
        blocks = re.findall(r'<h2 class="result__title">.*?</div>\s*</div>', html, re.S)

    results = []
    seen = set()
    for block in blocks:
        title_match = re.search(r'class="result__a" href="([^"]+)">(.*?)</a>', block, re.S)
        if not title_match:
            continue
        raw_url = unescape(title_match.group(1))
        title = clean_text(re.sub(r"<.*?>", "", title_match.group(2)))
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(.*?)</a>|class="result__snippet"[^>]*>(.*?)</div>',
            block,
            re.S,
        )
        snippet_html = ""
        if snippet_match:
            snippet_html = snippet_match.group(1) or snippet_match.group(2) or ""
        snippet = clean_text(re.sub(r"<.*?>", "", snippet_html))
        target = normalize_ddg_url(raw_url.strip())
        if not target.startswith("http"):
            continue
        key = target.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        results.append(
            SearchResult(
                title=title,
                url=target,
                domain=domain_of(target),
                snippet=snippet,
            )
        )
        if len(results) >= search_top_n:
            break
    return results


def search_bing_html(search_query: str, search_top_n: int) -> List[SearchResult]:
    count = min(max(search_top_n, 10), 20)
    urls = [
        "https://www.bing.com/search?q=" + quote_plus(search_query) + f"&count={count}",
        "https://www.bing.com/search?q=" + quote_plus(search_query) + f"&count={count}&ensearch=1",
    ]
    groups = []
    for url in urls:
        try:
            html = fetch_url(url, timeout=BING_HTML_TIMEOUT_SECONDS)
            groups.append(parse_bing_html(html, search_top_n))
        except Exception:
            continue
    return merge_results(groups, search_top_n)


def parse_bing_html(html: str, search_top_n: int) -> List[SearchResult]:
    blocks = re.findall(r'<li class="b_algo".*?</li>', html, re.S)
    results = []
    seen = set()
    for block in blocks:
        title_match = re.search(r'<h2.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not title_match:
            continue
        target = normalize_bing_url(unescape(title_match.group(1)).strip())
        title = clean_text(re.sub(r"<.*?>", "", title_match.group(2)))
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        snippet = ""
        if snippet_match:
            snippet = clean_text(re.sub(r"<.*?>", "", snippet_match.group(1)))
        if not title or not target.startswith("http"):
            continue
        key = target.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        results.append(
            SearchResult(
                title=title,
                url=target,
                domain=domain_of(target),
                snippet=snippet,
            )
        )
        if len(results) >= search_top_n:
            break
    return results


def search_bing_rss(search_query: str, search_top_n: int) -> List[SearchResult]:
    url = "https://www.bing.com/search?format=rss&q=" + quote_plus(search_query)
    xml_text = fetch_url(url, timeout=BING_RSS_TIMEOUT_SECONDS)
    root = ElementTree.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    results = []
    seen = set()
    for item in channel.findall("item"):
        title = clean_text(item.findtext("title") or "")
        link = clean_text(item.findtext("link") or "")
        snippet = clean_text(item.findtext("description") or "")
        if not title or not link.startswith("http"):
            continue
        key = link.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        results.append(
            SearchResult(
                title=title,
                url=link,
                domain=domain_of(link),
                snippet=snippet,
            )
        )
        if len(results) >= search_top_n:
            break
    return results


def search_sogou_html(search_query: str, search_top_n: int) -> List[SearchResult]:
    url = "https://www.sogou.com/web?query=" + quote_plus(search_query)
    html = fetch_url(url, timeout=SOGOU_TIMEOUT_SECONDS)
    return parse_sogou_html(html, search_top_n)


def parse_sogou_html(html: str, search_top_n: int) -> List[SearchResult]:
    blocks = re.findall(r'<div class="vrwrap".*?(?=<div class="vrwrap"|$)', html, re.S)
    if not blocks:
        blocks = re.findall(r'<div class="results".*?(?=<div class="results"|$)', html, re.S)

    results = []
    seen = set()
    for block in blocks:
        title_match = re.search(r'<h3[^>]*class="[^"]*vr-title[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not title_match:
            title_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not title_match:
            continue
        raw_url = unescape(title_match.group(1)).strip()
        title = clean_text(
            re.sub(
                r"<!--red_beg-->|<!--red_end-->|<em>|</em>|<.*?>",
                "",
                title_match.group(2),
            )
        )
        snippet_match = re.search(r'<div[^>]+class="[^"]*(?:text-layout|str-text-info|fz-mid desc)[^"]*"[^>]*>(.*?)</div>', block, re.S)
        snippet = ""
        if snippet_match:
            snippet = clean_text(re.sub(r"<.*?>", "", snippet_match.group(1)))
        if raw_url.startswith("/"):
            target = "https://www.sogou.com" + raw_url
        else:
            target = raw_url
        if not title or not target.startswith("http"):
            continue
        key = target.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        results.append(
            SearchResult(
                title=title,
                url=target,
                domain=domain_of(target),
                snippet=snippet,
            )
        )
        if len(results) >= search_top_n:
            break
    return results


def extract_page_text_fallback(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    text = remove_template_noise(" ".join(parser.parts))
    return text[:6000]


def build_page_extraction(
    content: str,
    read_status: str,
    title: str = "",
    published_at: str = "",
    author: str = "",
) -> PageExtraction:
    content = remove_template_noise(content or "")[:6000]
    return PageExtraction(
        content=content,
        content_length=len(content),
        title=clean_text(title or ""),
        published_at=clean_text(published_at or ""),
        author=clean_text(author or ""),
        read_status=read_status,
    )


def extract_with_trafilatura(html: str, url: str = "") -> PageExtraction:
    if trafilatura is None:
        return PageExtraction(read_status="trafilatura_unavailable")

    extracted = trafilatura.extract(
        html,
        url=url or None,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_tables=False,
    )
    if not extracted:
        return PageExtraction(read_status="empty_content")

    data = json.loads(extracted)
    content = data.get("text") or ""
    if not content.strip():
        return PageExtraction(read_status="empty_content")

    return build_page_extraction(
        content,
        "trafilatura_success",
        title=data.get("title") or "",
        published_at=data.get("date") or "",
        author=data.get("author") or "",
    )


def extract_page_data(html: str, url: str = "") -> PageExtraction:
    read_status = "extract_failed"
    try:
        extracted = extract_with_trafilatura(html, url)
        read_status = extracted.read_status
        if extracted.content.strip():
            return extracted
    except Exception:
        read_status = "trafilatura_error"

    content = extract_page_text_fallback(html)
    if content.strip():
        return build_page_extraction(content, "fallback_success")
    return PageExtraction(read_status=read_status)


def extract_page_text(html: str) -> str:
    return extract_page_data(html).content


def read_result_pages(
    results: List[SearchResult],
    read_top_k: int = 8,
    progress_callback: Optional[ProgressCallback] = None,
) -> None:
    selected_results = select_read_candidates(results, read_top_k)
    total = len(selected_results)
    if not selected_results:
        return

    completed_count = 0
    worker_count = min(READ_WORKER_LIMIT, len(selected_results))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(read_single_result_page, result) for result in selected_results]
        for future in as_completed(futures):
            completed_count += 1
            try:
                future.result()
            except Exception:
                pass
            if progress_callback:
                progress_callback(
                    "read",
                    completed_count,
                    total,
                    sum(1 for item in results if item.read_success),
                )


def read_single_result_page(result: SearchResult) -> None:
    if should_skip_read(result.domain):
        result.read_status = "skipped"
        result.read_error = "site blocks automated reading; using search snippet"
        return
    try:
        html = fetch_url(result.url)
        redirect_url = extract_client_redirect_url(html)
        if redirect_url:
            result.url = redirect_url
            result.domain = domain_of(redirect_url)
            html = fetch_url(redirect_url)
        extracted = extract_page_data(html, result.url)
        if len(extracted.content) < 120 or looks_like_template_noise(extracted.content):
            result.content_length = extracted.content_length
            result.published_at = extracted.published_at
            result.author = extracted.author
            result.read_status = "empty_content"
            result.read_error = "content too short, noisy, or unreadable"
            return
        result.content = extracted.content
        result.content_length = extracted.content_length
        result.published_at = extracted.published_at
        result.author = extracted.author
        result.read_status = extracted.read_status
        if extracted.title and not result.title.strip():
            result.title = extracted.title
        result.read_success = True
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        result.read_status = "extract_failed"
        result.read_error = type(exc).__name__
    except Exception as exc:
        result.read_status = "extract_failed"
        result.read_error = type(exc).__name__


def select_read_candidates(results: List[SearchResult], read_top_k: int) -> List[SearchResult]:
    if read_top_k <= 0:
        return []

    sampled = stratified_sample_results(results, min(len(results), max(read_top_k, READ_ATTEMPT_LIMIT)))

    def read_priority(result: SearchResult) -> tuple:
        domain = result.domain.lower()
        skip = should_skip_read(domain)
        likely_blocked = domain in {"baike.baidu.com", "baidu.com"} or domain.endswith(".baidu.com")
        has_snippet = bool(result.snippet.strip())
        return (
            1 if skip else 0,
            1 if likely_blocked else 0,
            0 if has_snippet else 1,
            result.source_tier,
        )

    return sorted(sampled, key=read_priority)[: min(len(sampled), max(read_top_k, READ_ATTEMPT_LIMIT))]


def should_skip_read(domain: str) -> bool:
    domain = domain.lower()
    return any(domain == blocked or domain.endswith("." + blocked) for blocked in SKIP_READ_DOMAINS)
