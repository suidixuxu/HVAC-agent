import re
from typing import List

from models import SearchResult


NOISY_PHRASES = [
    "Atlas Copco homepage",
    "browser is not supported",
    "浏览器不受支持",
    "Skip to main content",
    "Google Chrome Mozilla Firefox Microsoft Edge",
]

NOISY_PATTERNS = [
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
    r"\d{1,2}:\d{2}",
    r"CC\s*4\.0|BY-SA|版权|版权声明|最新推荐|最新文章",
    r"首页|登录|注册|浏览器|关注此人|确定不再关注",
    r"查看TA的文章|科技领域优质创作者|Skip to main content",
]

DISCLAIMER_TERMS = [
    "免责声明",
    "仅供参考",
    "请以原文为准",
    "版权",
    "转载",
    "联系我们",
    "隐私政策",
    "cookie",
    "登录",
    "注册",
    "广告",
    "all rights reserved",
    "privacy policy",
    "terms of use",
]

KNOWLEDGE_TERMS = [
    "原理",
    "定义",
    "组件",
    "结构",
    "系统",
    "效率",
    "能效",
    "节能",
    "热量",
    "制热",
    "制冷",
    "冷凝器",
    "蒸发器",
    "压缩机",
    "换热",
    "余热",
    "碳排放",
    "建筑",
    "暖通",
    "HVAC",
    "COP",
    "SCOP",
    "heat pump",
    "energy",
    "efficiency",
]

TARGET_EVIDENCE_TERMS = [
    "产品",
    "产品发布",
    "产品手册",
    "解决方案",
    "案例",
    "工程案例",
    "示范工程",
    "试点",
    "商业化",
    "创新",
    "新技术",
    "技术路线",
    "企业",
    "项目",
    "性能指标",
    "节能效果",
    "应用场景",
    "白皮书",
    "手册",
    "参数",
    "product",
    "product launch",
    "solution",
    "case study",
    "pilot",
    "commercial",
    "commercialization",
    "innovation",
    "innovative",
    "technology roadmap",
    "datasheet",
    "brochure",
    "white paper",
    "performance",
    "energy savings",
]

BASIC_KNOWLEDGE_TERMS = [
    "是什么",
    "定义",
    "原理",
    "基础知识",
    "入门",
    "百科",
    "概述",
    "分类",
    "what is",
    "definition",
    "principle",
    "basics",
    "overview",
    "introduction",
]

FORBIDDEN_CONCLUSION_PHRASES = [
    "本回答仅供参考",
    "请以原文为准",
    "不能替代专业意见",
    "无法得出结论",
    "当前只能综合",
    "形成保守判断",
    "未在核心发现中出现",
    "不应被视为本次检索结论",
]

FORBIDDEN_FINDING_PHRASES = [
    "现有来源显示",
    "资料显示",
    "检索结果显示",
    "根据来源可知",
    "本回答仅供参考",
    "请以原文为准",
    "不能替代专业意见",
]

FORBIDDEN_FINDING_TONE_PHRASES = [
    "不能只用",
    "不能只看",
    "不能扩展",
    "不能",
    "不应",
    "不要",
    "并非",
    "错误地认为",
    "需要注意",
    "还应",
    "必须",
    "应当",
    "应先",
    "而不是",
]

HVAC_COMPONENT_TERMS = [
    "压缩机",
    "蒸发器",
    "冷凝器",
    "节流装置",
    "制冷剂",
    "控制系统",
    "冷水机组",
    "锅炉",
    "冷却塔",
    "水泵",
    "风机",
    "风机盘管",
    "空气处理机组",
    "新风机组",
    "管道",
    "风管",
    "阀门",
    "传感器",
]

HVAC_TYPE_TERMS = [
    "空气源",
    "水源",
    "地源",
    "余热源",
    "风冷",
    "水冷",
    "直膨式",
    "全空气",
    "全水",
    "空气-水",
    "定风量",
    "变风量",
    "一次泵",
    "二次泵",
]

HVAC_METRIC_TERMS = [
    "COP",
    "EER",
    "IPLV",
    "SCOP",
    "能效",
    "效率",
    "负荷",
    "流量",
    "温湿度",
    "压差",
    "换热效率",
    "运行稳定性",
]

HVAC_FACTOR_TERMS = [
    "气候条件",
    "负荷特性",
    "系统匹配",
    "控制策略",
    "运行工况",
    "维护状态",
    "设备选型",
    "热源温度",
    "冷源温度",
    "新风量",
]

TECHNOLOGY_KEYWORDS = [
    ("AI预测控制", ["AI预测控制", "AI predictive control", "predictive control", "model predictive control", "MPC"]),
    ("建筑能源管理系统", ["建筑能源管理", "building energy management", "BMS", "楼宇自控", "building automation"]),
    ("热回收通风", ["热回收通风", "热回收", "余热", "heat recovery ventilation", "heat recovery", "HRV", "ERV"]),
    ("智能水泵", ["智能水泵", "smart pump", "variable speed pump", "变频水泵"]),
    ("自适应围护结构", ["自适应围护", "adaptive facade", "building envelope", "围护结构"]),
    ("热泵系统", ["热泵", "建筑冷热源", "冷热源", "heat pump"]),
    ("太阳能暖通系统", ["solar thermal", "太阳能", "光热", "光伏"]),
    ("暖通空调（HVAC）系统", ["HVAC", "暖通", "空调系统", "heating", "ventilation", "air conditioning"]),
]

SCENARIO_KEYWORDS = [
    ("商业建筑", ["商业建筑", "commercial building", "commercial"]),
    ("住宅建筑", ["住宅", "residential"]),
    ("数据中心", ["数据中心", "data center"]),
    ("楼宇运行管理", ["楼宇", "building automation", "BMS", "建筑能源管理"]),
    ("冷热源与输配系统", ["冷水机组", "锅炉", "水泵", "风机", "hydronic", "冷热源", "输配"]),
]

