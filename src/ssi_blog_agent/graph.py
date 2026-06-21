"""LangGraph wiring — per-question RESEARCH graph (Chunk 3 + analyst layer).

triage --(conditional)--> { retry -> triage, supervisor, fallback -> supervisor }
supervisor -> END

This graph now stops at research (fact sheets). Report writing moved OUT of
the per-question loop into a global two-stage synthesis layer (analyst +
writer) that runs once over ALL questions' fact sheets — see
layer4_presentation.py and main.py. That global view is what enables
cross-sectional reasoning instead of 5 siloed summaries.
"""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.layer2_triage import route_after_triage, triage, triage_fallback
from ssi_blog_agent.layer3_research.supervisor import supervise
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("triage", triage)
    graph.add_node("triage_fallback", triage_fallback)
    graph.add_node("supervisor", supervise)

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
    graph.add_edge("supervisor", END)

    return graph.compile()
