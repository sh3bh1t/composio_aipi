"""Documentation Discovery Agent.

Crawls documentation URLs for each app, extracts text content,
and produces DiscoveryResult objects for the extraction stage.

Strategy:
1. Build candidate URLs from the hint (domain → docs, developers, api pages)
2. Fetch each URL with timeout + retry
3. Extract clean text using trafilatura
4. Combine and return
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import aiohttp
import trafilatura

from src.config import settings
from src.models import DiscoveredPage, DiscoveryResult

logger = logging.getLogger(__name__)


def build_candidate_urls(hint: str) -> list[str]:
    """Build candidate documentation URLs from an app hint.

    Takes the hint (e.g., 'shopify.dev') and generates likely doc URLs.
    """
    urls: list[str] = []

    # Clean the hint — extract the domain/URL part
    hint_clean = hint.split("(")[0].strip()  # Remove parenthetical notes

    # If hint already looks like a URL path
    if "/" in hint_clean and "." in hint_clean:
        base = hint_clean.rstrip("/")
        if not base.startswith("http"):
            urls.append(f"https://{base}")
        else:
            urls.append(base)
    elif "." in hint_clean:
        # Just a domain
        domain = hint_clean.rstrip("/")
        urls.append(f"https://{domain}")

    # Extract base domain for generating additional URLs
    if urls:
        parsed = urlparse(urls[0])
        domain = parsed.netloc or parsed.path.split("/")[0]
    else:
        domain = hint_clean

    # Generate additional candidate URLs
    domain_clean = domain.replace("www.", "")
    base_domain = ".".join(domain_clean.split(".")[-2:])  # e.g., shopify.dev → shopify.dev

    additional_patterns = [
        f"https://developer.{base_domain}/docs",
        f"https://developers.{base_domain}/docs",
        f"https://developers.{base_domain}",
        f"https://developer.{base_domain}",
        f"https://docs.{base_domain}",
        f"https://api.{base_domain}",
        f"https://{base_domain}/docs",
        f"https://{base_domain}/api",
        f"https://{base_domain}/developers",
    ]

    for url in additional_patterns:
        if url not in urls:
            urls.append(url)

    return urls[:8]  # Cap at 8 candidates to avoid over-fetching


async def fetch_page(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> DiscoveredPage:
    """Fetch a single URL and extract text content."""
    async with semaphore:
        try:
            headers = {"User-Agent": settings.user_agent}
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=settings.crawl_timeout_seconds),
                headers=headers,
                ssl=False,
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return DiscoveredPage(
                        url=url,
                        fetch_success=False,
                        error=f"HTTP {response.status}",
                    )

                html = await response.text(errors="replace")

                # Extract clean text using trafilatura
                text = trafilatura.extract(
                    html,
                    include_links=False,
                    include_tables=True,
                    include_comments=False,
                    favor_recall=True,
                )

                if not text or len(text) < 50:
                    return DiscoveredPage(
                        url=url,
                        fetch_success=False,
                        error="No meaningful content extracted",
                    )

                return DiscoveredPage(
                    url=url,
                    title=_extract_title(html),
                    content_preview=text[:200],
                    content_length=len(text),
                    fetch_success=True,
                )

        except asyncio.TimeoutError:
            return DiscoveredPage(url=url, fetch_success=False, error="Timeout")
        except aiohttp.ClientError as e:
            return DiscoveredPage(url=url, fetch_success=False, error=str(e)[:100])
        except Exception as e:
            return DiscoveredPage(url=url, fetch_success=False, error=str(e)[:100])


async def fetch_page_with_text(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> tuple[DiscoveredPage, str]:
    """Fetch a page and return both the metadata and full extracted text."""
    async with semaphore:
        try:
            headers = {"User-Agent": settings.user_agent}
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=settings.crawl_timeout_seconds),
                headers=headers,
                ssl=False,
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return (
                        DiscoveredPage(url=url, fetch_success=False, error=f"HTTP {response.status}"),
                        "",
                    )

                html = await response.text(errors="replace")
                text = trafilatura.extract(
                    html,
                    include_links=False,
                    include_tables=True,
                    include_comments=False,
                    favor_recall=True,
                ) or ""

                if len(text) < 50:
                    return (
                        DiscoveredPage(url=url, fetch_success=False, error="No content"),
                        "",
                    )

                page = DiscoveredPage(
                    url=url,
                    title=_extract_title(html),
                    content_preview=text[:200],
                    content_length=len(text),
                    fetch_success=True,
                )
                return page, text

        except asyncio.TimeoutError:
            return DiscoveredPage(url=url, fetch_success=False, error="Timeout"), ""
        except Exception as e:
            return DiscoveredPage(url=url, fetch_success=False, error=str(e)[:100]), ""


async def discover_app_docs(
    app_id: int,
    app_name: str,
    hint: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
) -> DiscoveryResult:
    """Discover and fetch documentation for a single app."""
    candidate_urls = build_candidate_urls(hint)
    logger.info(f"[{app_name}] Trying {len(candidate_urls)} candidate URLs")

    tasks = [
        fetch_page_with_text(session, url, semaphore)
        for url in candidate_urls
    ]
    results = await asyncio.gather(*tasks)

    pages: list[DiscoveredPage] = []
    all_text_parts: list[str] = []

    for page, text in results:
        pages.append(page)
        if page.fetch_success and text:
            all_text_parts.append(text)

    combined_text = "\n\n---\n\n".join(all_text_parts)
    successful_pages = [p for p in pages if p.fetch_success]

    result = DiscoveryResult(
        app_id=app_id,
        app_name=app_name,
        hint=hint,
        pages=pages,
        raw_text=combined_text[:50000],  # Cap at 50k chars
        discovery_success=len(successful_pages) > 0,
        total_pages_found=len(successful_pages),
        total_content_length=len(combined_text),
    )

    status = "✓" if result.discovery_success else "✗"
    logger.info(
        f"[{app_name}] {status} Found {result.total_pages_found} pages, "
        f"{result.total_content_length} chars"
    )
    return result


async def discover_all_apps(
    apps: list[dict],
) -> list[DiscoveryResult]:
    """Run doc discovery for all apps concurrently."""
    semaphore = asyncio.Semaphore(settings.max_concurrent_crawls)
    connector = aiohttp.TCPConnector(limit=settings.max_concurrent_crawls, ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            discover_app_docs(
                app_id=app["id"],
                app_name=app["name"],
                hint=app["hint"],
                session=session,
                semaphore=semaphore,
            )
            for app in apps
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions
    final_results: list[DiscoveryResult] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Discovery failed for app {apps[i]['name']}: {result}")
            final_results.append(
                DiscoveryResult(
                    app_id=apps[i]["id"],
                    app_name=apps[i]["name"],
                    hint=apps[i]["hint"],
                    discovery_success=False,
                )
            )
        else:
            final_results.append(result)

    return final_results


def _extract_title(html: str) -> str:
    """Extract page title from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html[:5000], "html.parser")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True)[:100] if title_tag else ""
    except Exception:
        return ""
