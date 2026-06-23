"""Critic / gap-analysis node — the engine of the iterative deep-research loop.

After each research round it reviews everything gathered for the question,
scores coverage, and proposes specialist-tagged FOLLOW-UP queries to fill gaps
and resolve contradictions. The graph loops back to the supervisor to research
those, until coverage is sufficient or the round cap is hit. Defensive: any
failure ends the loop cleanly rather than crashing the run.
"""

from pydantic import ValidationError

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import CriticAssessment
from ssi_blog_agent.state import GraphState

CRITIC_MODEL = "deepseek-v4-pro"
MAX_RESEARCH_ROUNDS = 3
COVERAGE_THRESHOLD = 85
MAX_FOLLOWUPS_PER_ROUND = 3

CRITIC_SYSTEM_PROMPT = """Olet tutkimuksen kriitikko. Saat jäsenkysymyksen ja
siihen tähän mennessä kerätyt faktakoosteet lähteineen. Arvioi KRIITTISESTI:
- kuinka kattavasti kysymykseen on vastattu (0-100),
- mitkä KONKREETTISET faktat, luvut tai näkökulmat puuttuvat tai ovat heikosti
  tuettuja (nimeä ne täsmällisesti, älä yleisluontoisesti),
- mitkä lähteiden väliset RISTIRIIDAT vaativat lisäselvitystä.

Ehdota TÄSMÄLLISIÄ, FOKUSOITUJA jatkohakuja, jotka täyttävät nimetyn aukon
yhdellä konkreettisella faktalla/luvulla. Vältä päällekkäisyyttä jo tehtyjen
hakujen kanssa ja suosi auktoritatiivisia lähteitä (Tilastokeskus, viranomaiset,
toimialajärjestöt). Merkitse kullekin paras erikoisagentti: "oracle"
(sääntely/makro/standardit), "catalyst" (teknologia/työkalut/osaaminen),
"quant" (palkat/hinnat/numerot).

Jos kattavuus on jo korkea (>= 85) eikä olennaisia aukkoja ole, palauta tyhjä
follow_up_queries-lista.

Vastaa AINOASTAAN JSON-objektina:
{"coverage": <int 0-100>, "gaps": ["..."],
 "follow_up_queries": [{"query": "...", "specialist": "oracle|catalyst|quant"}]}"""


def _format_research(state: GraphState) -> str:
    blocks = []
    for fs in state.get("fact_sheets", []):
        tag = fs.specialist or "?"
        blocks.append(f"### [{tag}] {fs.sub_query}\n{fs.summary}")
    return "\n\n".join(blocks)


def critique(state: GraphState) -> GraphState:
    round_n = state.get("research_round", 1)

    # Hard stop at the round cap regardless of model output.
    if round_n >= MAX_RESEARCH_ROUNDS:
        return {**state, "pending_sub_queries": []}

    question = state["question"]
    try:
        data = deepseek.chat_json(
            [
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Jäsenkysymys: {question.text}\n\n"
                        f"=== KERÄTTY TUTKIMUS (kierros {round_n}) ===\n"
                        f"{_format_research(state)}"
                    ),
                },
            ],
            model=CRITIC_MODEL,
        )
        assessment = CriticAssessment.model_validate(data)
    except (ValidationError, ValueError, Exception) as exc:  # noqa: BLE001
        print(f"  [warn] critic failed, ending loop: {exc}")
        return {**state, "pending_sub_queries": []}

    researched = state.get("researched_keys", set())
    follow_ups = [
        sq
        for sq in assessment.follow_up_queries
        if sq.query.strip().lower() not in researched
    ][:MAX_FOLLOWUPS_PER_ROUND]

    if assessment.coverage >= COVERAGE_THRESHOLD:
        follow_ups = []

    return {
        **state,
        "pending_sub_queries": follow_ups,
        "coverage": assessment.coverage,
        "research_round": round_n + 1,
    }


def route_after_critic(state: GraphState) -> str:
    return "research_more" if state.get("pending_sub_queries") else "validate"
