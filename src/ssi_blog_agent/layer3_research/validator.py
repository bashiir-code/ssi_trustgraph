"""Validator / fact-check node — runs once after the research loop converges.

Critically reviews the question's accumulated research for claims unsupported
by the listed sources, unlabeled extrapolation, and internal contradictions,
and assigns an overall confidence. It does NOT rewrite the research; the note
flows into the synthesis layer so the final report reflects validated
confidence. Defensive: a failure yields an empty note, never a crash.
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.state import GraphState

VALIDATOR_MODEL = "deepseek-v4-flash"  # checking is lighter than analysis

VALIDATOR_SYSTEM_PROMPT = """Olet huolellinen faktantarkistaja. Saat
jäsenkysymyksen ja siihen kerätyt faktakoosteet lähteineen. Tarkista
KRIITTISESTI:
- onko jokin keskeinen väite ilman lähdetukea,
- onko datan yli menevä päättely merkitty (ekstrapolaatio/arvio) vai esitetty
  faktana,
- onko koosteiden välillä sisäisiä ristiriitoja.

ÄLÄ kirjoita tutkimusta uudelleen. Tuota lyhyt (3-6 virkettä) validointihuomio,
joka listaa havaitut heikkoudet ja varauksen aiheet, sekä päätä
KOKONAISLUOTTAMUS: korkea / keskitaso / matala."""


def _format_research(state: GraphState) -> str:
    blocks = []
    for fs in state.get("fact_sheets", []):
        tag = fs.specialist or "?"
        srcs = "; ".join(fs.sources) if fs.sources else "(ei lähteitä)"
        blocks.append(f"### [{tag}] {fs.sub_query}\n{fs.summary}\nLähteet: {srcs}")
    return "\n\n".join(blocks)


def validate(state: GraphState) -> GraphState:
    question = state["question"]
    try:
        note = deepseek.chat(
            [
                {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Jäsenkysymys: {question.text}\n\n"
                        f"=== KERÄTTY TUTKIMUS ===\n{_format_research(state)}"
                    ),
                },
            ],
            model=VALIDATOR_MODEL,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] validator failed: {exc}")
        note = ""
    return {**state, "validation_note": note, "run_status": "success"}
