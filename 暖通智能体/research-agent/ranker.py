import re
from datetime import datetime
from typing import Iterable, List

from models import SearchResult


BAD_PATTERNS = [
    "login",
    "signin",
    "register",
    "search?",
    "/search/",
    "\u5e7f\u544a",
    "\u76ee\u5f55",
    "\u5bfc\u822a",
    "\u82f1\u8bed\u5355\u8bcd",
    "\u662f\u4ec0\u4e48\u610f\u601d",
    "\u7ffb\u8bd1",
    "\u8bcd\u5178",
    "\u5c55\u5546",
    "\u5c55\u5546\u540d\u5355",
    "\u53c2\u5c55",
    "\u5c55\u4f1a",
    "\u535a\u89c8\u4f1a",
    "\u540d\u5355",
    "\u4f9b\u5e94\u5546\u540d\u5f55",
    "\u5382\u5546\u76ee\u5f55",
    "\u4f01\u4e1a\u540d\u5f55",
    "expo",
    "exhibitor",
    "exhibitors",
    "directory",
    "catalog",
    "supplier list",
    "\u592a\u9633\u7cfb",
    "\u6052\u661f",
    "\u8868\u9762\u6e29\u5ea6",
    "dictionary",
    "definition",
    "login",
]

BAD_DOMAINS = [
    "dictionary.cambridge.org",
    "iciba.com",
    "it.stonybrook.edu",
    "starwalk.space",
    "nasachina.cn",
]

UNRELATED_DOMAIN_HINTS = [
    "wargaming.net",
    "wotheat.com",
]

UNRELATED_TEXT_HINTS = [
    "world of tanks",
    "free-to-play",
    "shooter",
    "tactical shooter",
    "vehicle shooter",
    "multiplayer combat",
    "tank combat",
    "games/",
]

AUTHORITATIVE_DOMAIN_HINTS = [
    ".gov",
    ".edu",
    "edu.cn",
    "ac.cn",
    "iea.org",
    "ashrae.org",
    "energy.gov",
    "nrel.gov",
    "ipcc.ch",
    "sciencedirect.com",
    "springer.com",
    "ieeexplore.ieee.org",
    "mdpi.com",
    "science.org",
    "nature.com",
]

AUTHORITATIVE_TEXT_HINTS = [
    "\u6807\u51c6",
    "\u62a5\u544a",
    "\u767d\u76ae\u4e66",
    "\u671f\u520a",
    "\u8bba\u6587",
    "\u7814\u7a76",
    "\u6307\u5357",
    "standard",
    "report",
    "white paper",
    "whitepaper",
    "journal",
    "paper",
    "proceedings",
    "guideline",
    "guide",
    ".pdf",
]

INDUSTRY_TEXT_HINTS = [
    "\u4ea7\u54c1",
    "\u624b\u518c",
    "\u6280\u672f\u8d44\u6599",
    "\u89e3\u51b3\u65b9\u6848",
    "\u5de5\u7a0b\u6848\u4f8b",
    "\u6848\u4f8b",
    "\u53c2\u6570",
    "product",
    "solution",
    "case",
    "manual",
    "datasheet",
    "brochure",
    "specification",
    "technical",
]

INNOVATION_TEXT_HINTS = [
    "\u521b\u65b0",
    "\u65b0\u6280\u672f",
    "\u6280\u672f\u8def\u7ebf",
    "\u4ea7\u54c1\u53d1\u5e03",
    "\u5546\u4e1a\u5316",
    "\u8bd5\u70b9",
    "\u793a\u8303\u5de5\u7a0b",
    "\u89e3\u51b3\u65b9\u6848",
    "\u767d\u76ae\u4e66",
    "\u4ea7\u54c1\u624b\u518c",
    "\u6027\u80fd\u6307\u6807",
    "\u8282\u80fd\u6548\u679c",
    "\u5e94\u7528\u573a\u666f",
    "innovation",
    "innovative",
    "technology roadmap",
    "product launch",
    "commercial",
    "commercialization",
    "pilot",
    "demonstration project",
    "case study",
    "datasheet",
    "white paper",
    "brochure",
    "performance",
    "energy savings",
]

