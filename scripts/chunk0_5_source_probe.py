"""Chunk 0.5 — scraping reality check. Throwaway research spike, not
production code. Hits each real target source via Firecrawl/Tavily (or the
real API for Tilastokeskus) and reports what actually comes back.
"""

import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_KEY = os.environ["FIRECRAWL_API_KEY"]
TAVILY_KEY = os.environ["TAVILY_API_KEY"]

SOURCES = [
    {"name": "Tilastokeskus PxWeb API (metadata)", "url": "https://pxdata.stat.fi/PXWeb/api/v1/fi/StatFin/pra", "method": "api"},
    {"name": "Teknologiateollisuus - palkat", "url": "https://teknologiateollisuus.fi/talous-ja-tilastot/tilastot/palkat/", "method": "scrape"},
    {"name": "Teknologiateollisuus - talousnakymat", "url": "https://teknologiateollisuus.fi/talous-ja-tilastot/teknologiateollisuuden-talousnakymat/", "method": "scrape"},
    {"name": "SKOL suhdannekatsaus (index)", "url": "https://teknologiateollisuus.fi/skol/", "method": "scrape"},
    {"name": "RIL main site", "url": "https://ril.fi", "method": "scrape"},
    {"name": "Insinooriliitto IL - palkka-asiat", "url": "https://www.ilry.fi/tyoelaman-tilanteet/palkka-asiat/", "method": "scrape"},
    {"name": "Tyomarkkinatori - avoimet tyopaikat", "url": "https://tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat", "method": "scrape"},
    {"name": "Tekniikka&Talous (paywall test)", "url": "https://www.tekniikkatalous.fi/", "method": "scrape"},
    {"name": "Talouselama (paywall test)", "url": "https://www.talouselama.fi/", "method": "scrape"},
    {"name": "Rakennuslehti (paywall test)", "url": "https://www.rakennuslehti.fi/", "method": "scrape"},
]

TAVILY_QUERIES = [
    "RIL ROTI raportti rakennettu ymparisto PDF",
    "TEM toimialaraportti insinoorit julkaisut.valtioneuvosto.fi",
]


def firecrawl_scrape(url: str) -> dict:
    resp = httpx.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown", "links"]},
        timeout=60,
    )
    return {"status_code": resp.status_code, "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text}


def tavily_search(query: str) -> dict:
    resp = httpx.post(
        "https://api.tavily.com/search",
        headers={"Content-Type": "application/json"},
        json={"api_key": TAVILY_KEY, "query": query, "max_results": 5},
        timeout=30,
    )
    return {"status_code": resp.status_code, "body": resp.json()}


def stat_fi_api(url: str) -> dict:
    resp = httpx.get(url, timeout=30)
    return {"status_code": resp.status_code, "body": resp.json() if resp.status_code == 200 else resp.text}


def summarize_markdown(md: str) -> str:
    cleaned = md.strip().replace("\n", " ")
    return cleaned[:200] + ("..." if len(cleaned) > 200 else "")


def main() -> None:
    results = []

    for source in SOURCES:
        print(f"--- {source['name']} ---")
        try:
            if source["method"] == "api":
                result = stat_fi_api(source["url"])
                print(json.dumps(result["body"], ensure_ascii=False)[:500])
            else:
                result = firecrawl_scrape(source["url"])
                body = result["body"]
                if isinstance(body, dict) and body.get("success"):
                    md = body["data"].get("markdown", "")
                    links = body["data"].get("links", [])
                    print(f"status={result['status_code']} markdown_len={len(md)} links={len(links)}")
                    print(f"preview: {summarize_markdown(md)}")
                    result["markdown_len"] = len(md)
                    result["links_sample"] = links[:15]
                else:
                    print(f"status={result['status_code']} body={json.dumps(body, ensure_ascii=False)[:300]}")
            results.append({"source": source["name"], "url": source["url"], **result})
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({"source": source["name"], "url": source["url"], "error": str(exc)})

        time.sleep(2)
        print()

    print("=== Tavily searches ===")
    for query in TAVILY_QUERIES:
        print(f"--- query: {query} ---")
        try:
            result = tavily_search(query)
            for item in result["body"].get("results", []):
                print(f"  {item['url']}  -- {item['title']}")
            results.append({"source": f"tavily:{query}", **result})
        except Exception as exc:
            print(f"ERROR: {exc}")
        time.sleep(2)
        print()

    out_path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "chunk0_5_probe_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Full results written to {out_path}")


if __name__ == "__main__":
    main()