EFFECT_KEYWORDS = [
    ("降低能耗", ["节能", "能耗降低", "energy savings", "energy use", "reduce energy"]),
    ("提升运行效率", ["效率", "能效", "efficiency", "performance", "优化"]),
    ("改善舒适性和室内空气品质", ["舒适", "IAQ", "室内空气", "温湿度"]),
    ("减少碳排放", ["碳排放", "carbon", "decarbonization", "低碳"]),
]

PRODUCT_KEYWORDS = [
    "产品",
    "解决方案",
    "平台",
    "系统",
    "产品手册",
    "案例",
    "试点",
    "示范工程",
    "product",
    "solution",
    "platform",
    "datasheet",
    "case study",
    "pilot",
]

HVAC_KNOWLEDGE_GROUPS = [
    ("设备部件", HVAC_COMPONENT_TERMS),
    ("系统类型", HVAC_TYPE_TERMS),
    ("评价指标", HVAC_METRIC_TERMS),
    ("影响因素", HVAC_FACTOR_TERMS),
]

SITE_KEYWORD_GROUPS = [
    ("供暖", ["供暖", "采暖", "heating"], "scope"),
    ("通风", ["通风", "ventilation"], "scope"),
    ("空调调节", ["空调", "空气调节", "air conditioning"], "scope"),
    ("制冷", ["制冷", "冷却", "cooling", "refrigeration"], "scope"),
    ("冷热源", ["冷热源", "冷源", "热源", "heating and cooling source", "cooling source"], "system"),
    ("空气侧系统", ["空气侧", "air-side", "air side"], "system"),
    ("水侧系统", ["水侧", "water-side", "water side", "hydronic"], "system"),
    ("控制系统", ["控制", "控制系统", "楼宇自控", "BMS", "control", "controls"], "controls"),
    ("商业建筑", ["商业建筑", "commercial building", "commercial"], "application"),
    ("数据中心", ["数据中心", "data center"], "application"),
    ("住宅建筑", ["住宅", "residential"], "application"),
    ("能效", ["能效", "效率", "energy efficiency", "efficiency"], "metrics"),
    ("EER", ["EER"], "metrics"),
    ("COP", ["COP"], "metrics"),
    ("负荷", ["负荷", "load"], "metrics"),
    ("压缩机", ["压缩机", "compressor"], "components"),
    ("水泵", ["水泵", "pump"], "components"),
    ("风机", ["风机", "fan"], "components"),
    ("冷水机组", ["冷水机组", "chiller"], "components"),
    ("冷却塔", ["冷却塔", "cooling tower"], "components"),
    ("热回收", ["热回收", "余热", "heat recovery", "energy recovery"], "energy"),
    ("新风处理", ["新风", "fresh air", "outdoor air"], "ventilation"),
    ("节能", ["节能", "降低能耗", "energy savings", "reduce energy"], "energy"),
]

ANGLE_PRIORITY = [
    "scope",
    "system",
    "application",
    "metrics",
    "components",
    "controls",
    "ventilation",
    "energy",
]


def short(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit]


def compact_chinese_spaces(text: str) -> str:
    text = " ".join((text or "").split())
    text = re.sub(r"[您你]可以", "可", text)
    text = re.sub(r"[您你]需要", "需", text)
    text = re.sub(r"[您你]应当", "应", text)
    text = re.sub(r"[您你]", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff，。；：、“”‘’（）])\s+(?=[\u4e00-\u9fffA-Za-z0-9“‘（])", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9])\s+(?=[\u4e00-\u9fff，。；：、“”‘’（）])", "", text)
    text = re.sub(r"\s+(?=[，。；：！？、）])", "", text)
    text = re.sub(r"(?<=[（])\s+", "", text)
    return text


def has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def contains_english_sentence(text: str) -> bool:
    return len(re.findall(r"[A-Za-z]{4,}", text or "")) >= 5


def matched_labels(text: str, keyword_groups: List[tuple]) -> List[str]:
    lowered = (text or "").lower()
    labels = []
    for label, terms in keyword_groups:
        if any(term.lower() in lowered for term in terms):
            labels.append(label)
    return labels


def has_product_signal(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term.lower() in lowered for term in PRODUCT_KEYWORDS)


def is_hvac_query(query: str) -> bool:
    lowered = (query or "").lower()
    return "hvac" in lowered or "暖通" in query or "暖通空调" in query


def is_heat_pump_query(query: str) -> bool:
    lowered = (query or "").lower()
    return "热泵" in query or "heat pump" in lowered


def has_explicit_hvac_focus(text: str) -> bool:
    return has_any(
        text,
        [
            "HVAC",
            "暖通",
            "暖通空调",
            "供暖通风空调",
            "heating, ventilation and air conditioning",
            "heating ventilation air conditioning",
            "heating, ventilation, and air conditioning",
        ],
    )


def years_in_text(text: str) -> List[str]:
    return sorted(set(re.findall(r"\b202[4-6]\b", text or "")))


def matched_terms(text: str, terms: List[str], limit: int = 4) -> List[str]:
    lowered = (text or "").lower()
    found = []
    for term in terms:
        if term.lower() in lowered and term not in found:
            found.append(term)
        if len(found) >= limit:
            break
    return found


def site_clean_sentences(result: SearchResult) -> List[str]:
    raw_text = " ".join([result.snippet, result.content])
    sentences = []
    seen = set()
    for sentence in split_sentences(raw_text):
        sentence = remove_disclaimer_text(sentence)
        if not sentence or is_noisy_sentence(sentence):
            continue
        key = compact_chinese_spaces(sentence)[:64]
        if key in seen:
            continue
        seen.add(key)
        sentences.append(sentence)
    return sentences


