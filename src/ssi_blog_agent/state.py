from typing import TypedDict

from ssi_blog_agent.models import FactSheet, MemberQuestion, ResearchPlan


class GraphState(TypedDict, total=False):
    """Per-question graph state (Chunk 2).

    The batch of 5 questions is orchestrated in main.py, which invokes this
    per-question graph once per question. Parallelism / pointer-pattern /
    pruning arrive in later chunks.
    """

    question: MemberQuestion

    # Layer 2 — triage + conditional-edge retry loop
    research_plan: ResearchPlan | None
    triage_attempts: int
    triage_error: str | None
    triage_fallback_used: bool

    # Layer 3 / 4
    fact_sheets: list[FactSheet]
    final_report: str
    run_status: str  # "success" | "failed"
