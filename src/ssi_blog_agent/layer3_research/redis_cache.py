"""Upstash Redis 7-day research cache (Chunk 4).

Exact-match freshness cache keyed by the normalised sub-query: before any
external search, reuse a result researched in the last 7 days. Native TTL
key-value is the right tool for this (replaces the placeholder-vector Qdrant
cache; Qdrant returns for real semantic dedup in Chunk 6). Degrades
gracefully — a cache outage must never crash research.
"""

import hashlib
import json

import httpx

from ssi_blog_agent.config import settings

TTL_SECONDS = settings.cache_freshness_days * 24 * 3600  # 7 days
_KEY_PREFIX = "ssi:research:"


def _key(query: str) -> str:
    digest = hashlib.sha1(query.strip().lower().encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}{digest}"


def _command(command: list) -> dict | None:
    if not settings.upstash_redis_url or not settings.upstash_redis_token:
        return None
    resp = httpx.post(
        settings.upstash_redis_url,
        headers={"Authorization": f"Bearer {settings.upstash_redis_token}"},
        json=command,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_fresh(query: str) -> dict | None:
    """Return cached {summary, sources, doc_id} if researched < 7 days ago."""
    try:
        data = _command(["GET", _key(query)])
        if not data or data.get("result") is None:
            return None
        return json.loads(data["result"])
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] redis get failed: {exc}")
        return None


def put(query: str, summary: str, sources: list[str], doc_id: str | None) -> None:
    try:
        payload = json.dumps({"summary": summary, "sources": sources, "doc_id": doc_id})
        _command(["SET", _key(query), payload, "EX", str(TTL_SECONDS)])
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] redis put failed: {exc}")
