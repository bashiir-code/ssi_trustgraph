"""Real Supabase (PostgREST) client over httpx.

Uses the service_role key, which bypasses RLS — keep it server-side only.
"""

import httpx

from ssi_blog_agent.config import settings


def _headers(extra: dict | None = None) -> dict:
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def top_questions(limit: int = 1) -> list[dict]:
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/questions",
        headers=_headers(),
        params={"select": "*", "order": "votes.desc", "limit": str(limit)},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def insert_questions(rows: list[dict]) -> list[dict]:
    resp = httpx.post(
        f"{settings.supabase_url}/rest/v1/questions",
        headers=_headers({"Prefer": "return=representation"}),
        json=rows,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def insert_report(content_md: str) -> list[dict]:
    resp = httpx.post(
        f"{settings.supabase_url}/rest/v1/reports",
        headers=_headers({"Prefer": "return=representation"}),
        json={"content_md": content_md},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
