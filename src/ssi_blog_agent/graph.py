"""LangGraph-tilakoneen kokoaminen: L1 -> L2 (retry loop) -> L3 -> L4 -> notify."""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.crosscutting.observability import notify_run_result
from ssi_blog_agent.layer1_data_entry import (
    acquire_run_lock,
    dedup_questions,
    fetch_member_questions,
)
from ssi_blog_agent.layer2_triage import triage_needs_retry, triage_questions
from ssi_blog_agent.layer3_research.supervisor import run_research_swarm
from ssi_blog_agent.layer4_presentation import write_report
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("acquire_run_lock", acquire_run_lock)
    graph.add_node("fetch_member_questions", fetch_member_questions)
    graph.add_node("dedup_questions", dedup_questions)
    graph.add_node("triage_questions", triage_questions)
    graph.add_node("run_research_swarm", run_research_swarm)
    graph.add_node("write_report", write_report)
    graph.add_node("notify_run_result", notify_run_result)

    graph.set_entry_point("acquire_run_lock")
    graph.add_edge("acquire_run_lock", "fetch_member_questions")
    graph.add_edge("fetch_member_questions", "dedup_questions")
    graph.add_edge("dedup_questions", "triage_questions")

    graph.add_conditional_edges(
        "triage_questions",
        triage_needs_retry,
        {"retry": "triage_questions", "continue": "run_research_swarm"},
    )

    graph.add_edge("run_research_swarm", "write_report")
    graph.add_edge("write_report", "notify_run_result")
    graph.add_edge("notify_run_result", END)

    return graph.compile()