BASIC_KNOWLEDGE_HINTS = [
    "\u662f\u4ec0\u4e48",
    "\u5b9a\u4e49",
    "\u539f\u7406",
    "\u57fa\u7840\u77e5\u8bc6",
    "\u5165\u95e8",
    "\u767e\u79d1",
    "\u6982\u8ff0",
    "\u5206\u7c7b",
    "what is",
    "definition",
    "principle",
    "basics",
    "overview",
    "introduction",
]

INDUSTRY_DOMAIN_HINTS = [
    "huawei.com",
    "haier.com",
    "atlascopco.com",
    "atlascopco.com.cn",
    "csisolar.com",
]

WEAK_DOMAINS = [
    "sohu.com",
    "sina.cn",
    "sina.com.cn",
    "163.com",
    "qq.com",
    "zhihu.com",
    "zhuanlan.zhihu.com",
    "xueqiu.com",
    "baike.baidu.com",
    "csdn.net",
    "jianshu.com",
    "toutiao.com",
    "weixin.qq.com",
]

WEAK_TEXT_HINTS = [
    "\u95ee\u7b54",
    "\u767e\u79d1",
    "\u65b0\u95fb",
    "\u8d44\u8baf",
    "\u8f6c\u8f7d",
    "\u81ea\u5a92\u4f53",
    "\u8bba\u575b",
    "\u535a\u5ba2",
    "\u6295\u8d44",
    "forum",
    "blog",
    "news",
    "media",
]

SOURCE_TIER_LABELS = {
    1: "\u6743\u5a01\u7814\u7a76\u6765\u6e90",
    2: "\u4ea7\u4e1a/\u4f01\u4e1a\u6765\u6e90",
    3: "\u8865\u5145\u5f31\u6765\u6e90",
}

TOPIC_TERMS = [
    "\u7a7a\u8c03",
    "\u5efa\u7b51",
    "\u8282\u80fd",
    "\u70ed\u6cf5",
    "\u592a\u9633\u80fd",
    "\u5236\u51b7",
    "\u4f9b\u6696",
    "\u4f4e\u78b3",
    "\u80fd\u6548",
    "hvac",
    "building",
    "energy",
    "efficiency",
    "heat pump",
    "solar",
    "photovoltaic",
    "pv",
    "renewable",
    "\u5149\u4f0f",
    "\u53ef\u518d\u751f\u80fd\u6e90",
    "\u56f4\u62a4\u7ed3\u6784",
    "\u7ef4\u62a4\u7ed3\u6784",
    "\u51b7\u70ed\u5a92\u8f93\u9001",
    "\u8f93\u914d",
    "\u70ed\u56de\u6536",
    "\u7cfb\u7edf\u7ba1\u7406",
    "building envelope",
    "hydronic",
    "heat recovery",
    "building management system",
]

HVAC_CONTEXT_TERMS = [
    "hvac",
    "暖通",
    "暖通空调",
    "空调",
    "空调系统",
    "供暖",
    "通风",
    "制冷",
    "冷热源",
    "新风",
    "楼宇自控",
    "建筑能源",
    "heating",
    "ventilation",
    "air conditioning",
    "refrigeration",
    "cooling",
    "building automation",
    "building energy",
]

HVAC_QUERY_TERMS = [
    "hvac",
    "暖通",
    "空调",
    "供暖",
    "通风",
    "制冷",
    "冷热源",
    "新风",
]

EXPLICIT_HVAC_FOCUS_TERMS = [
    "hvac",
    "暖通",
    "暖通空调",
    "供暖通风空调",
    "heating, ventilation and air conditioning",
    "heating ventilation air conditioning",
    "heating, ventilation, and air conditioning",
]

