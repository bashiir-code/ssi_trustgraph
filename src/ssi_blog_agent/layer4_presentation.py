"""LAYER 4 — Presentation: koostaa faktakoosteet Forbes-tyyliseksi raportiksi.

State Pruning: vain lopulliset tiivistelmät + lähde-ID:t siirtyvät tähän
kerrokseen, ei raakaa Layer 3 -välidataa, jotta input-tokenit pysyvät minimissä.
"""

from ssi_blog_agent.models import AgentResult, AgentStatus
from ssi_blog_agent.state import GraphState

REPORT_SYSTEM_PROMPT = """Olet asiantuntijatoimittaja. Kirjoita Forbes-tyylinen
markkina-analyysiraportti annetuista faktakoosteista. Käytä skannattavia
otsikoita, lihavoituja avainhavaintoja, vertailutaulukoita tilastoille ja
blockquoteja kriittisille trendeille. Upota lähdeviite (linkki) jokaisen
keskeisen tilastoluvun yhteyteen. Ei raakaa koodia tai jäsentelemättömiä
datadumppeja."""


def _prune_state_for_presentation(results: list[AgentResult]) -> list[dict]:
    pruned = []
    for result in results:
        if result.status == AgentStatus.FAILED:
            pruned.append({"agent": result.agent_name, "status": "failed", "error": result.error})
            continue
        pruned.append(
            {
                "agent": result.agent_name,
                "status": "ok",
                "facts": [
                    {"fact": f.fact, "source_url": f.source_url} for f in result.facts
                ],
            }
        )
    return pruned


def _call_deepseek_presentation(pruned_facts: list[dict]) -> str:
    """TODO: korvaa oikealla DeepSeek V4-Flash-kutsulla (raskas raakateksti),
    valinnaisesti V4-Pro-loppusilaus editointiin."""
    lines = ["# Viikon insinöörimarkkina-analyysi\n"]
    for item in pruned_facts:
        if item["status"] == "failed":
            lines.append(
                f"> ⚠️ Tietoja **{item['agent']}**-osa-alueelta ei saatu tällä "
                f"viikolla: {item['error']}\n"
            )
        else:
            for fact in item["facts"]:
                lines.append(f"- {fact['fact']} ([lähde]({fact['source_url']}))")
    return "\n".join(lines)


def write_report(state: GraphState) -> GraphState:
    if state.get("run_locked"):
        return state

    results = state.get("agent_results", [])
    pruned = _prune_state_for_presentation(results)
    report = _call_deepseek_presentation(pruned)

    any_failed = any(r.status == AgentStatus.FAILED for r in results)
    run_status = "partial" if any_failed else "success"

    return {**state, "report_markdown": report, "run_status": run_status}
