"""LAYER 1 — Data Entry: fetch member questions, dedup, run-lock."""

import uuid

from ssi_blog_agent.config import settings
from ssi_blog_agent.models import MemberQuestion
from ssi_blog_agent.state import GraphState

RUN_LOCK_KEY = "ssi_blog_agent:run_in_progress"


def acquire_run_lock(state: GraphState) -> GraphState:
    """Estää päällekkäiset ajot (tupla-cron / manuaalinen ajo kesken edellisen).

    TODO: korvaa Supabase/Redis SETNX-lukolla tuotannossa.
    """
    locked = False  # placeholder: lookup RUN_LOCK_KEY
    if locked:
        return {**state, "run_locked": True, "run_status": "skipped_locked"}
    return {**state, "run_locked": False}


def fetch_member_questions(state: GraphState) -> GraphState:
    """Hakee 5 kriittisintä/eniten ääniä saanutta kysymystä Supabasesta.

    TODO: korvaa oikealla Supabase-kyselyllä (settings.supabase_url/service_key).
    """
    if state.get("run_locked"):
        return state

    raw = [
        MemberQuestion(id=str(uuid.uuid4()), text="placeholder question", votes=0)
        for _ in range(5)
    ]
    return {**state, "raw_questions": raw}


def dedup_questions(state: GraphState) -> GraphState:
    """Semanttinen dedup-tarkistus (embedding-cosine) ennen Triagea.

    TODO: laske embeddingit ja yhdistä/karsi kysymykset, joiden cosine-similarity
    ylittää kynnysarvon (esim. 0.9), jotta lähes identtiset kysymykset eivät
    tuplaa Research-kerroksen kustannuksia.
    """
    if state.get("run_locked"):
        return state

    raw = state.get("raw_questions", [])
    return {**state, "deduped_questions": raw}
