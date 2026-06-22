import unittest
import time
from unittest.mock import patch

import search_engine
from models import SearchResult
from search_engine import (
    build_query_variants,
    dedupe_results,
    domain_of,
    normalize_result_url,
    stratified_sample_results,
)
from ranker import rank_results
from summarizer import build_evidence_findings


def make_result(title: str, url: str, snippet: str = "") -> SearchResult:
    return SearchResult(title=title, url=url, domain=domain_of(url), snippet=snippet)


class SearchSamplingTest(unittest.TestCase):
    def test_build_query_variants_expands_chinese_and_english_terms(self):
        variants = build_query_variants("热泵")

        self.assertIn("热泵", variants)
        self.assertTrue(any("heat pump" in variant for variant in variants))
        self.assertTrue(any("product" in variant for variant in variants))
        self.assertTrue(any("case study" in variant for variant in variants))
        self.assertTrue(any("2024 2025 2026" in variant for variant in variants))
        self.assertFalse(any("原理" in variant for variant in variants))

    def test_query_variants_expand_to_wider_candidate_set(self):
        variants = build_query_variants("heat pump")

        self.assertGreaterEqual(len(variants), 6)
        self.assertLessEqual(len(variants), 8)

    def test_search_single_query_merges_bing_and_duckduckgo(self):
        bing = make_result("Bing heat pump", "https://bing.example.com/heat-pump")
        duckduckgo = make_result("Duck heat pump", "https://duck.example.com/heat-pump")

        with patch.object(search_engine, "search_bing_rss", return_value=[bing]):
            with patch.object(search_engine, "search_bing_html", return_value=[]):
                with patch.object(search_engine, "search_sogou_html", return_value=[]):
                    with patch.object(
                        search_engine,
                        "search_duckduckgo_html",
                        return_value=[duckduckgo],
                    ) as search_duckduckgo:
                        results = search_engine.search_single_query("heat pump", 10)

        self.assertEqual(
            {result.domain for result in results},
            {"bing.example.com", "duck.example.com"},
        )
        search_duckduckgo.assert_called_once()

    def test_search_single_query_fetches_sources_in_parallel(self):
        def slow_result(domain: str):
            time.sleep(0.15)
            return [make_result(domain, f"https://{domain}/article")]

        with patch.object(search_engine, "search_bing_rss", side_effect=lambda *_: slow_result("rss.example.com")):
            with patch.object(search_engine, "search_bing_html", side_effect=lambda *_: slow_result("html.example.com")):
                with patch.object(search_engine, "search_sogou_html", side_effect=lambda *_: slow_result("sogou.example.com")):
                    with patch.object(search_engine, "search_duckduckgo_html", side_effect=lambda *_: slow_result("duck.example.com")):
                        started = time.perf_counter()
                        results = search_engine.search_single_query("heat pump", 10)
                        elapsed = time.perf_counter() - started

        self.assertEqual(len(results), 4)
        self.assertLess(elapsed, 0.35)

    def test_dedupe_results_uses_normalized_urls(self):
        first = make_result(
            "Heat pump report",
            "https://Example.com/report/?utm_source=test&id=1#section",
        )
        duplicate = make_result("Duplicate", "https://example.com/report?id=1")

        self.assertEqual(
            normalize_result_url(first.url),
            "https://example.com/report?id=1",
        )
        self.assertEqual(len(dedupe_results([first, duplicate])), 1)

    def test_read_result_pages_fetches_pages_in_parallel(self):
        results = [
            make_result(
                f"HVAC result {index}",
                f"https://example{index}.com/article",
                "HVAC system article with enough context",
            )
            for index in range(6)
        ]

        def slow_fetch(_url):
            time.sleep(0.15)
            return "<html>ok</html>"

        def fake_extract(_html, _url):
            return search_engine.PageExtraction(
                content="HVAC system performance and energy savings. " * 6,
                content_length=260,
                read_status="fallback_success",
            )

        started = time.perf_counter()
        with patch.object(search_engine, "fetch_url", side_effect=slow_fetch):
            with patch.object(search_engine, "extract_page_data", side_effect=fake_extract):
                search_engine.read_result_pages(results, read_top_k=6)
        elapsed = time.perf_counter() - started

        self.assertEqual(sum(1 for result in results if result.read_success), 6)
        self.assertLess(elapsed, 0.6)

    def test_stratified_sample_does_not_only_keep_first_results(self):
        weak_results = [
            make_result(f"News item {index}", f"https://news.example.com/{index}", "news blog")
            for index in range(4)
        ]
        industry = make_result(
            "Heat pump product solution",
            "https://carrier.com/heat-pump-solution",
            "product solution technical case",
        )
        authoritative = make_result(
            "Heat pump research report",
            "https://www.energy.gov/eere/buildings/heat-pump-report",
            "research report guideline",
        )

        results = weak_results + [industry, authoritative]
        sampled = stratified_sample_results(results, 3)
        sampled_domains = {result.domain for result in sampled}

        self.assertNotEqual(sampled, results[:3])
        self.assertIn("carrier.com", sampled_domains)
        self.assertIn("energy.gov", sampled_domains)

    def test_rank_results_prefers_recent_product_information_over_basics(self):
        product = make_result(
            "Heat pump product launch 2025 case study",
            "https://carrier.com/heat-pump-product-2025",
            "commercial heat pump product launch 2025 case study energy savings datasheet",
        )
        basic = make_result(
            "热泵是什么和原理介绍",
            "https://example.com/heat-pump-basics",
            "热泵定义 原理 基础知识 概述",
        )

        ranked = rank_results([basic, product], "热泵")

        self.assertEqual(ranked[0].title, product.title)

    def test_core_findings_summarize_english_source_as_chinese_knowledge(self):
        result = make_result(
            "What is HVAC?",
            "https://example.com/what-is-hvac",
            "HVAC units are used in both commercial and residential areas.",
        )
        result.content = (
            "HVAC units are used in both commercial and residential areas. "
            "HVAC systems offer solutions for commercial building energy efficiency."
        )
        result.source_tier = 2
        result.source_tier_label = "产业/企业来源"
        result.source_reliability_score = 5.0

        findings = build_evidence_findings("HVAC AI预测控制产品 2024", [result])
        joined = "\n".join(findings)

        self.assertIn("暖通空调", joined)
        self.assertIn("商业建筑", joined)
        self.assertNotIn("HVAC units are used", joined)
        self.assertNotIn("commercial and residential areas", joined)

    def test_hvac_query_filters_game_sites_and_portal_homepages(self):
        game = make_result(
            "World of Tanks: HEAT",
            "https://wargaming.net/en/games/wotheat",
            "World of Tanks: HEAT is a free-to-play vehicle shooter from Wargaming.",
        )
        portal_home = make_result(
            "制冷网-制冷行业权威的门户网站 制冷,空调,冷冻,冷藏,冷链",
            "http://www.zhileng.com/",
            "中国制冷网,立志成为行业内原创信息量最大的门户网站,全力构建国内制冷行业的信息交流平台!",
        )
        article = make_result(
            "HVAC系统节能控制技术文章",
            "http://www.zhileng.com/news/hvac-energy-saving-control.html",
            "本文介绍暖通空调HVAC系统在商业建筑中的节能控制技术和应用案例。",
        )

        ranked = rank_results([game, portal_home, article], "HVAC")

        self.assertEqual([item.title for item in ranked], [article.title])

    def test_hvac_query_variants_include_zhileng_article_search(self):
        variants = build_query_variants("HVAC")

        self.assertTrue(any("site:zhileng.com" in variant for variant in variants))
        self.assertTrue(any("技术 文章" in variant for variant in variants))

    def test_hvac_query_keeps_hvac_as_primary_topic_when_source_mentions_heat_pump(self):
        result = make_result(
            "What Does HVAC Stand For?",
            "https://example.com/what-does-hvac-stand-for",
            (
                "HVAC stands for heating, ventilation and air conditioning. "
                "Heat pump systems can be used as a heating and cooling source in buildings."
            ),
        )
        result.content = (
            "HVAC stands for heating, ventilation and air conditioning. "
            "HVAC systems combine heating, ventilation, cooling, air-side systems, "
            "water-side systems and controls. Heat pump systems can be used as one building "
            "heating and cooling source."
        )
        result.source_tier = 2
        result.source_tier_label = "产业/企业来源"
        result.source_reliability_score = 6.5

        findings = build_evidence_findings("HVAC", [result])
        joined = "\n".join(findings)

        self.assertIn("暖通空调（HVAC）系统", joined)
        self.assertIn("供暖", joined)
        self.assertIn("通风", joined)
        self.assertNotIn("热泵系统可作为建筑冷热源方案", joined)

    def test_core_findings_use_knowledge_points_and_keep_two_to_four_items(self):
        heat_pump = make_result(
            "热泵系统运行参数分析",
            "https://example.com/heat-pump-operation",
            "热泵系统涉及压缩机、蒸发器、冷凝器和COP等评价指标，适用于建筑冷热源。",
        )
        hvac_control = make_result(
            "HVAC系统节能控制技术",
            "https://example.com/hvac-control",
            "HVAC系统通过变频水泵、风机和控制策略降低商业建筑能耗。免责声明：仅供参考。",
        )
        heat_recovery = make_result(
            "热回收通风系统应用",
            "https://example.com/heat-recovery",
            "热回收通风可回收排风余热，降低新风处理负荷并提升系统能效。",
        )
        for result in [heat_pump, hvac_control, heat_recovery]:
            result.source_tier = 2
            result.source_tier_label = "产业/企业来源"
            result.source_reliability_score = 6.5

        findings = build_evidence_findings("HVAC", [heat_pump, hvac_control, heat_recovery])
        joined = "\n".join(findings)

        self.assertGreaterEqual(len(findings), 2)
        self.assertLessEqual(len(findings), 4)
        self.assertNotIn("该来源具有产品、平台或案例线索", joined)
        self.assertNotIn("免责声明", joined)
        self.assertIn("HVAC", joined)
        self.assertNotIn("压缩机", joined)

    def test_core_findings_reduce_overlap_by_site_keywords_and_viewpoints(self):
        hvac_scope = make_result(
            "Types of HVAC Systems",
            "https://hvac365.com/types",
            "暖通空调（HVAC）系统覆盖供暖、通风和空调调节环节，在商业建筑中通过冷热源、空气侧和水侧系统实现环境控制，其中评价指标涉及EER。",
        )
        hvac_boundary = make_result(
            "What Is HVAC?",
            "https://hvac.com/guide",
            "暖通空调（HVAC）系统通常包括冷热源、空气侧系统、水侧系统和控制系统，用于建筑环境控制。",
        )
        hvac_datacenter = make_result(
            "HVAC for Data Centers",
            "https://questionsabouthvac.com/datacenter",
            "数据中心暖通空调系统中的设备部件涉及压缩机、水泵、风机，评价指标涉及效率和运行稳定性。",
        )
        hvac_recovery = make_result(
            "HVAC Heat Recovery",
            "https://example.com/recovery",
            "热回收通风关注排风余热和新风处理中的能量回收，可降低冷热源负荷并提升系统能效。",
        )
        for result in [hvac_scope, hvac_boundary, hvac_datacenter, hvac_recovery]:
            result.content = result.snippet
            result.source_tier = 1
            result.source_tier_label = "权威研究来源"
            result.source_reliability_score = 8.0

        findings = build_evidence_findings(
            "HVAC",
            [hvac_scope, hvac_boundary, hvac_datacenter, hvac_recovery],
        )
        joined = "\n".join(findings)

        self.assertGreaterEqual(len(findings), 3)
        self.assertIn("EER", joined)
        self.assertIn("冷热源", joined)
        self.assertIn("数据中心", joined)
        self.assertTrue("热回收" in joined or "新风处理" in joined)
        self.assertLess(joined.count("覆盖供暖、通风和空调调节环节"), 3)


if __name__ == "__main__":
    unittest.main()
