"""LAYER 2 — Triage: DeepSeek V4-Flash purkaa kysymykset Research Chunkeiksi.

Pydantic-validointi pakollisena + Enum-domainit + korjaussilmukka (max 2 yritystä)
+ fallback-pohja, jos jäsennys epäonnistuu toistuvasti.
"""

import uuid

from pydantic import ValidationError

from ssi_blog_agent.config import settings
from ssi_blog_agent.models import Domain, MemberQuestion, ResearchChunk, TriagePlan
from ssi_blog_agent.state import GraphState

TRIAGE_SYSTEM_PROMPT = """Olet triage-avustaja. Pura jäsenkysymykset yksittäisiksi
tutkimusalikyselyiksi (research chunks) ja kategorisoi ne TARKALLEEN yhteen
seuraavista domain-arvoista: construction, industrial, energy, other.
Vastaa AINOASTAAN JSON-skeeman mukaisesti, ei mitään muuta tekstiä."""


def _call_deepseek_triage(question: MemberQuestion, error_feedback: str | None) -> dict:
    """TODO: korvaa oikealla DeepSeek V4-Flash structured-output -kutsulla.

    error_feedback annetaan mallille korjaussilmukassa, jos edellinen yritys
    tuotti virheellisen JSON:in.
    """
    return {
        "chunk_id": str(uuid.uuid4()),
        "question_id": question.id,
        "domain": Domain.OTHER.value,
        "research_prompt": question.text,
    }


def triage_questions(state: GraphState) -> GraphState:
    if state.get("run_locked"):
        return state

    questions = state.get("deduped_questions", [])
    attempts = state.get("triage_attempts", 0)
    error_feedback = state.get("triage_error")

    chunks: list[ResearchChunk] = []
    last_error: str | None = None

    for question in questions:
        try:
            raw = _call_deepseek_triage(question, error_feedback)
            chunks.append(ResearchChunk.model_validate(raw))
        except ValidationError as exc:
            last_error = str(exc)
            if attempts >= settings.triage_max_retries:
                # Fallback-pohja: käsittele manuaalisesti "muu"-kategoriassa.
                chunks.append(
                    ResearchChunk(
                        chunk_id=str(uuid.uuid4()),
                        question_id=question.id,
                        domain=Domain.OTHER,
                        research_prompt=question.text,
                    )
                )

    if last_error and attempts < settings.triage_max_retries:
        return {
            **state,
            "triage_attempts": attempts + 1,
            "triage_error": last_error,
        }

    return {
        **state,
        "triage_plan": TriagePlan(chunks=chunks),
        "triage_error": None,
    }


def triage_needs_retry(state: GraphState) -> str:
    """Conditional edge: palauttaako triage-solmuun vai jatkaako Layer 3:een."""
    if state.get("triage_error") and "triage_plan" not in state:
        return "retry"
    return "continue"
