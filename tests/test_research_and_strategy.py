from __future__ import annotations

import unittest

from mail_bot.ai.lead_strategy import LeadStrategy, fallback_strategy, parse_lead_strategy_output
from mail_bot.models import CompanyRecord, SearchQuery, Settings
from mail_bot.scraper.company_research import ResearchBundle, reject_company_candidate


class ResearchAndStrategyTests(unittest.TestCase):
    def test_public_institution_is_rejected(self) -> None:
        reason = reject_company_candidate(
            {"name": "Ankara Universitesi", "category": "Universite", "website": "https://example.com"},
            SearchQuery(sector="yazilim", city="Ankara"),
        )
        self.assertIsNotNone(reason)

    def test_unclear_strategy_is_clamped_below_recommended_threshold(self) -> None:
        fallback = LeadStrategy(
            lead_type="unclear",
            fit_score=60,
            fit_reasons=["Karisik sinyal"],
            company_summary="Ozet",
            research_summary="Ozet",
            recommended_profile_variant="Odak",
            recommended_cta="CTA",
            routing_reason="Karisik",
            value_prop_brief="Brief",
            recommended_reference_project="Proje",
            mail_subject="Konu",
            mail_body="Govde",
            recommended_attachment_key="all"
        )
        parsed = parse_lead_strategy_output(
            '{"lead_type":"unclear","fit_score":95,"fit_reasons":["x"],"company_summary":"o","research_summary":"o","recommended_profile_variant":"p","recommended_cta":"c","routing_reason":"r","value_prop_brief":"b","recommended_reference_project":"pr","mail_subject":"konu","mail_body":"govde"}',
            fallback,
        )
        self.assertEqual(parsed.lead_type, "unclear")
        self.assertLess(parsed.fit_score, 70)

    def test_fallback_strategy_prefers_job_when_hiring_signal_high(self) -> None:
        company = CompanyRecord(id=1, name="Acme", city="Istanbul", category="Yazilim")
        settings = Settings(user_name="Emre", user_title="Developer", target_roles="Backend Developer")
        strategy = fallback_strategy(
            company,
            settings,
            SearchQuery(sector="yazilim", city="Istanbul"),
            ResearchBundle(
                visited_urls=["https://example.com"],
                page_texts={"home": "we are hiring backend developer"},
                combined_text="we are hiring backend developer",
                hiring_signal_score=80,
                digital_need_score=20,
                company_size_guess="orta",
                decision_maker_candidates=["CTO"],
                detected_tech_stack=[],
                has_active_job_board_postings=False,
                weak_signal=False,
            ),
        )
        self.assertEqual(strategy.lead_type, "job")
        self.assertGreaterEqual(strategy.fit_score, 70)
