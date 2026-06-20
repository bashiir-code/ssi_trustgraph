from typing import TypedDict

from ssi_blog_agent.models import AgentResult, MemberQuestion, TriagePlan


class GraphState(TypedDict, total=False):
    # Layer 1
    raw_questions: list[MemberQuestion]
    deduped_questions: list[MemberQuestion]
    run_locked: bool

    # Layer 2
    triage_plan: TriagePlan
    triage_attempts: int
    triage_error: str | None

    # Layer 3
    agent_results: list[AgentResult]

    # Layer 4
    report_markdown: str

    # Cross-cutting
    run_cost_eur: float
    budget_exceeded: bool
    run_status: str  # "success" | "partial" | "failed"
