"""Supervisor node (Chunk 3): reads the triage plan and routes each sub-query
to the specialist tagged for it (oracle/catalyst/quant), collecting the
resulting fact sheets.

Still sequential within a question; concurrency throttling (Chunk 4) and
matrix jobs (Chunk 6) parallelise later.
"""

from ssi_blog_agent.layer3_research.catalyst import CatalystAgent
from ssi_blog_agent.layer3_research.oracle import OracleAgent
from ssi_blog_agent.layer3_research.quant import QuantAgent
from ssi_blog_agent.models import FactSheet, Specialist
from ssi_blog_agent.state import GraphState

_AGENTS = {
    Specialist.ORACLE: OracleAgent(),
    Specialist.CATALYST: CatalystAgent(),
    Specialist.QUANT: QuantAgent(),
}


def supervise(state: GraphState) -> GraphState:
    plan = state["research_plan"]
    fact_sheets: list[FactSheet] = []

    for sub_query in plan.sub_queries:
        agent = _AGENTS[sub_query.specialist]
        fact_sheets.append(agent.research(sub_query.query))

    return {**state, "fact_sheets": fact_sheets}
