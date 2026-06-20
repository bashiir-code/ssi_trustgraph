"""Deterministic proof that the Chunk 2 triage retry loop works.

No network: DeepSeek and Tavily are monkeypatched. We force malformed /
invalid triage output and assert the graph (1) retries up to the max and
falls back to domain=other, and (2) recovers if a later attempt is valid.

Run: python scripts/test_triage_retry.py
"""

import sys

from ssi_blog_agent.clients import deepseek, search
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.models import Domain, MemberQuestion

# --- Neutralise Layer 3 / 4 network calls so the test is offline & fast ---
search.tavily_search = lambda query, max_results=4: []
deepseek.chat = lambda messages, **kwargs: "stub-summary-or-report"

Q = MemberQuestion(id="test-1", text="Testikysymys insinöörimarkkinasta?", votes=1)


def scenario_always_bad() -> bool:
    """Every triage attempt returns malformed JSON -> expect fallback to OTHER
    after exactly MAX_TRIAGE_ATTEMPTS attempts."""
    calls = {"n": 0}

    def bad_chat_json(messages, **kwargs):
        calls["n"] += 1
        raise ValueError("forced malformed JSON")  # simulates json.loads failure

    deepseek.chat_json = bad_chat_json

    state = build_graph().invoke({"question": Q})
    plan = state["research_plan"]

    ok = (
        calls["n"] == 2  # MAX_TRIAGE_ATTEMPTS
        and state.get("triage_fallback_used") is True
        and plan.domain == Domain.OTHER
    )
    print(f"  scenario A (always bad): attempts={calls['n']}, "
          f"fallback={state.get('triage_fallback_used')}, domain={plan.domain.value} "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def scenario_bad_then_good() -> bool:
    """First attempt invalid, second attempt valid -> expect recovery with the
    valid plan and no fallback."""
    calls = {"n": 0}

    def flaky_chat_json(messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"domain": "not_a_real_domain", "sub_queries": []}  # invalid
        return {"domain": "energy", "sub_queries": ["palkkakehitys", "rekrytointi"]}

    deepseek.chat_json = flaky_chat_json

    state = build_graph().invoke({"question": Q})
    plan = state["research_plan"]

    ok = (
        calls["n"] == 2
        and not state.get("triage_fallback_used")
        and plan.domain == Domain.ENERGY
        and plan.sub_queries == ["palkkakehitys", "rekrytointi"]
    )
    print(f"  scenario B (bad then good): attempts={calls['n']}, "
          f"fallback={bool(state.get('triage_fallback_used'))}, domain={plan.domain.value} "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> None:
    print("Triage retry-loop proof:")
    results = [scenario_always_bad(), scenario_bad_then_good()]
    if all(results):
        print("ALL PASS")
    else:
        print("FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
