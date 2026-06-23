"""Deterministic proof that the triage retry loop works (Chunk 2 + 3).

No network: DeepSeek, the research-tools interface and the Qdrant cache are
monkeypatched. We force malformed / invalid triage output and assert the
graph (1) retries up to the max and falls back, and (2) recovers if a later
attempt is valid (with correct specialist routing).

Run: python scripts/test_triage_retry.py
"""

import sys

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.layer3_research import qdrant_cache, research_tools
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.models import Domain, MemberQuestion, Specialist

# --- Neutralise all Layer 3 / 4 network so the test is offline & fast ---
research_tools.search_sources = lambda query, include_domains=None: []
qdrant_cache.get_fresh = lambda query: None
qdrant_cache.put = lambda *a, **k: None
deepseek.chat = lambda messages, **kwargs: "stub-summary-or-report"


def _is_triage(messages) -> bool:
    return any("triage-avustaja" in m.get("content", "") for m in messages)


def _benign_critic() -> dict:
    # High coverage, no follow-ups -> ends the deep-research loop immediately.
    return {"coverage": 100, "gaps": [], "follow_up_queries": []}


Q = MemberQuestion(id="test-1", text="Testikysymys insinöörimarkkinasta?", votes=1)


def scenario_always_bad() -> bool:
    """Every triage attempt malformed -> fallback after MAX_TRIAGE_ATTEMPTS."""
    calls = {"n": 0}

    def bad_chat_json(messages, **kwargs):
        if not _is_triage(messages):
            return _benign_critic()  # critic call -> end loop, don't count
        calls["n"] += 1
        raise ValueError("forced malformed JSON")  # simulates json.loads failure

    deepseek.chat_json = bad_chat_json

    state = build_graph().invoke({"question": Q})
    plan = state["research_plan"]
    ok = (
        calls["n"] == 2
        and state.get("triage_fallback_used") is True
        and plan.domain == Domain.OTHER
        and plan.sub_queries[0].specialist == Specialist.ORACLE
    )
    print(f"  scenario A (always bad): attempts={calls['n']}, "
          f"fallback={state.get('triage_fallback_used')}, domain={plan.domain.value} "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def scenario_bad_then_good() -> bool:
    """First attempt invalid, second valid -> recover with routed sub-queries."""
    calls = {"n": 0}

    def flaky_chat_json(messages, **kwargs):
        if not _is_triage(messages):
            return _benign_critic()  # critic call -> end loop, don't count
        calls["n"] += 1
        if calls["n"] == 1:
            return {"domain": "not_a_real_domain", "sub_queries": []}  # invalid
        return {
            "domain": "industrial",
            "sub_queries": [
                {"query": "palkkakehitys", "specialist": "quant"},
                {"query": "sääntelymuutokset", "specialist": "oracle"},
            ],
        }

    deepseek.chat_json = flaky_chat_json

    state = build_graph().invoke({"question": Q})
    plan = state["research_plan"]
    ok = (
        calls["n"] == 2
        and not state.get("triage_fallback_used")
        and plan.domain == Domain.INDUSTRIAL
        and plan.sub_queries[0].query == "palkkakehitys"
        and plan.sub_queries[0].specialist == Specialist.QUANT
        and plan.sub_queries[1].specialist == Specialist.ORACLE
    )
    print(f"  scenario B (bad then good): attempts={calls['n']}, "
          f"fallback={bool(state.get('triage_fallback_used'))}, "
          f"routed={[sq.specialist.value for sq in plan.sub_queries]} "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> None:
    print("Triage retry-loop proof:")
    results = [scenario_always_bad(), scenario_bad_then_good()]
    print("ALL PASS" if all(results) else "FAILED")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
