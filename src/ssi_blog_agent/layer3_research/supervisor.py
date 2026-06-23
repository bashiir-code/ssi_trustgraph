"""Supervisor node (Chunk 3 + iterative loop): researches the CURRENT round's
pending sub-queries, routing each to its specialist, and ACCUMULATES fact
sheets across rounds. Deduplicates against already-researched sub-queries.

Still sequential within a round; concurrency throttling (Chunk 4) and matrix
jobs (Chunk 6) parallelise later.
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
    pending = state.get("pending_sub_queries", [])
    fact_sheets: list[FactSheet] = list(state.get("fact_sheets", []))
    researched: set[str] = set(state.get("researched_keys", set()))

    for sub_query in pending:
        key = sub_query.query.strip().lower()
        if key in researched:
            continue
        agent = _AGENTS[sub_query.specialist]
        fact_sheets.append(agent.research(sub_query.query))
        researched.add(key)

    return {
        **state,
        "fact_sheets": fact_sheets,
        "researched_keys": researched,
        "pending_sub_queries": [],
    }