PORTAL_HOMEPAGE_HINTS = [
    "门户网站",
    "门户网",
    "信息交流平台",
    "行业门户",
    "首页",
    "立志成为",
    "original information",
    "portal",
]

KNOWLEDGE_TERMS = [
    "\u539f\u7406",
    "\u7ed3\u6784",
    "\u7ec4\u4ef6",
    "\u7cfb\u7edf",
    "\u6548\u7387",
    "\u80fd\u6548",
    "\u8282\u80fd",
    "\u80fd\u8017",
    "\u8fd0\u884c",
    "\u63a7\u5236",
    "\u8d1f\u8377",
    "\u5de5\u51b5",
    "\u6362\u70ed",
    "\u538b\u7f29\u673a",
    "\u84b8\u53d1\u5668",
    "\u51b7\u51dd\u5668",
    "\u70ed\u56de\u6536",
    "\u65b0\u98ce",
    "\u8f93\u914d",
    "\u51b7\u70ed\u6e90",
    "\u78b3\u6392\u653e",
    "principle",
    "system",
    "efficiency",
    "energy",
    "performance",
    "control",
    "load",
    "operation",
    "heat recovery",
    "compressor",
    "evaporator",
    "condenser",
]

LOW_INFO_TERMS = [
    "\u5c55\u5546",
    "\u5c55\u5546\u540d\u5355",
    "\u53c2\u5c55",
    "\u5c55\u4f1a",
    "\u535a\u89c8\u4f1a",
    "\u540d\u5355",
    "\u76ee\u5f55",
    "\u5382\u5546",
    "\u4f9b\u5e94\u5546",
    "\u8054\u7cfb\u6211\u4eec",
    "\u5c55\u4f4d",
    "expo",
    "exhibitor",
    "exhibitors",
    "directory",
    "catalog",
    "booth",
    "supplier",
]


def tokenize(query: str) -> List[str]:
    raw = re.split(r"[\s,;]+", query.strip())
    terms = [x for x in raw if x]
    if query.strip() and query.strip() not in terms:
        terms.insert(0, query.strip())
    return terms


def domain_matches(domain: str, hints: List[str]) -> bool:
    for hint in hints:
        if hint.startswith(".") and hint in domain:
            return True
        if domain == hint or domain.endswith("." + hint):
            return True
    return False


def source_text(result: SearchResult) -> str:
    return f"{result.title} {result.url} {result.snippet} {result.content[:1500]}".lower()


def source_header_text(result: SearchResult) -> str:
    return f"{result.title} {result.url} {result.snippet}".lower()


def has_topic_context(result: SearchResult) -> bool:
    text = source_text(result)
    return any(term.lower() in text for term in TOPIC_TERMS)


def query_requires_hvac_context(query: str) -> bool:
    lowered = (query or "").lower()
    return any(term.lower() in lowered for term in HVAC_QUERY_TERMS)


def is_broad_hvac_query(query: str) -> bool:
    lowered = (query or "").lower()
    return (
        ("hvac" in lowered or "暖通" in query or "暖通空调" in query)
        and "热泵" not in query
        and "heat pump" not in lowered
    )


def has_hvac_context(result: SearchResult) -> bool:
    text = source_text(result)
    return any(term.lower() in text for term in HVAC_CONTEXT_TERMS)


def has_explicit_hvac_focus(result: SearchResult) -> bool:
    text = source_text(result)
    return any(term.lower() in text for term in EXPLICIT_HVAC_FOCUS_TERMS)


def is_homepage_url(url: str) -> bool:
    path = re.sub(r"/+", "/", url.lower().split("?", 1)[0])
    return path.count("/") <= 2


def is_portal_homepage(result: SearchResult) -> bool:
    if not is_homepage_url(result.url):
        return False
    text = source_text(result)
    return any(term.lower() in text for term in PORTAL_HOMEPAGE_HINTS)