def keyword_frequency(text: str, terms: List[str]) -> int:
    lowered = (text or "").lower()
    return sum(len(re.findall(re.escape(term.lower()), lowered)) for term in terms)


def extract_site_keywords(query: str, result: SearchResult, limit: int = 8) -> List[dict]:
    text = normalize_text(" ".join([result.title, result.snippet, result.content]))
    scored = []
    for label, terms, angle in SITE_KEYWORD_GROUPS:
        count = keyword_frequency(text, terms)
        if count <= 0:
            continue
        score = count
        if any(term.lower() in result.title.lower() for term in terms):
            score += 2
        if query and any(term.lower() in query.lower() for term in terms):
            score += 2
        scored.append({"label": label, "terms": terms, "angle": angle, "score": score})
    scored.sort(key=lambda item: (-item["score"], ANGLE_PRIORITY.index(item["angle"]) if item["angle"] in ANGLE_PRIORITY else 99))
    selected = []
    angle_counts = {}
    for item in scored:
        angle = item["angle"]
        if angle_counts.get(angle, 0) >= 3:
            continue
        selected.append(item)
        angle_counts[angle] = angle_counts.get(angle, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def sentence_matches_keyword(sentence: str, keyword: dict) -> bool:
    lowered = sentence.lower()
    return any(term.lower() in lowered for term in keyword["terms"])


def collect_keyword_sentences(result: SearchResult, keywords: List[dict]) -> List[str]:
    sentences = site_clean_sentences(result)
    if not keywords:
        return [sentence for sentence in sentences if has_knowledge_signal(sentence)]
    matched = []
    for sentence in sentences:
        if any(sentence_matches_keyword(sentence, keyword) for keyword in keywords):
            matched.append(sentence)
    if matched:
        matched.sort(
            key=lambda sentence: -sum(
                keyword["score"] for keyword in keywords if sentence_matches_keyword(sentence, keyword)
            )
        )
        return matched
    return [sentence for sentence in sentences if has_knowledge_signal(sentence)]


def keywords_for_angle(keywords: List[dict], angle: str) -> List[str]:
    labels = []
    for keyword in keywords:
        if keyword["angle"] == angle and keyword["label"] not in labels:
            labels.append(keyword["label"])
    return labels


def choose_viewpoint_angle(keywords: List[dict], used_angles: set) -> str:
    angle_scores = {}
    for keyword in keywords:
        angle_scores[keyword["angle"]] = angle_scores.get(keyword["angle"], 0) + keyword["score"]
    if any(keyword["label"] == "热回收" for keyword in keywords) and "energy" not in used_angles:
        return "energy"
    for angle in ANGLE_PRIORITY:
        if angle in angle_scores and angle not in used_angles:
            return angle
    if angle_scores:
        return max(angle_scores, key=angle_scores.get)
    return "scope"


def build_site_viewpoint(query: str, result: SearchResult, keywords: List[dict], sentences: List[str], used_angles: set) -> str:
    angle = choose_viewpoint_angle(keywords, used_angles)
    labels = keywords_for_angle(keywords, angle)
    all_labels = [keyword["label"] for keyword in keywords]
    subject = "暖通空调（HVAC）系统" if is_hvac_query(query) and not is_heat_pump_query(query) else query
    if angle == "scope" and labels:
        title = f"{subject}在该来源中主要覆盖{'、'.join(labels[:4])}等环境调节环节"
    elif angle == "system" and labels:
        title = f"该来源将{subject}的系统边界集中在{'、'.join(labels[:4])}等协同环节"
    elif angle == "application" and labels:
        title = f"该来源强调{subject}在{'、'.join(labels[:3])}等场景中的应用"
    elif angle == "metrics" and labels:
        title = f"该来源围绕{'、'.join(labels[:4])}等指标评价{subject}的性能表现"
    elif angle == "components" and labels:
        title = f"该来源提到{subject}相关设备部件包括{'、'.join(labels[:4])}"
    elif angle == "controls" and labels:
        title = f"该来源将{'、'.join(labels[:3])}作为{subject}运行调节的重要内容"
    elif angle == "ventilation" and labels:
        title = f"该来源把{'、'.join(labels[:3])}作为{subject}空气侧处理的重要内容"
    elif angle == "energy" and labels:
        title = f"该来源围绕{'、'.join(labels[:3])}说明{subject}的能量利用与节能价值"
    elif all_labels:
        title = f"该来源关于{subject}的核心信息集中在{'、'.join(all_labels[:4])}"
    elif sentences:
        title = compact_chinese_spaces(short(sentences[0], 140))
    else:
        return ""
    reviewed = review_finding_title(query, title, " ".join(sentences))
    if reviewed:
        used_angles.add(angle)
    return reviewed


def support_evidence_from_sentences(sentences: List[str], keywords: List[dict]) -> str:
    if not sentences:
        return ""
    labels = [keyword["label"] for keyword in keywords[:5]]
    base = compact_chinese_spaces(short("；".join(sentences[:2]), 180)).strip("。；;，, ")
    if labels:
        return f"站内关键词包括{'、'.join(labels)}；原文相关句子集中说明：{base}"
    return base


def knowledge_detail_clause(text: str) -> str:
    clauses = []
    for label, terms in HVAC_KNOWLEDGE_GROUPS:
        found = matched_terms(text, terms, limit=3)
        if found:
            clauses.append(f"{label}涉及{'、'.join(found)}")
    if clauses:
        return "，".join(clauses[:2])
    return ""


def summarize_evidence_as_chinese(query: str, result: SearchResult, sentences: List[str]) -> str:
    text = normalize_text(" ".join([result.title, result.snippet, result.content, " ".join(sentences)]))
    technologies = matched_labels(text, TECHNOLOGY_KEYWORDS)
    scenarios = matched_labels(text, SCENARIO_KEYWORDS)
    effects = matched_labels(text, EFFECT_KEYWORDS)
    years = years_in_text(text)
    detail = knowledge_detail_clause(text)

    if is_hvac_query(query) and not is_heat_pump_query(query) and has_explicit_hvac_focus(text):
        technology = "暖通空调（HVAC）系统"
    else:
        technology = technologies[0] if technologies else "该技术方向"
    scenario = scenarios[0] if scenarios else "建筑暖通场景"
    effect = effects[0] if effects else "提升系统运行管理水平"
    year_note = f"{'、'.join(years[:2])}年资料中，" if years else ""
    detail_note = f"，其中{detail}" if detail else ""

    if "AI预测控制" in technology or "建筑能源管理系统" in technology:
        return f"{year_note}{technology}可用于{scenario}的暖通运行优化，核心价值在于基于负荷和运行状态进行提前调节，从而{effect}{detail_note}"
    if "热回收" in technology:
        return f"{year_note}{technology}关注排风、余热或新风处理中的能量回收，适合在{scenario}中降低冷热源负荷并{effect}{detail_note}"
    if "热泵" in technology:
        if is_hvac_query(query) and not is_heat_pump_query(query):
            return f"{year_note}在暖通空调（HVAC）系统中，热泵属于冷热源方案之一，其运行效果通常与适用工况、产品参数和案例运行数据有关{detail_note}"
        return f"{year_note}{technology}可作为建筑冷热源方案，其运行效果取决于适用工况、产品参数和案例运行数据{detail_note}"
    if "太阳能" in technology:
        return f"{year_note}{technology}需要与建筑负荷、储能或热泵系统匹配，评价重点是应用场景、产品化进展和运行数据{detail_note}"
    if "HVAC" in technology:
        return f"{year_note}{technology}覆盖供暖、通风和空调调节环节，在{scenario}中通常通过冷热源、空气侧和水侧系统协同实现环境控制{detail_note}"
    return f"{year_note}{technology}在{scenario}中的价值主要体现在{effect}，其技术判断通常围绕技术路线、适用边界和性能指标展开{detail_note}"


def markdown_link(label: str, url: str) -> str:
    safe_label = (label or "").replace("[", "\\[").replace("]", "\\]")
    safe_url = (url or "").replace(")", "%29").replace("(", "%28")
    return f"[{safe_label}]({safe_url})" if safe_url else safe_label


def useful_text(result: SearchResult) -> str:
    for candidate in [result.content, result.snippet]:
        text = " ".join((candidate or "").split())
        if not text:
            continue
        lowered = text.lower()
        if any(phrase.lower() in lowered for phrase in NOISY_PHRASES):
            continue
        return text
    return ""


def normalize_text(text: str) -> str:
    text = " ".join((text or "").split())
    for phrase in NOISY_PHRASES:
        text = re.sub(re.escape(phrase), " ", text, flags=re.I)
    for pattern in NOISY_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.I)
    return " ".join(text.split())


