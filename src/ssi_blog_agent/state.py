from typing import TypedDict

from ssi_blog_agent.models import FactSheet, MemberQuestion, ResearchPlan


class GraphState(TypedDict, total=False):
    """Chunk 1 vertical-slice state. Grows into the full multi-question
    state (with pointer pattern / pruning) in later chunks."""

    question: MemberQuestion
    research_plan: ResearchPlan
    fact_sheets: list[FactSheet]
    final_report: str
    error: str | None
    run_status: str  # "success" | "failed"
