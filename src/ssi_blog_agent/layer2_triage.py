"""LAYER 2 — Triage with conditional-edge retry loop (Chunk 2 + 3).

DeepSeek V4-Flash breaks one question into focused sub-queries, tags each
with the specialist that should research it (oracle/catalyst/quant), and
picks a strict Enum domain. Raw JSON is validated with Pydantic
(ResearchPlan). On a malformed/invalid response the graph re-prompts Triage
with the error (max 2 attempts), then falls back rather than crashing.

Wiring (see graph.py):
    triage --route_after_triage--> { retry: triage, supervisor, fallback }
    triage_fallback --> supervisor
"""

import json

from pydantic import ValidationError

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import Domain, ResearchPlan, Specialist, SubQuery
from ssi_blog_agent.state import GraphState

MAX_TRIAGE_ATTEMPTS = 2
MAX_SUB_QUERIES = 4  # initial coverage; the critic adds follow-ups per round

TRIAGE_SYSTEM_PROMPT = f"""Olet triage-avustaja suomalaiselle insinöörialan
tutkimusagentille. Pura jäsenkysymys 2-{MAX_SUB_QUERIES} konkreettiseksi,
itsenäiseksi hakukyselyksi. Merkitse jokaiselle paras erikoisagentti:
- "oracle": makro, sääntely, standardit (ISO/EU), toimialatrendit
- "catalyst": teknologiat, työkalut, työnkulut, osaaminen ja kompetenssit
- "quant": palkat, hinnat, kustannukset, numeeriset vertailut

Valitse lisäksi domain TARKALLEEN yhdestä arvosta:
construction, industrial, energy, other.

Vastaa AINOASTAAN JSON-objektina, ei muuta tekstiä:
{{"domain": "<arvo>", "sub_queries": [
  {{"query": "...", "specialist": "oracle|catalyst|quant"}}
]}}"""


def triage(state: GraphState) -> GraphState:
    question = state["question"]
    attempts = state.get("triage_attempts", 0)
    error_feedback = state.get("triage_error")

    messages = [
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": question.text},
    ]
    if error_feedback:
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
        plan = ResearchPlan.model_validate(data)  # Pydantic + Enum checks
        plan.sub_queries = plan.sub_queries[:MAX_SUB_QUERIES]
        # Seed the iterative research loop.
        return {
            **state,
            "research_plan": plan,
            "triage_error": None,
            "pending_sub_queries": plan.sub_queries,
            "fact_sheets": [],
            "researched_keys": set(),
            "research_round": 1,
        }
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
        return "supervisor"
    if state.get("triage_attempts", 0) >= MAX_TRIAGE_ATTEMPTS:
        return "fallback"
    return "retry"


def triage_fallback(state: GraphState) -> GraphState:
    """After max attempts: research the raw question via the Oracle (broad
    macro/context generalist) under domain=other."""
    question = state["question"]
    plan = ResearchPlan(
        domain=Domain.OTHER,
        sub_queries=[SubQuery(query=question.text, specialist=Specialist.ORACLE)],
    )
    return {
        **state,
        "research_plan": plan,
        "triage_fallback_used": True,
        "pending_sub_queries": plan.sub_queries,
        "fact_sheets": [],
        "researched_keys": set(),
        "research_round": 1,
    }
