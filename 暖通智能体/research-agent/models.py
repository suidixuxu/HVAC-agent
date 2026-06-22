from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchResult:
    title: str
    url: str
    domain: str
    snippet: str = ""
    source_type: str = "unknown"
    source_tier: int = 3
    source_tier_label: str = ""
    source_reliability_score: float = 0.0
    source_reason: str = ""
    topic_relevance_score: float = 0.0
    content_readability_score: float = 0.0
    freshness_score: float = 0.0
    ranking_reason: str = ""
    score: float = 0.0
    rank: int = 0
    content: str = ""
    content_length: int = 0
    published_at: str = ""
    author: str = ""
    read_status: str = ""
    read_success: bool = False
    read_error: str = ""
    matched_terms: List[str] = field(default_factory=list)


@dataclass
class SearchReport:
    query: str
    search_engine: str
    raw_count: int
    read_count: int
    kept_count: int
    results: List[SearchResult]
    summary: str
    debug_notes: List[str]
