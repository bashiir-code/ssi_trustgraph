"""Validated research tools (Chunk 0.5): Tavily search + Firecrawl scrape.

Retries transient transport errors and 429/5xx with exponential backoff
(Chunk 4) — free-tier rate limits must degrade, not crash.

Compatibility notes from docs/source_compatibility.md:
- Tyomarkkinatori is a client-rendered SPA -> always pass wait_for >= 8000.
- Alma Media titles (Talouselama, Tekniikka&Talous, Rakennuslehti) are
  excluded by policy; do not scrape them here.
"""

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ssi_blog_agent.config import settings


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


_RETRY = retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception(_is_retryable),
)


@_RETRY
def tavily_search(
    query: str,
    max_results: int = 5,
    include_domains: list[str] | None = None,
    search_depth: str = "basic",
) -> list[dict]:
    """Returns a list of {title, url, content} result dicts.

    include_domains biases results toward authoritative sources (Chunk 3
    specialist source-steering); search_depth="advanced" returns richer
    content per result (deeper research, more credits).
    """
    payload: dict = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
    }
    if include_domains:
        payload["include_domains"] = include_domains

    resp = httpx.post("https://api.tavily.com/search", json=payload, timeout=45)
    resp.raise_for_status()
    return resp.json().get("results", [])


@_RETRY
def firecrawl_scrape(url: str, wait_for: int = 0) -> str:
    """Returns clean markdown for a page. Set wait_for (ms) for JS-heavy SPAs."""
    payload: dict = {"url": url, "formats": ["markdown"]}
    if wait_for:
        payload["waitFor"] = wait_for

    resp = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("markdown", "")
