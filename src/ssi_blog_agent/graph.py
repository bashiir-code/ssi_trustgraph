"""LangGraph wiring — per-question graph (Chunk 2).

triage --(conditional)--> { retry -> triage, research, fallback -> research }
research -> write_report -> END

The conditional edge after triage is the JSON-robustness retry loop. The
batch of 5 questions is looped over this graph in main.py (still sequential;
parallel matrix jobs come in Chunk 6).
"""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.layer2_triage import route_after_triage, triage, triage_fallback
from ssi_blog_agent.layer3_research.single_agent import research
from ssi_blog_agent.layer4_presentation import write_report
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("triage", triage)
    graph.add_node("triage_fallback", triage_fallback)
    graph.add_node("research", research)
    graph.add_node("write_report", write_report)

    graph.set_entry_point("triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "retry": "triage",
            "research": "research",
            "fallback": "triage_fallback",
        },
    )
    graph.add_edge("triage_fallback", "research")
    graph.add_edge("research", "write_report")
    graph.add_edge("write_report", END)

    return graph.compile()
