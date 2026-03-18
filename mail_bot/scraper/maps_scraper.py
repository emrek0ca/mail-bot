from __future__ import annotations

import asyncio
import inspect
import os
import random
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus

from ..models import IntegrationCheckResult

from ..models import SearchQuery

GOOGLE_MAPS_URL = "https://www.google.com/maps/search/{query}"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
_INSTALL_LOCK = threading.Lock()


async def search_companies(
    query: SearchQuery,
    on_company: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
) -> list[dict[str, Any]]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright kurulu degil.\n"
            "Terminalde `pip install playwright && playwright install chromium` calistirin."
        ) from exc

    try:
        await ensure_chromium_installed()
    except Exception as exc:
        msg = f"Tarayici (Chromium) baslatilamadi: {exc}"
        if sys.platform.startswith("linux"):
            msg += "\nSistem bagimliliklari eksik olabilir. 'sudo npx playwright install-deps' calistirmayi deneyin."
        raise RuntimeError(msg) from exc

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    search_url = GOOGLE_MAPS_URL.format(query=quote_plus(query.query_text))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=CHROME_USER_AGENT, viewport={"width": 1440, "height": 960})
        page = await context.new_page()
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2500)
            feed = page.locator('div[role="feed"]')
            processed_count = 0
            stale_passes = 0

            while len(results) < query.limit and stale_passes < 5:
                cards = page.locator('div[role="article"]')
                card_count = await cards.count()
                if processed_count >= card_count:
                    stale_passes += 1
                    await _scroll_results(feed)
                    continue

                for index in range(processed_count, card_count):
                    if len(results) >= query.limit:
                        break
                    card = cards.nth(index)
                    try:
                        await card.click(timeout=10000)
                        await page.wait_for_timeout(int(random.uniform(800, 2200)))
                        company = await _extract_company(page, query.city)
                    except PlaywrightTimeoutError:
                        continue
                    if not company.get("name"):
                        continue
                    dedupe_key = (company["name"].strip().lower(), company.get("website"))
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append(company)
                    if on_company:
                        callback_result = on_company(company)
                        if inspect.isawaitable(callback_result):
                            await callback_result
                    if len(results) % 10 == 0:
                        await asyncio.sleep(random.uniform(3, 6))
                processed_count = card_count
                await _scroll_results(feed)
                stale_passes = 0
        finally:
            await context.close()
            await browser.close()

    return results


async def validate_playwright_setup() -> IntegrationCheckResult:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        return IntegrationCheckResult("playwright", False, "Playwright kurulu degil.")  # pragma: no cover

    try:
        await ensure_chromium_installed()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=CHROME_USER_AGENT, viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            await page.goto("https://www.google.com/maps", wait_until="domcontentloaded", timeout=20000)
            title = await page.title()
            await context.close()
            await browser.close()
            return IntegrationCheckResult("playwright", True, f"Playwright hazir. Sayfa basligi: {title[:80]}")
    except Exception as exc:
        return IntegrationCheckResult("playwright", False, f"Playwright tarayici acilamadi: {exc}")


async def ensure_chromium_installed() -> None:
    if _has_installed_browser():
        return
    await asyncio.to_thread(_install_chromium)


def _has_installed_browser() -> bool:
    browser_root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")).expanduser()
    if not browser_root.exists():
        return False
    return any(path.is_dir() and path.name.startswith("chromium-") for path in browser_root.iterdir())


def _install_chromium() -> None:
    with _INSTALL_LOCK:
        if _has_installed_browser():
            return
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        driver_executable, driver_cli = compute_driver_executable()
        completed = subprocess.run(
            [driver_executable, driver_cli, "install", "chromium"],
            env=get_driver_env(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "Chromium kurulumu basarisiz."
            raise RuntimeError(stderr)


async def _extract_company(page: Any, fallback_city: str) -> dict[str, Any]:
    return {
        "name": await _text(page, ('h1.DUwDvf', 'div.fontHeadlineLarge', '[data-attrid="title"]', 'h1 span')),
        "address": await _text(page, ('button[data-item-id="address"]', 'div.Io6YTe.fontBodyMedium', '[data-item-id="address"]')),
        "phone": await _text(page, ('button[data-item-id^="phone"]', 'button[data-tooltip*="Telefon"]', 'div.QSv61c')),
        "website": await _attr(page, ('a[data-item-id="authority"]', 'a[aria-label*="Web sitesi"]', 'a[href*="http"]'), "href"),
        "category": await _text(page, ('button[jsaction*="pane.rating.category"]', 'span.DkEaL', 'div.fontBodyMedium span')),
        "city": fallback_city,
    }


async def _text(page: Any, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count() == 0:
                continue
            value = await locator.inner_text(timeout=1500)
            cleaned = " ".join(value.split()).strip()
            if cleaned:
                return cleaned
        except Exception:
            continue
    return None


async def _attr(page: Any, selectors: tuple[str, ...], name: str) -> str | None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count() == 0:
                continue
            value = await locator.get_attribute(name, timeout=1500)
            if value:
                return value.strip()
        except Exception:
            continue
    return None


async def _scroll_results(feed: Any) -> None:
    try:
        await feed.evaluate("(node) => node.scrollBy(0, node.scrollHeight)")
        await asyncio.sleep(random.uniform(1.0, 1.8))
    except Exception:
        await asyncio.sleep(1.2)
