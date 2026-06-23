from typing import TypedDict

from ssi_blog_agent.models import FactSheet, MemberQuestion, ResearchPlan, SubQuery


class GraphState(TypedDict, total=False):
    """Per-question graph state — iterative deep-research loop.

    plan(triage) -> research(supervisor) -> critic(gap analysis)
                 -> [research more | validate] -> END

    The batch of 5 questions is looped over this graph in main.py.
    """

    question: MemberQuestion

    # Layer 2 — triage + conditional-edge retry loop
    research_plan: ResearchPlan | None
    triage_attempts: int
    triage_error: str | None
    triage_fallback_used: bool

    # Layer 3 — iterative research loop
    pending_sub_queries: list[SubQuery]  # what the supervisor researches next
    researched_keys: set[str]  # normalised sub-queries already done (dedup)
    fact_sheets: list[FactSheet]  # accumulated across rounds
    research_round: int
    coverage: int  # critic's latest coverage estimate (0-100)
    validation_note: str  # validator's fact-check note

    run_status: str