def is_unrelated_site(result: SearchResult) -> bool:
    domain = result.domain.lower()
    text = source_text(result)
    if any(domain == hint or domain.endswith("." + hint) for hint in UNRELATED_DOMAIN_HINTS):
        return True
    return any(term in text for term in UNRELATED_TEXT_HINTS) and not has_hvac_context(result)


def classify_source(result: SearchResult) -> None:
    domain = result.domain.lower()
    text = source_text(result)
    header_text = source_header_text(result)

    if domain_matches(domain, WEAK_DOMAINS) or domain.startswith("news.") or ".news." in domain:
        result.source_tier = 3
        result.source_type = "supplementary/weak"
        result.source_tier_label = SOURCE_TIER_LABELS[3]
        result.source_reliability_score = 2.0
        result.source_reason = "\u5a92\u4f53/\u95ee\u7b54/\u767e\u79d1\u7c7b\u5f31\u6765\u6e90\u57df\u540d"
        return

    if domain_matches(domain, AUTHORITATIVE_DOMAIN_HINTS):
        result.source_tier = 1
        result.source_type = "authoritative"
        result.source_tier_label = SOURCE_TIER_LABELS[1]
        result.source_reliability_score = 9.0
        result.source_reason = "\u653f\u5e9c/\u9ad8\u6821/\u884c\u4e1a\u7ec4\u7ec7/\u671f\u520a\u7c7b\u57df\u540d"
        return

    if any(hint in header_text for hint in AUTHORITATIVE_TEXT_HINTS) and has_topic_context(result):
        result.source_tier = 1
        result.source_type = "authoritative"
        result.source_tier_label = SOURCE_TIER_LABELS[1]
        result.source_reliability_score = 8.0
        result.source_reason = "\u6807\u9898\u6216\u8def\u5f84\u5305\u542b\u62a5\u544a/\u6807\u51c6/\u8bba\u6587\u7279\u5f81"
        return

    if domain_matches(domain, INDUSTRY_DOMAIN_HINTS):
        result.source_tier = 2
        result.source_type = "industry/enterprise"
        result.source_tier_label = SOURCE_TIER_LABELS[2]
        result.source_reliability_score = 6.5
        result.source_reason = "\u5df2\u8bc6\u522b\u7684\u4f01\u4e1a\u5b98\u7f51\u57df\u540d"
        return

    if any(hint in header_text for hint in WEAK_TEXT_HINTS):
        result.source_tier = 3
        result.source_type = "supplementary/weak"
        result.source_tier_label = SOURCE_TIER_LABELS[3]
        result.source_reliability_score = 3.0
        result.source_reason = "\u6587\u672c\u5448\u73b0\u5a92\u4f53/\u535a\u5ba2/\u8d44\u8baf\u7279\u5f81"
        return

    if any(hint in text for hint in INDUSTRY_TEXT_HINTS):
        result.source_tier = 2
        result.source_type = "industry/enterprise"
        result.source_tier_label = SOURCE_TIER_LABELS[2]
        result.source_reliability_score = 6.5
        result.source_reason = "\u4ea7\u54c1/\u624b\u518c/\u89e3\u51b3\u65b9\u6848/\u6848\u4f8b\u7c7b\u7279\u5f81"
        return

    result.source_tier = 2
    result.source_type = "industry/enterprise"
    result.source_tier_label = SOURCE_TIER_LABELS[2]
    result.source_reliability_score = 5.0
    result.source_reason = "\u672a\u547d\u4e2d\u5f31\u6765\u6e90\uff0c\u6309\u666e\u901a\u4ea7\u4e1a\u7f51\u9875\u5904\u7406"


def source_type(domain: str) -> str:
    if domain_matches(domain.lower(), AUTHORITATIVE_DOMAIN_HINTS):
        return "authoritative"
    if domain_matches(domain.lower(), WEAK_DOMAINS):
        return "supplementary/weak"
    return "enterprise/media"


