from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..models import SearchQuery
from ..security import normalize_public_url

PAGE_PATHS = {
    "home": "",
    "about": "/about",
    "about_tr": "/hakkimizda",
    "contact": "/contact",
    "contact_tr": "/iletisim",
    "careers": "/careers",
    "jobs": "/jobs",
    "services": "/services",
    "team": "/team",
    "blog": "/blog",
}
PUBLIC_SECTOR_KEYWORDS = (
    "universite",
    "university",
    "belediye",
    "bakanligi",
    "bakanlik",
    "ministry",
    "okulu",
    "koleji",
    "meslek yuksekokulu",
    "devlet",
    "valiligi",
)
IRRELEVANT_CATEGORY_KEYWORDS = (
    "okul",
    "universite",
    "belediye",
    "kamu",
)
HIRING_KEYWORDS = (
    "kariyer",
    "career",
    "join our team",
    "acik pozisyon",
    "job opening",
    "we are hiring",
    "basvuru",
    "developer",
    "frontend",
    "backend",
    "software engineer",
    "full stack",
)
DIGITAL_NEED_KEYWORDS = (
    "rezervasyon",
    "online",
    "randevu",
    "e-ticaret",
    "siparis",
    "crm",
    "erp",
    "mobil uygulama",
    "web uygulama",
    "entegrasyon",
    "automation",
    "otomasyon",
    "customer portal",
    "booking",
)
TECH_SUPPLY_KEYWORDS = (
    "yazilim",
    "software",
    "digital agency",
    "web tasarim",
    "mobil uygulama",
    "it consulting",
)
TITLE_PATTERNS = (
    "founder",
    "kurucu",
    "ceo",
    "cto",
    "co-founder",
    "ik",
    "human resources",
    "hr",
    "talent",
    "muhendislik muduru",
    "engineering manager",
)
TECH_STACK_FOOTPRINTS = {
    "React": ["react", "react-dom"],
    "Next.js": ["__next", "_next/static"],
    "Vue.js": ["data-v-", "vue@"],
    "Nuxt.js": ["__nuxt__"],
    "WordPress": ["wp-content", "wp-includes"],
    "PHP": [".php"],
    "Shopify": ["cdn.shopify.com"],
    "AWS": ["amazonaws.com"],
    "Cloudflare": ["cloudflare"],
    "Google Analytics": ["google-analytics.com", "gtag"],
    "Tailwind CSS": ["tailwind"],
    "Bootstrap": ["bootstrap"],
    "jQuery": ["jquery"],
    "Webflow": ["cdn.webflow.com"],
    "Wix": ["cdn.wix.com"],
}

@dataclass(slots=True)
class ResearchBundle:
    visited_urls: list[str]
    page_texts: dict[str, str]
    combined_text: str
    hiring_signal_score: int
    digital_need_score: int
    company_size_guess: str
    decision_maker_candidates: list[str]
    detected_tech_stack: list[str]
    has_active_job_board_postings: bool
    weak_signal: bool


def reject_company_candidate(company: dict[str, str | None], query: SearchQuery) -> str | None:
    haystack = " ".join(
        [
            company.get("name") or "",
            company.get("category") or "",
            query.sector,
        ]
    ).lower()
    if any(keyword in haystack for keyword in PUBLIC_SECTOR_KEYWORDS):
        return "Kamu veya egitim kurumu elendi."
    category = (company.get("category") or "").lower()
    if any(keyword in category for keyword in IRRELEVANT_CATEGORY_KEYWORDS):
        return "Kategori hedef disi."
    if not (company.get("website") or "").strip():
        return "Website sinyali zayif."
    return None


async def _check_job_boards(company_name: str) -> bool:
    if not company_name:
        return False
    url = "https://html.duckduckgo.com/html/"
    query = f"site:linkedin.com/jobs OR site:kariyer.net {company_name}"
    try:
        async with httpx.AsyncClient(timeout=6.0, headers=_headers()) as client:
            response = await client.post(url, data={"q": query})
            if response.status_code == 200:
                html = response.text.lower()
                soup = BeautifulSoup(html, "html.parser")
                snippets = soup.find_all(class_="result__snippet")
                for snip in snippets:
                    text = snip.get_text().lower()
                    if "iş ilanı" in text or "job" in text or "hiring" in text or "iş ilanları" in text:
                        return True
    except Exception:
        pass
    return False


