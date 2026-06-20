"""LAYER 2 — Triage with conditional-edge retry loop (Chunk 2).

DeepSeek V4-Flash breaks one question into focused sub-queries and a strict
Enum domain. The raw JSON is validated with Pydantic (ResearchPlan). On a
malformed/invalid response the graph re-prompts Triage with the error
message (max 2 attempts), then falls back to domain=other rather than
crashing the run.

Wiring (see graph.py):
    triage --route_after_triage--> { retry: triage, research, fallback }
    triage_fallback --> research
"""

import json

from pydantic import ValidationError

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import Domain, ResearchPlan
from ssi_blog_agent.state import GraphState

MAX_TRIAGE_ATTEMPTS = 2
MAX_SUB_QUERIES = 3

TRIAGE_SYSTEM_PROMPT = f"""Olet triage-avustaja suomalaiselle insinöörialan
tutkimusagentille. Pura jäsenkysymys 2-{MAX_SUB_QUERIES} konkreettiseksi,
itsenäiseksi hakukyselyksi, joilla löytyy tuoretta faktatietoa Suomen
markkinasta. Valitse lisäksi domain TARKALLEEN yhdestä arvosta:
construction, industrial, energy, other.

Vastaa AINOASTAAN JSON-objektina, ei muuta tekstiä:
{{"domain": "<arvo>", "sub_queries": ["...", "..."]}}"""


def triage(state: GraphState) -> GraphState:
    question = state["question"]
    attempts = state.get("triage_attempts", 0)
    error_feedback = state.get("triage_error")

    messages = [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": question.text},
    ]
    if error_feedback:
        # Re-prompt: feed the previous failure back to the model.
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Edellinen yrityksesi oli virheellinen: {error_feedback}. "
                    "Palauta nyt VALIDI JSON tarkalleen pyydetyssä muodossa."
                ),
            }
        )

    try:
        data = deepseek.chat_json(messages)
        plan = ResearchPlan.model_validate(data)  # Pydantic schema + Enum check
        plan.sub_queries = plan.sub_queries[:MAX_SUB_QUERIES]
        return {**state, "research_plan": plan, "triage_error": None}
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        # ValueError covers json.JSONDecodeError (malformed JSON) too.
        return {
            **state,
            "research_plan": None,
            "triage_attempts": attempts + 1,
            "triage_error": str(exc),
        }


def route_after_triage(state: GraphState) -> str:
    if state.get("research_plan") is not None:
        return "research"
    if state.get("triage_attempts", 0) >= MAX_TRIAGE_ATTEMPTS:
        return "fallback"
    return "retry"


def triage_fallback(state: GraphState) -> GraphState:
    """After max attempts: research the raw question under domain=other."""
    question = state["question"]
    plan = ResearchPlan(domain=Domain.OTHER, sub_queries=[question.text])
    return {**state, "research_plan": plan, "triage_fallback_used": True}
