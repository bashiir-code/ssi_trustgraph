"""LangGraph wiring — per-question ITERATIVE deep-research graph.

triage --(conditional)--> { retry -> triage, supervisor, fallback -> supervisor }
supervisor -> critic
critic --(conditional)--> { research_more -> supervisor, validate -> validator }
validator -> END

The triage->retry edge is the JSON-robustness loop. The supervisor<->critic
edge is the agentic deep-research loop: research -> gap analysis -> research
more, until coverage is sufficient or the round cap (critic.MAX_RESEARCH_ROUNDS)
is hit. The validator fact-checks before synthesis. Report writing is the
global analyst+writer pass in main.py / layer4_presentation.py.
"""

from langgraph.graph import END, StateGraph

from ssi_blog_agent.layer2_triage import route_after_triage, triage, triage_fallback
from ssi_blog_agent.layer3_research.critic import critique, route_after_critic
from ssi_blog_agent.layer3_research.supervisor import supervise
from ssi_blog_agent.layer3_research.validator import validate
from ssi_blog_agent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("triage", triage)
    graph.add_node("triage_fallback", triage_fallback)
    graph.add_node("supervisor", supervise)
    graph.add_node("critic", critique)
    graph.add_node("validator", validate)

    graph.set_entry_point("triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"retry": "triage", "supervisor": "supervisor", "fallback": "triage_fallback"},
    )
    graph.add_edge("triage_fallback", "supervisor")
    graph.add_edge("supervisor", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"research_more": "supervisor", "validate": "validator"},
    )
    graph.add_edge("validator", END)

    return graph.compile()