async def enrich_company_website(url: str | None, company_name: str | None = None) -> ResearchBundle:
    has_jobs = await _check_job_boards(company_name) if company_name else False
    if not url:
        return ResearchBundle([], {}, "", 0, 0, "bilinmiyor", [], [], has_jobs, True)

    normalized = normalize_public_url(url)
    visited_urls: list[str] = []
    page_texts: dict[str, str] = {}
    decision_makers: list[str] = []
    detected_tech = set()

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=_headers()) as client:
        for name, suffix in PAGE_PATHS.items():
            page_url = normalized if not suffix else urljoin(normalized.rstrip("/") + "/", suffix.lstrip("/"))
            if page_url in visited_urls:
                continue
            try:
                response = await client.get(page_url)
                response.raise_for_status()
            except Exception:
                continue
            visited_urls.append(page_url)
            
            html_content = response.text
            lowered_html = html_content.lower()
            for tech, footprints in TECH_STACK_FOOTPRINTS.items():
                if any(fp in lowered_html for fp in footprints):
                    detected_tech.add(tech)
                    
            text, candidates = _extract_page_insights(html_content)
            if text:
                page_texts[name] = text[:2200]
            for candidate in candidates:
                if candidate not in decision_makers:
                    decision_makers.append(candidate)

    combined_text = "\n\n".join(text for text in page_texts.values() if text).strip()
    lowered = combined_text.lower()
    hiring_signal_score = _score_hits(lowered, HIRING_KEYWORDS, 18)
    digital_need_score = _score_digital_need(lowered)
    company_size_guess = _guess_company_size(lowered, len(page_texts))
    weak_signal = not combined_text or len(combined_text) < 300
    return ResearchBundle(
        visited_urls=visited_urls,
        page_texts=page_texts,
        combined_text=combined_text[:7000],
        hiring_signal_score=hiring_signal_score,
        digital_need_score=digital_need_score,
        company_size_guess=company_size_guess,
        decision_maker_candidates=decision_makers[:5],
        detected_tech_stack=sorted(list(detected_tech)),
        has_active_job_board_postings=has_jobs,
        weak_signal=weak_signal,
    )


def _extract_page_insights(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "img", "svg"]):
        tag.decompose()
    text_block = soup.get_text(separator="\n", strip=True)
    cleaned_text = re.sub(r"\s+", " ", text_block).strip()
    candidates: list[str] = []
    raw_lines = [line.strip() for line in text_block.splitlines() if line.strip()]
    for line in raw_lines:
        lowered = line.lower()
        if any(pattern in lowered for pattern in TITLE_PATTERNS):
            normalized = " ".join(line.split())
            if normalized not in candidates:
                candidates.append(normalized[:140])
        if "@" in line and any(pattern in lowered for pattern in TITLE_PATTERNS):
            normalized = " ".join(line.split())
            if normalized not in candidates:
                candidates.append(normalized[:140])
    return cleaned_text, candidates


def _score_hits(text: str, keywords: tuple[str, ...], weight: int) -> int:
    hits = sum(1 for keyword in keywords if keyword in text)
    return min(100, hits * weight)


def _score_digital_need(text: str) -> int:
    demand_hits = sum(1 for keyword in DIGITAL_NEED_KEYWORDS if keyword in text)
    supply_hits = sum(1 for keyword in TECH_SUPPLY_KEYWORDS if keyword in text)
    score = min(100, demand_hits * 16 + max(0, 2 - supply_hits) * 10)
    if supply_hits >= 3:
        score = max(15, score - 25)
    return score


def _guess_company_size(text: str, page_count: int) -> str:
    if any(keyword in text for keyword in ("enterprise", "kurumsal", "global", "holding", "group")):
        return "kurumsal"
    if any(keyword in text for keyword in ("10+", "20+", "ekibimiz", "our team", "team")) or page_count >= 4:
        return "orta"
    return "kucuk"


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }
