"""Validated research tools (Chunk 0.5): Tavily search + Firecrawl scrape.

Compatibility notes from docs/source_compatibility.md:
- Tyomarkkinatori is a client-rendered SPA -> always pass wait_for >= 8000.
- Alma Media titles (Talouselama, Tekniikka&Talous, Rakennuslehti) are
  excluded by policy; do not scrape them here.
"""

import httpx

from ssi_blog_agent.config import settings


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Returns a list of {title, url, content} result dicts."""
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        },
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


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
