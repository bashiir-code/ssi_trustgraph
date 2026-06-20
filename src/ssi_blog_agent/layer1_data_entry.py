"""LAYER 1 — Data Entry (Chunk 2).

Fetch the top-N voted member questions from Supabase. Dedup and run-lock
arrive in Chunk 6; the per-question graph is invoked once per question by
the orchestrator in main.py.
"""

from ssi_blog_agent.clients import supabase_client
from ssi_blog_agent.models import MemberQuestion


def fetch_top_questions(limit: int = 5) -> list[MemberQuestion]:
    rows = supabase_client.top_questions(limit=limit)
    return [
        MemberQuestion(id=str(row["id"]), text=row["text"], votes=row.get("votes", 0))
        for row in rows
    ]
