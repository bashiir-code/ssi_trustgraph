"""LangGraph wiring — Chunk 1 vertical slice.

fetch_top_question -> triage -> research (single agent) -> write_report.
Linear, no retry loop / swarm / cross-cutting yet; those arrive in later
chunks.
"""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.layer1_data_entry import fetch_top_question
from ssi_blog_agent.layer2_triage import triage
from ssi_blog_agent.layer3_research.single_agent import research
from ssi_blog_agent.layer4_presentation import write_report
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("fetch_top_question", fetch_top_question)
    graph.add_node("triage", triage)
    graph.add_node("research", research)
    graph.add_node("write_report", write_report)

    graph.set_entry_point("fetch_top_question")
    graph.add_edge("fetch_top_question", "triage")
    graph.add_edge("triage", "research")
    graph.add_edge("research", "write_report")
    graph.add_edge("write_report", END)

    return graph.compile()
