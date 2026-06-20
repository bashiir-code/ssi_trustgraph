"""LAYER 1 — Data Entry (Chunk 1).

Fetch the single top-voted member question from Supabase. Dedup, run-lock
and the 5-question batch come in later chunks.
"""

from ssi_blog_agent.clients import supabase_client
from ssi_blog_agent.models import MemberQuestion
from ssi_blog_agent.state import GraphState


def fetch_top_question(state: GraphState) -> GraphState:
    rows = supabase_client.top_questions(limit=1)
    if not rows:
        return {
            **state,
            "error": "Ei kysymyksiä Supabasen questions-taulussa",
            "run_status": "failed",
        }

    row = rows[0]
    question = MemberQuestion(
        id=str(row["id"]), text=row["text"], votes=row.get("votes", 0)
    )
    return {**state, "question": question}
