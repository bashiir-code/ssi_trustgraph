"""Chunk 4 proof: a forced 429 (rate limit) degrades, not crashes.

Monkeypatches the search layer to raise an HTTP 429 and confirms:
  1. the agent returns a FAILED fact sheet (Partial Success), not an exception;
  2. a mixed batch (one failing agent + one healthy) still produces a
     publishable report via the synthesis layer.

Run: python scripts/test_partial_success.py
"""

import sys

import httpx

from ssi_blog_agent.layer3_research import redis_cache, research_tools
from ssi_blog_agent.layer3_research.oracle import OracleAgent
from ssi_blog_agent.models import AgentStatus, MemberQuestion, QuestionResearch
from ssi_blog_agent import layer4_presentation as pres

# Offline: no cache, no real network.
redis_cache.get_fresh = lambda query: None
redis_cache.put = lambda *a, **k: None


def _force_429(*args, **kwargs):
    request = httpx.Request("POST", "https://api.tavily.com/search")
    response = httpx.Response(429, request=request, text="rate limited")
    raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)


def test_agent_degrades() -> bool:
    research_tools.search_sources = _force_429  # every search 429s
    fs = OracleAgent().research("jokin sääntelykysymys 2026")
    ok = fs.status == AgentStatus.FAILED and "429" in (fs.error or "")
    print(f"  agent on forced 429 -> status={fs.status.value}, "
          f"error~={(fs.error or '')[:40]!r} -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_report_still_publishes() -> bool:
    # One failed sheet + one healthy sheet for the same question.
    from ssi_blog_agent.models import FactSheet

    failed = FactSheet(sub_query="epäonnistunut haku", summary="(epäonnistui)",
                       specialist="oracle", status=AgentStatus.FAILED, error="429")
    healthy = FactSheet(
        sub_query="rakennusalan sääntely 2026",
        summary="EU:n rakennustuoteasetus päivittyy 2026 [virallinen].",
        sources=["https://example.fi/cpr"], specialist="oracle",
    )
    bundle = [QuestionResearch(
        question=MemberQuestion(id="q1", text="Sääntelyn vaikutus 2026?"),
        fact_sheets=[failed, healthy], coverage=60, validation_note="",
    )]

    # Stub the LLM calls so the test is offline.
    pres.deepseek.chat = lambda messages, **kw: "## Analyysi\nSääntely tiukkenee [1]."
    brief = pres.synthesize(bundle)
    report = pres.write_report(bundle, brief)

    ok = bool(report) and "## Lähteet" in report and "[1]" in report
    print(f"  mixed batch -> report length {len(report)}, has bibliography "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> None:
    print("Partial Success proof (forced 429):")
    results = [test_agent_degrades(), test_report_still_publishes()]
    print("ALL PASS" if all(results) else "FAILED")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
