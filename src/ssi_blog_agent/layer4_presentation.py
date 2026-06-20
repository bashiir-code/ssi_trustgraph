"""LAYER 4 — Presentation (Chunk 3).

DeepSeek V4-Flash turns the specialists' grounded fact sheets into one
Forbes-style Markdown section with inline citations. Reads only the
compressed summaries + sources from state (pointer pattern keeps raw text in
the scratchpad). State pruning + cohesive multi-question assembly are
refined in Chunk 5.
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.state import GraphState

REPORT_SYSTEM_PROMPT = """Olet talous- ja insinöörialan asiantuntijatoimittaja.
Kirjoita YKSI Forbes-tyylinen markkina-analyysiosio (suomeksi, Markdown)
annetuista faktakoosteista. Vaatimukset:
- skannattava H2-otsikko
- lihavoidut avainhavainnot
- tarvittaessa vertailutaulukko tilastoille
- blockquote yhdelle kriittiselle trendille
- upota lähdeviitteet inline-linkkeinä keskeisten väitteiden yhteyteen
Älä keksi lukuja — käytä vain koosteiden tietoja. Ei raakaa koodia tai
jäsentelemättömiä datadumppeja."""


def _format_fact_sheets(state: GraphState) -> str:
    blocks = []
    for fs in state.get("fact_sheets", []):
        sources = "; ".join(fs.sources) if fs.sources else "(ei lähteitä)"
        tag = f" [{fs.specialist}]" if fs.specialist else ""
        blocks.append(
            f"### Alikysymys{tag}: {fs.sub_query}\n{fs.summary}\n\nLähteet: {sources}"
        )
    return "\n\n".join(blocks)


def write_report(state: GraphState) -> GraphState:
    question = state["question"]
    report = deepseek.chat(
        [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Jäsenkysymys: {question.text}\n\n"
                    f"=== FAKTAKOOSTEET ===\n{_format_fact_sheets(state)}"
                ),
            },
        ]
    )
    return {**state, "final_report": report, "run_status": "success"}