def is_invalid(result: SearchResult) -> bool:
    url = result.url.lower()
    title = result.title.strip()
    domain = result.domain.lower()
    if not title or len(title) < 4:
        return True
    if any(domain == bad or domain.endswith("." + bad) for bad in BAD_DOMAINS):
        return True
    if is_unrelated_site(result):
        return True
    if any(p in url or p in title.lower() for p in BAD_PATTERNS):
        return True
    if is_portal_homepage(result):
        return True
    combined = f"{title} {result.snippet} {result.content[:800]}".lower()
    if calculate_content_readability(result) < 2 and any(term in combined for term in LOW_INFO_TERMS):
        return True
    path = re.sub(r"/+", "/", url.split("?", 1)[0])
    if path.count("/") <= 2 and not result.snippet:
        return True
    return False


def clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 2)


def calculate_topic_relevance(result: SearchResult, query: str) -> float:
    terms = tokenize(query)
    hay_title = result.title.lower()
    hay_snippet = result.snippet.lower()
    hay_content = result.content.lower()
    combined = f"{hay_title} {hay_snippet} {hay_content[:1500]}"
    score = 0.0
    matched = []

    for term in terms:
        t = term.lower()
        if t in hay_title:
            score += 4.0
            matched.append(term)
        if t in hay_snippet:
            score += 2.5
            matched.append(term)
        if result.read_success and t in hay_content:
            score += 1.5
            matched.append(term)

    topic_hits = [term for term in TOPIC_TERMS if term in combined]
    score += min(len(topic_hits), 8) * 0.35
    matched.extend(topic_hits[:5])

    if is_broad_hvac_query(query):
        if has_explicit_hvac_focus(result):
            score += 3.0
            matched.append("HVAC")
        elif "heat pump" in combined or "热泵" in combined:
            score -= 2.5

    innovation_hits = [term for term in INNOVATION_TEXT_HINTS if term.lower() in combined]
    score += min(len(innovation_hits), 6) * 0.55
    matched.extend(innovation_hits[:5])

    result.matched_terms = sorted(set(matched))
    return clamp_score(score)


def calculate_content_readability(result: SearchResult) -> float:
    text = f"{result.title} {result.snippet} {result.content[:2500]}".lower()
    knowledge_hits = sum(1 for term in KNOWLEDGE_TERMS if term.lower() in text)
    innovation_hits = sum(1 for term in INNOVATION_TEXT_HINTS if term.lower() in text)
    basic_hits = sum(1 for term in BASIC_KNOWLEDGE_HINTS if term.lower() in text)
    low_info_hits = sum(1 for term in LOW_INFO_TERMS if term.lower() in text)
    content_len = len(result.content.strip())

    score = 2.0 if result.snippet else 0.5
    score += min(knowledge_hits, 5) * 0.25
    score += min(innovation_hits, 8) * 0.75
    if content_len >= 800:
        score += 3.0
    elif content_len >= 300:
        score += 1.8
    elif content_len >= 120:
        score += 0.8
    elif result.read_success:
        score -= 1.0
    if result.read_success:
        score += 1.0
    if not result.read_success and len(result.snippet) < 80:
        score -= 1.5
    score -= min(low_info_hits, 5) * 1.4
    if basic_hits and innovation_hits == 0:
        score -= min(basic_hits, 4) * 0.9
    return clamp_score(score)


def calculate_innovation_product_fit(result: SearchResult) -> float:
    text = source_text(result)
    innovation_hits = sum(1 for term in INNOVATION_TEXT_HINTS if term.lower() in text)
    basic_hits = sum(1 for term in BASIC_KNOWLEDGE_HINTS if term.lower() in text)
    recent_hits = len(re.findall(r"\b202[4-6]\b", text))

    score = min(innovation_hits, 8) * 1.0 + min(recent_hits, 3) * 1.2
    if innovation_hits >= 2 and recent_hits:
        score += 1.2
    if basic_hits and innovation_hits == 0:
        score -= min(basic_hits, 4) * 1.0
    return clamp_score(score)