def split_sentences(text: str) -> List[str]:
    text = normalize_text(text)
    parts = re.split(r"[。！？.!?；;]\s*", text)
    sentences = []
    for part in parts:
        part = part.strip(" \t:-_—，,;；")
        match = re.search(
            r"(产品|案例|创新|试点|商业化|热泵|空调|节能|系统|HVAC|product|case|innovation|heat pump)",
            part,
            flags=re.I,
        )
        if match:
            prefix = part[: match.start()]
            trimmed = part[match.start() :]
            if 12 <= len(trimmed) <= 180 and not has_knowledge_signal(prefix):
                part = trimmed
        if 12 <= len(part) <= 180:
            sentences.append(part)
    return sentences


def is_noisy_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if any(phrase.lower() in lowered for phrase in NOISY_PHRASES):
        return True
    if any(term.lower() in lowered for term in DISCLAIMER_TERMS):
        return True
    if any(re.search(pattern, sentence, flags=re.I) for pattern in NOISY_PATTERNS):
        return True
    if len(re.findall(r"\d", sentence)) > 10:
        return True
    if sentence.count("|") >= 2 or sentence.count("_") >= 2:
        return True
    return False


def remove_disclaimer_text(text: str) -> str:
    cleaned = text or ""
    for term in DISCLAIMER_TERMS:
        match = re.search(re.escape(term), cleaned, flags=re.I)
        if match:
            cleaned = cleaned[: match.start()]
    return compact_chinese_spaces(cleaned).strip("。；;，, ")


def sentence_score(sentence: str, query: str) -> int:
    lowered = sentence.lower()
    score = 0
    for term in [query, *query.split()]:
        if term and term.lower() in lowered:
            score += 4
    for term in KNOWLEDGE_TERMS:
        if term.lower() in lowered:
            score += 1
    target_hits = sum(1 for term in TARGET_EVIDENCE_TERMS if term.lower() in lowered)
    basic_hits = sum(1 for term in BASIC_KNOWLEDGE_TERMS if term.lower() in lowered)
    score += min(target_hits, 5) * 3
    if re.search(r"\b202[4-6]\b", sentence):
        score += 4
    if any(word in sentence for word in ["发布", "推出", "应用", "采用", "部署", "试点", "节省", "降低", "提升"]):
        score += 2
    if any(word in sentence for word in ["因此", "通过", "可以", "能够", "有助于", "适用于"]):
        score += 1
    if basic_hits and target_hits == 0:
        score -= min(basic_hits, 3) * 2
    return score


def has_knowledge_signal(text: str) -> bool:
    return has_any(
        text,
        [
            *KNOWLEDGE_TERMS,
            *TARGET_EVIDENCE_TERMS,
            *HVAC_COMPONENT_TERMS,
            *HVAC_TYPE_TERMS,
            *HVAC_METRIC_TERMS,
            *HVAC_FACTOR_TERMS,
            "HVAC",
            "暖通",
            "空调",
            "通风",
            "供暖",
            "数据中心",
            "building",
            "energy",
            "efficiency",
        ],
    )


