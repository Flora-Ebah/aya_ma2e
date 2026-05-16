"""Scraper léger pour ma2e.ci (ou tout site institutionnel simple).

Crawl récursif limité au domaine, parse HTML → texte propre, dédoublonne.
Utilise httpx (pas Playwright) — suffisant pour ma2e.ci qui est statique.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; MA2EKnowledgeBot/1.0; "
    "+https://ma2e.ci) AYA assistant ingestion"
)
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Sélecteurs HTML à virer avant extraction texte
NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe",
    "header nav", "footer nav", ".menu", ".navigation", ".navbar",
    ".cookie", ".cookies", "[role=banner]",
]


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str
    content_hash: str
    links: list[str] = field(default_factory=list)


def _clean_text(s: str) -> str:
    """Nettoie un texte brut : espaces multiples, lignes vides redondantes."""
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _extract(html: str, base_url: str) -> tuple[str, str, list[str]]:
    """Retourne (title, plain_text, internal_links)."""
    soup = BeautifulSoup(html, "lxml")

    for sel in NOISE_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Préserver les <h*> en les forçant en lignes distinctes
    for hx in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
        hx.insert_before("\n\n")
        hx.insert_after("\n")
    for p in soup.find_all(["p", "li"]):
        p.insert_after("\n")

    text = soup.get_text()
    text = _clean_text(text)

    # Liens internes
    links: list[str] = []
    base_host = urlparse(base_url).netloc
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)
        if urlparse(absolute).netloc.endswith(base_host):
            links.append(absolute)

    return title, text, links


def _is_skippable_url(url: str) -> bool:
    """Filtre les ressources non-textuelles."""
    lower = url.lower()
    BAD_EXT = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".css", ".js", ".pdf", ".zip", ".mp4", ".mp3", ".woff", ".woff2",
    )
    return any(lower.endswith(ext) for ext in BAD_EXT)


async def crawl_site(
    start_url: str,
    *,
    max_pages: int = 50,
    same_host_only: bool = True,
) -> list[ScrapedPage]:
    """Crawl récursif simple (BFS) sur le même domaine.

    Retourne la liste des pages avec leur texte extrait.
    """
    start_host = urlparse(start_url).netloc
    queue: list[str] = [start_url]
    seen: set[str] = set()
    pages: list[ScrapedPage] = []

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
    ) as client:
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            url, _ = urldefrag(url)
            if url in seen or _is_skippable_url(url):
                continue
            seen.add(url)
            if same_host_only and not urlparse(url).netloc.endswith(start_host):
                continue

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.warning("skip %s -> %s", url, resp.status_code)
                    continue
                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type.lower():
                    continue
                title, text, links = _extract(resp.text, url)
                if len(text) < 80:  # page trop pauvre, on saute
                    continue
                page = ScrapedPage(
                    url=url,
                    title=title or url,
                    text=text,
                    content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    links=list(dict.fromkeys(links)),
                )
                pages.append(page)
                log.info("[scrape %d/%d] %s (%d chars, %d links)", len(pages), max_pages, url, len(text), len(links))
                # Empile les liens internes
                for link in page.links:
                    if link not in seen:
                        queue.append(link)
            except Exception as e:
                log.warning("scrape failed %s: %s", url, e)
            await asyncio.sleep(0.2)  # politesse, ne pas marteler le site

    return pages