def parse_published_date(value: str):
    if not value:
        return None
    text = value.strip()
    patterns = [
        r"(?P<year>20\d{2}|19\d{2})[-/.年](?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})",
        r"(?P<year>20\d{2}|19\d{2})[-/.](?P<month>\d{1,2})",
        r"(?P<year>20\d{2}|19\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        year = int(match.group("year"))
        month = int(match.groupdict().get("month") or 1)
        day = int(match.groupdict().get("day") or 1)
        try:
            return datetime(year, month, day)
        except ValueError:
            return None
    return None


def calculate_freshness(result: SearchResult) -> float:
    published = parse_published_date(result.published_at)
    if not published:
        recent_years = re.findall(r"\b(202[4-6])\b", source_header_text(result))
        if recent_years:
            return 8.0
    if not published:
        return 5.0

    age_days = (datetime.now() - published).days
    if age_days < 0:
        return 5.0
    if age_days <= 365:
        return 10.0
    if age_days <= 365 * 3:
        return 8.0
    if age_days <= 365 * 5:
        return 6.0
    if age_days <= 365 * 10:
        return 4.0
    return 2.0


def build_ranking_reason(result: SearchResult) -> str:
    reasons = []
    if result.topic_relevance_score >= 8:
        reasons.append("主题高度匹配")
    elif result.topic_relevance_score >= 5:
        reasons.append("主题匹配度中等")
    elif result.read_success:
        reasons.append("主题匹配较弱")

    if result.source_reliability_score >= 8:
        reasons.append(f"来源为{result.source_tier_label}")
    elif result.source_reliability_score <= 3:
        reasons.append("来源可信度较低")
    else:
        reasons.append(f"来源为{result.source_tier_label}")

    if result.content_readability_score >= 7:
        reasons.append("正文信息较完整")
    elif result.content_readability_score < 3:
        reasons.append("正文可读性较低")

    if result.freshness_score >= 8:
        reasons.append("发布时间较新")
    elif result.freshness_score == 5:
        reasons.append("发布时间未知")
    elif result.freshness_score <= 4:
        reasons.append("发布时间较早")

    if getattr(result, "innovation_product_fit_score", 0) >= 7:
        reasons.append("包含创新技术或产品化信息")
    elif getattr(result, "innovation_product_fit_score", 0) <= 2:
        reasons.append("创新产品信息较少")

    return "，".join(reasons) + "。"


def score_result(result: SearchResult, query: str) -> float:
    classify_source(result)
    result.topic_relevance_score = calculate_topic_relevance(result, query)
    result.content_readability_score = calculate_content_readability(result)
    result.freshness_score = calculate_freshness(result)
    result.innovation_product_fit_score = calculate_innovation_product_fit(result)
    result.score = round(
        result.topic_relevance_score * 0.34
        + result.source_reliability_score * 0.30
        + result.content_readability_score * 0.16
        + result.freshness_score * 0.10
        + result.innovation_product_fit_score * 0.10,
        2,
    )
    result.ranking_reason = build_ranking_reason(result)
    return result.score


def rank_results(results: Iterable[SearchResult], query: str) -> List[SearchResult]:
    kept = []
    broad_hvac = is_broad_hvac_query(query)
    for result in results:
        if is_invalid(result):
            continue
        score_result(result, query)
        if query_requires_hvac_context(query) and not has_hvac_context(result):
            continue
        if broad_hvac and not has_explicit_hvac_focus(result) and ("热泵" in source_text(result) or "heat pump" in source_text(result)):
            continue
        if result.score >= 2.5 and result.content_readability_score >= 1.5:
            kept.append(result)
        elif (
            query_requires_hvac_context(query)
            and has_hvac_context(result)
            and not is_homepage_url(result.url)
            and result.topic_relevance_score >= 4.0
            and result.score >= 3.0
        ):
            kept.append(result)
    kept.sort(key=lambda x: (-x.score, x.source_tier))
    for idx, result in enumerate(kept, 1):
        result.rank = idx
    return kept
