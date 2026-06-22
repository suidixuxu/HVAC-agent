from ranker import rank_results
from search_engine import read_result_pages, search_web
from summarizer import build_summary


def run(query: str, search_top_n: int = 20, read_top_k: int = 8):
    raw = search_web(query, search_top_n)
    read_result_pages(raw, read_top_k)
    ranked = rank_results(raw, query)
    read_count = sum(1 for r in raw if r.read_success)
    summary = build_summary(query, len(raw), read_count, ranked)
    return raw, ranked, summary


if __name__ == "__main__":
    queries = ["\u70ed\u6cf5", "\u592a\u9633\u80fd"]
    for query in queries:
        raw, ranked, summary = run(query)
        print("=" * 80)
        print("QUERY:", query)
        print("RAW_COUNT:", len(raw), "KEPT_COUNT:", len(ranked))
        print("TOP_TITLES:")
        for item in ranked[:5]:
            print(
                f"- {item.title} | {item.domain} | "
                f"final={item.score} topic={item.topic_relevance_score} "
                f"source={item.source_reliability_score} "
                f"readability={item.content_readability_score} "
                f"freshness={item.freshness_score} | {item.ranking_reason}"
            )
        print("SUMMARY:")
        print(summary[:900])
