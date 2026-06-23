"""LAYER 1 — Data Entry (Chunk 2).

Fetch the top-N voted member questions from Supabase. Dedup and run-lock
arrive in Chunk 6; the per-question graph is invoked once per question by
the orchestrator in main.py.
"""

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.models import MemberQuestion


def fetch_top_questions(limit: int = 5) -> list[MemberQuestion]:
    rows = supabase_client.top_questions(limit=limit)
    return [
        MemberQuestion(id=str(row["id"]), text=row["text"], votes=row.get("votes", 0))
        for row in rows
    ]


_DEDUP_PROMPT = """Tunnista lähes identtiset jäsenkysymykset (sama aihe/ydin).
Palauta säilytettävien kysymysten indeksit: poista päällekkäiset niin että
kustakin samankaltaisten ryhmästä jää YKSI (mieluiten kattavin). Säilytä kaikki
aidosti erilaiset. Vastaa AINOASTAAN JSON-objektina: {"keep": [indeksit]}"""


def dedup_questions(questions: list[MemberQuestion]) -> list[MemberQuestion]:
    """Semantic dedup before triage so near-duplicate weekly questions don't
    double-spend in research. LLM-based (Flash, cheap, no embeddings dep);
    degrades to no-op on any failure."""
    if len(questions) < 2:
        return questions
    listing = "\n".join(f"{i}: {q.text}" for i, q in enumerate(questions))
    try:
        data = deepseek.chat_json(
            [
                {"role": "system", "content": _DEDUP_PROMPT},
                {"role": "user", "content": listing},
            ]
        )
        keep = sorted({int(i) for i in data.get("keep", []) if 0 <= int(i) < len(questions)})
        if not keep:
            return questions
        deduped = [questions[i] for i in keep]
        if len(deduped) < len(questions):
            print(f"  dedup: {len(questions)} -> {len(deduped)} questions")
        return deduped
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] dedup failed (using all questions): {exc}")
        return questions