def extract_knowledge_sentences(query: str, result: SearchResult, limit: int = 2) -> List[str]:
    scored = []
    for sentence in split_sentences(useful_text(result)):
        if is_noisy_sentence(sentence):
            continue
        score = sentence_score(sentence, query)
        if score >= 4 or (score >= 2 and has_knowledge_signal(sentence)):
            scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in scored[:limit]]


def collect_evidence(query: str, results: List[SearchResult], limit: int = 5) -> List[str]:
    evidence = []
    seen = set()
    for result in results:
        for sentence in extract_knowledge_sentences(query, result, limit=3):
            key = sentence[:42]
            if key in seen:
                continue
            seen.add(key)
            evidence.append(sentence)
            if len(evidence) >= limit:
                return evidence
    return evidence


def has_any(text: str, terms: List[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def infer_heat_pump_points(text: str) -> List[str]:
    points = []
    if has_any(text, ["压缩机", "蒸发器", "冷凝器", "节流", "制冷剂", "冷媒", "compression", "evaporator", "condenser"]):
        points.append(
            "典型蒸气压缩式热泵由压缩机、蒸发器、冷凝器、节流装置和制冷剂循环构成，通过吸热、压缩升温、放热和节流降压完成热量搬运"
        )
    if has_any(text, ["COP", "HSPF", "SCOP", "效率", "能效", "节能比", "制热量", "能耗"]):
        points.append(
            "热泵能效评价通常涉及制热或制冷能力、COP、季节能效和运行工况等维度"
        )
    points.extend(infer_heat_pump_type_points(text))
    if has_any(text, ["供暖", "热水", "空调", "建筑", "冷热源", "采暖", "生活热水"]):
        points.append(
            "从建筑应用看，热泵适合承担供暖、生活热水和空调冷热源任务，是建筑运行阶段降低能源消耗的重要设备"
        )
    if has_any(text, ["碳排放", "化石", "减排", "电能", "余热", "废热", "能源消耗"]):
        points.append(
            "从节能机制看，热泵的优势在于用较少电能搬运环境热或余热，从而减少直接燃烧化石能源带来的能耗和排放"
        )
    return points


def infer_heat_pump_type_points(text: str) -> List[str]:
    type_terms = [
        ("空气源热泵", ["空气源", "环境空气", "室外空气", "air source", "ASHP"]),
        ("水源热泵", ["水源", "地下水", "地表水", "water source", "WSHP"]),
        ("地源热泵", ["地源", "土壤", "岩土", "ground source", "GSHP"]),
        ("余热源热泵", ["余热", "废热", "排热", "waste heat"]),
    ]
    found = [name for name, terms in type_terms if has_any(text, terms)]
    if len(found) >= 2:
        return [
            f"按热源形式划分，热泵可结合资料中的表述归纳为{'、'.join(found)}等类型，不同类型的效率和适用条件取决于热源温度稳定性与取热条件"
        ]
    if found:
        return [
            f"该资料主要覆盖{found[0]}，重点说明这一类型的取热方式和应用特点"
        ]
    return []


def infer_solar_points(text: str) -> List[str]:
    points = []
    if has_any(text, ["光伏", "发电", "PV", "photovoltaic"]):
        points.append("光伏路径的重点是把建筑可利用太阳辐射转化为电力，为空调、热泵或建筑用电负荷提供补充能源")
    if has_any(text, ["光热", "集热", "热水", "供暖", "solar thermal"]):
        points.append("光热路径的重点是把太阳辐射转化为热量，更适合与生活热水、供暖或辅助热源系统结合")
    if has_any(text, ["储能", "蓄热", "控制", "管理", "并网", "负荷"]):
        points.append("太阳能建筑节能效果依赖储能、蓄热和运行控制，只有与负荷时段匹配时才能稳定降低外购能源需求")
    return points


def infer_hvac_points(text: str) -> List[str]:
    points = []
    if has_any(text, ["heating", "ventilation", "air conditioning", "HVAC", "暖通", "通风", "空调"]):
        points.append(
            "HVAC系统由供暖、通风、空气调节和控制环节构成，系统边界通常包括冷热源、空气侧和水侧系统"
        )
    if has_any(text, ["冷水机组", "锅炉", "热泵", "风机盘管", "空气处理", "AHU", "VAV", "水泵", "风机", "管道", "风管"]):
        points.append(
            "HVAC系统能耗来自冷热源、风机、水泵和末端设备的共同作用，系统能效评价通常包括主机效率、输配能耗和末端换热效率"
        )
    if has_any(text, ["负荷", "温湿度", "新风", "室内空气", "舒适", "IAQ", "fresh air", "humidity"]):
        points.append(
            "HVAC系统的运行目标是在满足温湿度、室内空气品质和热舒适要求的前提下降低能耗，因此建筑负荷、新风量和控制策略会直接影响节能效果"
        )
    if has_any(text, ["控制", "自控", "BMS", "传感器", "变频", "节能", "能效", "优化", "demand", "control"]):
        points.append(
            "HVAC节能的关键路径包括变频输配、按需通风、运行时段优化和建筑管理系统联动，核心是减少低负荷和非使用时段的无效运行"
        )
    if has_any(text, ["热回收", "余热", "heat recovery", "recovery"]):
        points.append(
            "当系统存在排风、冷凝热或余热资源时，热回收可降低新风处理和冷热源负荷，是提高HVAC系统综合能效的重要措施"
        )
    return points


def infer_general_points(query: str, text: str) -> List[str]:
    points = []
    if has_any(text, ["产品", "解决方案", "案例", "试点", "commercial", "product", "case study"]):
        points.append(f"{query}应优先整理为具体产品或工程案例线索，重点核查发布时间、应用场景和性能指标")
    if has_any(text, ["创新", "新技术", "技术路线", "innovation", "innovative", "technology"]):
        points.append(f"{query}的检索重点应落在近三年创新技术路线及其相对传统方案的改进点")
    if has_any(text, ["节能效果", "性能指标", "参数", "energy savings", "performance", "datasheet"]):
        points.append(f"{query}的可用证据应优先提取性能指标、节能效果、产品参数和案例数据")
    return points


def synthesize_points(query: str, result: SearchResult, sentences: List[str]) -> List[str]:
    text = normalize_text(" ".join([result.title, result.snippet, result.content, " ".join(sentences)]))
    if is_hvac_query(query) and not is_heat_pump_query(query) and has_knowledge_signal(text):
        return [summarize_evidence_as_chinese(query, result, sentences)]
    if sentences and (
        has_any(text, TARGET_EVIDENCE_TERMS)
        or contains_english_sentence(text)
        or has_any(text, ["HVAC", "暖通", "空调", "建筑", "energy", "building"])
    ):
        return [summarize_evidence_as_chinese(query, result, sentences)]
    if not has_any(text, TARGET_EVIDENCE_TERMS):
        return []

    if "热泵" in query:
        points = infer_heat_pump_points(text)
    elif "太阳能" in query:
        points = infer_solar_points(text)
    elif "HVAC" in query.upper() or "暖通" in query or "空调" in query:
        points = infer_hvac_points(text)
    else:
        points = infer_general_points(query, text)
    if not points and sentences:
        points = infer_general_points(query, " ".join(sentences))
    return points[:3]


def point_key(point: str) -> str:
    return re.sub(r"[，。；：、“”‘’（）\s]", "", point)[:28]


def make_finding(query: str, result: SearchResult, sentences: List[str], used_points: set) -> str:
    title = re.sub(r"[_|].*$", "", result.title).strip()
    source_link = markdown_link(title, result.url)
    points = synthesize_points(query, result, sentences)
    chosen = ""
    for point in points:
        key = point_key(point)
        if key and key not in used_points:
            chosen = point
            used_points.add(key)
            break
    if not chosen:
        return ""
    weak_note = "，参考性较弱" if result.source_tier == 3 else ""
    return f"{chosen}。来源：{source_link}（{result.domain}，{result.source_tier_label}{weak_note}）"


def pick_findings(query: str, results: List[SearchResult]) -> List[str]:
    findings = []
    used_points = set()
    for result in results:
        sentences = extract_knowledge_sentences(query, result)
        finding = make_finding(query, result, sentences, used_points)
        if not finding:
            continue
        findings.append(finding)
        if len(findings) >= 3:
            break
    return findings


def reliable_results(results: List[SearchResult]) -> List[SearchResult]:
    return [result for result in results if result.source_tier <= 2]


def weak_results(results: List[SearchResult]) -> List[SearchResult]:
    return [result for result in results if result.source_tier == 3]


def source_id(index: int) -> str:
    return f"S{index + 1}"


def source_confidence(result: SearchResult) -> str:
    if result.source_tier <= 1 and result.source_reliability_score >= 8:
        return "高"
    if result.source_tier <= 2 and result.source_reliability_score >= 6:
        return "中"
    return "低"


def source_reference(result: SearchResult, index: int) -> str:
    title = re.sub(r"[_|].*$", "", result.title).strip() or result.domain or result.url
    return (
        f"[{source_id(index)}] {markdown_link(title, result.url)}"
        f"（{result.source_tier_label or result.source_type}/{result.domain}，"
        f"可信度评分 {result.source_reliability_score}/10）"
    )


def evidence_conclusion(query: str, sentence: str) -> str:
    sentence = compact_chinese_spaces(short(sentence, 140)).rstrip("。；;，,")
    if not sentence:
        return ""
    if query and query not in sentence:
        return f"{query}相关信息包括：{sentence}"
    return sentence


def term_count(text: str, terms: List[str]) -> int:
    return sum(1 for term in terms if term.lower() in text.lower())


def title_has_forbidden_phrase(title: str) -> bool:
    return any(phrase in title for phrase in FORBIDDEN_FINDING_PHRASES)


def title_has_forbidden_tone(title: str) -> bool:
    return any(phrase in title for phrase in FORBIDDEN_FINDING_TONE_PHRASES)


def neutralize_finding_title(query: str, title: str, text: str) -> str:
    title = title.replace("需要注意的是，", "").replace("需要注意的是", "")
    if "不能只看" in title:
        first = re.search(r"不能只看([^，。；;]+)", title)
        second = re.search(r"(?:还应结合|还应考虑|应结合|应考虑)([^，。；;]+)", title)
        parts = []
        if first:
            parts.append(first.group(1).strip())
        if second:
            parts.append(second.group(1).strip())
        if parts:
            return f"{query}评价通常涉及{'、'.join(parts)}等维度"
    if "不能只用" in title:
        components = [term for term in HVAC_COMPONENT_TERMS if term in text]
        if len(components) >= 3:
            return f"{query}通常由{'、'.join(components[:5])}等组成"
    if "不能扩展" in title and "该资料" in title:
        title = re.sub(r"，?其结论.*$", "", title)
    title = title.replace("还应结合", "通常涉及")
    title = title.replace("还应考虑", "通常涉及")
    title = title.replace("应结合", "涉及")
    title = title.replace("应考虑", "涉及")
    title = title.replace("必须考虑", "涉及")
    title = title.replace("应先", "通常")
    title = title.replace("而不是", "并")
    return title


def title_needs_narrowing(title: str) -> bool:
    broad_type = any(phrase in title for phrase in ["几种类型", "多种类型", "主要类型", "以下几种"])
    broad_component = any(phrase in title for phrase in ["几个关键部件", "关键组件", "关键部件", "系统组成"])
    broad_factor = any(phrase in title for phrase in ["影响因素", "关键因素", "主要因素"])
    broad_metric = any(phrase in title for phrase in ["评价指标", "评价维度", "性能指标"])
    if broad_type and term_count(title, HVAC_TYPE_TERMS) < 2:
        return True
    if broad_component and term_count(title, HVAC_COMPONENT_TERMS) < 3:
        return True
    if broad_factor and term_count(title, HVAC_FACTOR_TERMS) < 2:
        return True
    if broad_metric and term_count(title, HVAC_METRIC_TERMS) == 0:
        return True
    return False


def review_finding_title(query: str, title: str, text: str) -> str:
    title = compact_chinese_spaces(title).strip("。；;，, ")
    for phrase in FORBIDDEN_FINDING_PHRASES:
        title = title.replace(phrase, "").strip("，。；;：: ")
    title = neutralize_finding_title(query, title, text)
    if "热泵" in query and title_needs_narrowing(title):
        points = infer_heat_pump_points(text)
        for point in points:
            if not title_needs_narrowing(point) and not title_has_forbidden_tone(point):
                return point
    if title_has_forbidden_tone(title):
        return ""
    return title


def build_finding_title(query: str, result: SearchResult, sentences: List[str], used_titles: set) -> str:
    text = normalize_text(" ".join([result.title, result.snippet, result.content, " ".join(sentences)]))
    candidates = synthesize_points(query, result, sentences)
    candidates = sorted(candidates, key=lambda candidate: sentence_score(candidate, query), reverse=True)
    for candidate in candidates:
        title = review_finding_title(query, candidate, text)
        if not title or title_has_forbidden_phrase(title) or title_has_forbidden_tone(title):
            continue
        key = point_key(title)
        if key and key not in used_titles:
            used_titles.add(key)
            return title
    return ""


def build_support_evidence(query: str, sentence: str, text: str) -> str:
    evidence = summarize_evidence_as_chinese(
        query,
        SearchResult(title="", url="", domain="", snippet="", content=text),
        [sentence],
    )
    evidence = review_finding_title(query, evidence, text)
    if not evidence or title_has_forbidden_phrase(evidence) or title_has_forbidden_tone(evidence):
        evidence = compact_chinese_spaces(short(sentence, 160))
        for phrase in FORBIDDEN_FINDING_PHRASES:
            evidence = evidence.replace(phrase, "").strip("，。；;：: ")
        evidence = neutralize_finding_title(query, evidence, text)
    return evidence.strip("。；;，, ")


def evidence_limitation(result: SearchResult) -> str:
    if result.source_tier >= 3:
        return "该来源参考性较弱，需用政府、高校、标准组织或技术文档等一手资料复核。"
    if result.source_reliability_score < 8:
        return "该发现主要来自单一来源，仍缺少更多一手数据或案例交叉验证。"
    return "该发现只说明来源文本中可核查的内容，实际效果仍受工况、场景和系统匹配影响。"


def build_evidence_findings(query: str, results: List[SearchResult]) -> List[str]:
    findings = []
    used_sentences = set()
    used_titles = set()
    used_angles = set()
    broad_hvac_query = is_hvac_query(query) and not is_heat_pump_query(query)
    explicit_hvac_available = any(
        has_explicit_hvac_focus(normalize_text(" ".join([result.title, result.snippet, result.content[:800]])))
        for result in results
    )
    for index, result in enumerate(results):
        result_text = normalize_text(" ".join([result.title, result.snippet, result.content[:1200]]))
        if (
            broad_hvac_query
            and explicit_hvac_available
            and not has_explicit_hvac_focus(result_text)
            and has_any(result_text, ["热泵", "heat pump"])
        ):
            continue
        site_keywords = extract_site_keywords(query, result)
        sentences = collect_keyword_sentences(result, site_keywords)
        if not sentences:
            sentences = extract_knowledge_sentences(query, result, limit=2)
        if not sentences:
            fallback_text = normalize_text(" ".join([result.title, result.snippet, result.content[:400]]))
            sentences = [
                sentence
                for sentence in split_sentences(fallback_text)
                if not is_noisy_sentence(sentence) and has_knowledge_signal(sentence)
            ][:2]
            if not sentences and has_knowledge_signal(fallback_text):
                sentences = [short(remove_disclaimer_text(fallback_text), 160)]
        if not sentences:
            continue
        candidate_text = normalize_text(" ".join([result.title, result.snippet, result.content, " ".join(sentences)]))
        if not has_knowledge_signal(candidate_text):
            continue
        sentence = sentences[0]
        key = compact_chinese_spaces(result.title + sentence)[:64]
        if key in used_sentences:
            continue
        title = build_site_viewpoint(query, result, site_keywords, sentences, used_angles)
        title_registered = False
        if not title:
            title = build_finding_title(query, result, sentences, used_titles)
            title_registered = bool(title)
        if not title:
            continue
        title_key = point_key(title)
        if not title_registered and title_key in used_titles:
            continue
        if not title_registered:
            used_titles.add(title_key)
        used_sentences.add(key)
        evidence_text = support_evidence_from_sentences(sentences, site_keywords)
        if not evidence_text or contains_english_sentence(evidence_text):
            evidence_text = build_support_evidence(
                query,
                sentence,
                normalize_text(" ".join([result.title, result.snippet, result.content, " ".join(sentences)])),
            )
        confidence = source_confidence(result)
        reason = (
            "来源等级较高且与主题相关，证据可直接回到原链接核查。"
            if confidence != "低"
            else "来源质量或证据完整度有限，只能作为低强度发现。"
        )
        finding = "\n".join(
            [
                f"#### 发现 {len(findings) + 1}：{title}",
                f"- 支撑证据：[{source_id(index)}] {evidence_text}。",
                "- 来源链接：",
                f"  - {source_reference(result, index)}",
                f"- 可信度：{confidence}。{reason}",
                f"- 局限性：{evidence_limitation(result)}",
            ]
        )
        findings.append(finding)
        if len(findings) >= 4:
            break
    return findings


def build_evidence_conclusion(query: str, findings: List[str], reliable_count: int) -> str:
    points = conclusion_points_from_findings(query, findings)
    if points:
        conclusion = synthesize_knowledge_conclusion(query, points)
    else:
        conclusion = fallback_knowledge_conclusion(query)
    return review_knowledge_conclusion(query, conclusion, points)


def conclusion_points_from_findings(query: str, findings: List[str], limit: int = 4) -> List[str]:
    points = []
    seen = set()
    for finding in findings:
        match = re.search(r"^####\s*发现\s*\d+：(.+)$", finding, flags=re.M)
        if not match:
            continue
        point = clean_conclusion_point(query, match.group(1))
        if not point:
            continue
        key = point_key(point)
        if key in seen:
            continue
        seen.add(key)
        points.append(point)
        if len(points) >= limit:
            break
    return points


def clean_conclusion_point(query: str, point: str) -> str:
    point = compact_chinese_spaces(point)
    point = re.sub(r"^现有来源显示，", "", point)
    if query:
        point = re.sub(rf"^{re.escape(query)}相关信息包括：", "", point)
    point = point.strip("。；;，, ")
    point = re.sub(r"来源：.*$", "", point).strip("。；;，, ")
    return short(point, 76)


def synthesize_knowledge_conclusion(query: str, points: List[str]) -> str:
    if len(points) == 1:
        return f"关于“{query}”，检索资料主要显示：{points[0]}。"
    if len(points) == 2:
        return f"关于“{query}”，检索资料共同指向两个重点：{points[0]}；同时，{points[1]}。"
    main_points = "；".join(points[:3])
    return f"关于“{query}”，检索资料主要形成三条技术产品线索：{main_points}。"


def fallback_knowledge_conclusion(query: str) -> str:
    if "热泵" in query:
        return (
            "本次结果尚未形成足够完整的热泵创新产品证据。"
            "后续应继续优先追踪近三年的高温热泵、余热源热泵、自然工质热泵或模块化商用热泵产品，重点核查企业发布、产品手册、示范项目、性能指标和节能效果。"
        )
    if "太阳能" in query:
        return (
            "本次结果尚未形成足够完整的太阳能暖通创新产品证据。"
            "后续应继续优先追踪近三年的太阳能光热空调、PVT 与热泵耦合、建筑光伏直驱空调或商业建筑示范项目，重点核查产品化进展、应用场景和运行数据。"
        )
    if "HVAC" in query.upper() or "暖通" in query or "空调" in query:
        return (
            f"本次结果尚未形成足够完整的“{query}”创新产品证据。"
            "后续应继续优先追踪近三年的AI预测控制、智能楼宇管理、低碳冷热源、热回收新风或智慧输配产品，重点核查企业案例、产品发布、性能指标和节能效果。"
        )
    return (
        f"关于“{query}”，当前结果尚未形成足够完整的近三年创新技术与产品证据。"
        "后续应继续换用更细分的产品、企业、案例、白皮书、产品手册、试点项目和性能指标关键词，避免退回基础概念综述。"
    )


def review_knowledge_conclusion(query: str, conclusion: str, points: List[str]) -> str:
    if any(phrase in conclusion for phrase in FORBIDDEN_CONCLUSION_PHRASES):
        return fallback_knowledge_conclusion(query)
    if points and not any(point[:12] in conclusion for point in points):
        return synthesize_knowledge_conclusion(query, points)
    return conclusion


def build_summary(query: str, raw_count: int, read_count: int, results: List[SearchResult]) -> str:
    kept_count = len(results)
    reliable = reliable_results(results)
    findings = build_evidence_findings(query, results[:8])
    reliable_note = (
        "高可信来源数量相对充足，可形成初步交叉参考。"
        if len(reliable) >= 2
        else "高可信来源少于 2 条，当前摘要只适合作为初步检索结果。"
    )

    lines = [
        f"### 查询主题：{query}",
        "",
        "### 本次检索概况",
        (
            f"本次共检索到 {raw_count} 条结果，成功读取正文 {read_count} 页，"
            f"筛选后保留 {kept_count} 条来源。{reliable_note}"
        ),
        "",
        "### 核心发现",
    ]
    if findings:
        lines.extend(findings)
    else:
        lines.append("暂无可靠核心发现。")

    lines.extend(["", "### 重要来源"])
    if reliable:
        for index, result in enumerate(reliable[:5]):
            lines.append(f"- {source_reference(result, index)}")
    else:
        lines.append("- 暂无足够可靠来源。")

    weak = weak_results(results)
    if weak:
        lines.extend(["", "### 补充来源（参考性较弱）"])
        for result in weak[:5]:
            title = re.sub(r"[_|].*$", "", result.title).strip() or result.domain or result.url
            lines.append(
                f"- {markdown_link(title, result.url)}"
                f"（{result.domain}，参考性较弱，需人工复核）"
            )

    uncertainty_points = [
        "部分网页正文可能因反爬、登录限制或页面脚本加载而无法完整读取，证据覆盖不完整。",
        "产品参数、运行工况和案例真实性需要回到原始页面或一手文件人工复核。",
    ]
    if len(reliable) < 2:
        uncertainty_points.append("高可信来源不足 2 条，现有来源不足以支持更强判断。")

    lines.extend(["", "### 不能确认的点"])
    for point in uncertainty_points[:3]:
        lines.append(f"- {point}")

    lines.extend(["", "### 总体结论", build_evidence_conclusion(query, findings, len(reliable))])
    return "\n".join(lines)
