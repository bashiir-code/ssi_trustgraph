"""LAYER 2 — Triage (Chunk 1).

DeepSeek V4-Flash breaks one question into focused sub-queries and picks a
domain. Chunk 1 keeps this simple: try/except + a fallback plan, no
conditional-edge retry loop yet (that arrives in Chunk 2).
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import Domain, ResearchPlan
from ssi_blog_agent.state import GraphState

MAX_SUB_QUERIES = 3

TRIAGE_SYSTEM_PROMPT = f"""Olet triage-avustaja suomalaiselle insinöörialan
tutkimusagentille. Pura jäsenkysymys 2-{MAX_SUB_QUERIES} konkreettiseksi,
itsenäiseksi hakukyselyksi, joilla löytyy tuoretta faktatietoa Suomen
markkinasta. Valitse lisäksi domain TARKALLEEN yhdestä arvosta:
construction, industrial, energy, other.

Vastaa AINOASTAAN JSON-objektina muodossa:
{{"domain": "<arvo>", "sub_queries": ["...", "..."]}}"""


def triage(state: GraphState) -> GraphState:
    question = state["question"]
    try:
        data = deepseek.chat_json(
            [
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": question.text},
            ]
        )
        domain = Domain(data.get("domain", "other"))
        sub_queries = [q for q in data.get("sub_queries", []) if q][:MAX_SUB_QUERIES]
        if not sub_queries:
            raise ValueError("Triage palautti tyhjän sub_queries-listan")
        plan = ResearchPlan(domain=domain, sub_queries=sub_queries)
        return {**state, "research_plan": plan}
    except Exception as exc:
        # Chunk 1: log + degrade to researching the raw question, don't crash.
        plan = ResearchPlan(domain=Domain.OTHER, sub_queries=[question.text])
        return {**state, "research_plan": plan, "error": f"triage fallback: {exc}"}
