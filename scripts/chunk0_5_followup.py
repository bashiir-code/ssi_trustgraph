"""Chunk 0.5 follow-up: PDF extraction, Tyomarkkinatori JS rendering,
paywall depth on a real article, and a deliberate 429 stress test.
Throwaway research spike.
"""

import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_KEY = os.environ["FIRECRAWL_API_KEY"]


def firecrawl_scrape(url: str, **extra) -> dict:
    payload = {"url": url, "formats": ["markdown"]}
    payload.update(extra)
    resp = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    return {"status_code": resp.status_code, "body": resp.json()}


def test_pdf_extraction():
    print("=== 1. PDF extraction: RIL ROTI 2025 report ===")
    url = "https://ril.fi/wp-content/uploads/2025/03/ROTI-raportti_2025_low_Suojattu.pdf"
    result = firecrawl_scrape(url)
    body = result["body"]
    if body.get("success"):
        md = body["data"].get("markdown", "")
        print(f"status={result['status_code']} markdown_len={len(md)}")
        print(f"preview: {md[:400]}")
    else:
        print(f"FAILED: {json.dumps(body, ensure_ascii=False)[:400]}")
    print()


def test_tyomarkkinatori_wait():
    print("=== 2. Tyomarkkinatori with waitFor=8000ms ===")
    url = "https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat"
    result = firecrawl_scrape(url, waitFor=8000)
    body = result["body"]
    if body.get("success"):
        md = body["data"].get("markdown", "")
        print(f"status={result['status_code']} markdown_len={len(md)}")
        print(f"preview: {md[:400]}")
    else:
        print(f"FAILED: {json.dumps(body, ensure_ascii=False)[:400]}")
    print()


def test_paywall_article():
    print("=== 3. Paywall depth: a real Talouselama subscriber article ===")
    # Real article link extracted from the Chunk 0.5 homepage scrape's
    # links_sample (artifacts/chunk0_5_probe_results.json), not guessed.
    url = "https://www.talouselama.fi/uutiset/a/8ff14509-01d8-45fd-b760-69924a3d33aa"
    result = firecrawl_scrape(url)
    body = result["body"]
    if body.get("success"):
        md = body["data"].get("markdown", "")
        print(f"status={result['status_code']} markdown_len={len(md)}")
        print(f"preview: {md[:600]}")
    else:
        print(f"FAILED: {json.dumps(body, ensure_ascii=False)[:400]}")
    print()


def test_rate_limit():
    print("=== 4. Deliberate rate-limit stress test (10 rapid calls, no sleep) ===")
    url = "https://example.com"
    for i in range(10):
        try:
            resp = httpx.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
                json={"url": url},
                timeout=30,
            )
            print(f"  call {i+1}: HTTP {resp.status_code}")
            if resp.status_code == 429:
                print(f"  429 body: {resp.text[:300]}")
                print(f"  429 headers: retry-after={resp.headers.get('retry-after')}, "
                      f"x-ratelimit-remaining={resp.headers.get('x-ratelimit-remaining')}")
        except Exception as exc:
            print(f"  call {i+1}: ERROR {exc}")
    print()


if __name__ == "__main__":
    test_pdf_extraction()
    test_tyomarkkinatori_wait()
    test_paywall_article()
    test_rate_limit()
