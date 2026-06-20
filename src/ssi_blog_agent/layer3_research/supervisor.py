"""Supervisor-node: jakaa research chunkit Oracle/Catalyst/Quant-agenteille.

Concurrency control: rajoitettu rinnakkaisuus + viive käynnistysten välillä,
jotta ilmaistason API-kiintiöt (Firecrawl/Tavily/Qdrant) eivät laukea 429:ää.
Tuotannossa GitHub Actions matrix-strategia ajaa yhden chunkin per job —
tämä supervisor vastaa yhden chunkin sisäisestä agenttien koordinoinnista
(tai paikallisesta ajosta matrix-jobien ulkopuolella).
"""

from concurrent.futures import ThreadPoolExecutor

from ssi_blog_agent.layer3_research.catalyst import CatalystAgent
from ssi_blog_agent.layer3_research.oracle import OracleAgent
from ssi_blog_agent.layer3_research.quant import QuantAgent
from ssi_blog_agent.state import GraphState

MAX_CONCURRENCY = 2
AGENTS = [OracleAgent(), CatalystAgent(), QuantAgent()]


def run_research_swarm(state: GraphState) -> GraphState:
    if state.get("run_locked"):
        return state

    plan = state.get("triage_plan")
    if plan is None:
        return state

    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
        futures = [
            pool.submit(agent.run, chunk)
            for chunk in plan.chunks
            for agent in AGENTS
        ]
        for future in futures:
            results.append(future.result())

    return {**state, "agent_results": results}
