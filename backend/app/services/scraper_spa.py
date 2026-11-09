"""Scraper SPA basé sur Playwright (Chromium headless).

Utilisé quand le site cible est une SPA (React/Vue/Angular) dont le HTML
initial ne contient aucun texte utile. Playwright rend la page comme un
vrai navigateur, puis on extrait le DOM après rendu JS.

Sous Windows, uvicorn tourne souvent avec SelectorEventLoop qui n'accepte
pas `subprocess_exec` → Playwright plante avec NotImplementedError. On
contourne en exécutant tout le crawl Playwright dans un thread dédié avec
une ProactorEventLoop à nous. Le résultat (liste de pages) est renvoyé via
une queue async.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
import threading
from typing import AsyncIterator
from urllib.parse import urldefrag, urlparse

from app.services.scraper import ScrapedPage, _clean_text, _extract, _is_skippable_url

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MA2EKnowledgeBot/1.0"
)

_SENTINEL = object()


async def _playwright_crawl_inner(start_url, max_pages, same_host_only, wait_after_load_ms, out_queue):
    """Boucle Playwright. Pousse chaque page dans la queue partagée."""
    from playwright.async_api import async_playwright

    start_host = urlparse(start_url).netloc
    queue: list[str] = [start_url]
    seen: set[str] = set()
    yielded = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=USER_AGENT,
                locale="fr-FR",
                ignore_https_errors=True,
            )
            page = await context.new_page()

            while queue and yielded < max_pages:
                url = queue.pop(0)
                url, _ = urldefrag(url)
                if url in seen or _is_skippable_url(url):
                    continue
                seen.add(url)
                if same_host_only and not urlparse(url).netloc.endswith(start_host):
                    continue

                try:
                    resp = await page.goto(url, wait_until="networkidle", timeout=30_000)
                    if resp is None or resp.status >= 400:
                        continue
                    await page.wait_for_timeout(wait_after_load_ms)
                    html = await page.content()
                    title, text, links = _extract(html, url)
                    if len(text) < 40:
                        continue

                    scraped = ScrapedPage(
                        url=url,
                        title=title or url,
                        text=_clean_text(text),
                        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        links=list(dict.fromkeys(links)),
                    )
                    yielded += 1
                    log.info("[spa %d/%d] %s (%d chars)", yielded, max_pages, url, len(text))
                    out_queue.put_nowait(scraped)

                    for link in scraped.links:
                        if link not in seen:
                            queue.append(link)
                except Exception as e:
                    log.warning("spa scrape failed %s: %s", url, e)

                await asyncio.sleep(0.2)
        finally:
            await browser.close()


def _run_in_thread(start_url, max_pages, same_host_only, wait_after_load_ms, loop, async_queue):
    """Thread worker : nouvelle event loop Proactor + run Playwright, puis
    pousse chaque page vers la queue de la loop principale."""
    def _put(item):
        loop.call_soon_threadsafe(async_queue.put_nowait, item)

    class _Shim:
        def put_nowait(self, item):
            _put(item)

    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        inner_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(inner_loop)
        try:
            inner_loop.run_until_complete(
                _playwright_crawl_inner(start_url, max_pages, same_host_only, wait_after_load_ms, _Shim())
            )
        finally:
            inner_loop.close()
    except Exception as e:
        log.exception("playwright thread crashed: %s", e)
    finally:
        loop.call_soon_threadsafe(async_queue.put_nowait, _SENTINEL)


async def crawl_site_spa_iter(
    start_url: str,
    *,
    max_pages: int = 50,
    same_host_only: bool = True,
    wait_after_load_ms: int = 1500,
) -> AsyncIterator[ScrapedPage]:
    """Crawl BFS avec rendu JS complet (Playwright, thread isolé)."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        log.error("playwright non installé — pip install playwright && playwright install chromium")
        return

    loop = asyncio.get_running_loop()
    async_queue: asyncio.Queue = asyncio.Queue()
    thread = threading.Thread(
        target=_run_in_thread,
        args=(start_url, max_pages, same_host_only, wait_after_load_ms, loop, async_queue),
        daemon=True,
    )
    thread.start()

    while True:
        item = await async_queue.get()
        if item is _SENTINEL:
            break
        yield item
