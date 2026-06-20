"""LangGraph wiring — per-question graph (Chunk 3 swarm).

triage --(conditional)--> { retry -> triage, supervisor, fallback -> supervisor }
supervisor -> write_report -> END

The conditional edge after triage is the JSON-robustness retry loop. The
supervisor routes each sub-query to its specialist (Oracle/Catalyst/Quant).
The batch of 5 questions is looped over this graph in main.py.
"""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.layer2_triage import route_after_triage, triage, triage_fallback
from ssi_blog_agent.layer3_research.supervisor import supervise
from ssi_blog_agent.layer4_presentation import write_report
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("triage", triage)
    graph.add_node("triage_fallback", triage_fallback)
    graph.add_node("supervisor", supervise)
    graph.add_node("write_report", write_report)

    graph.set_entry_point("triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "retry": "triage",
            "supervisor": "supervisor",
            "fallback": "triage_fallback",
        },
    )
    graph.add_edge("triage_fallback", "supervisor")
    graph.add_edge("supervisor", "write_report")
    graph.add_edge("write_report", END)

    return graph.compile()
