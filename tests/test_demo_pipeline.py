"""End-to-end: the whole agent system in offline demo mode (no API keys).

Runs the real LangGraph pipeline against the deterministic fakes in
ssi_blog_agent/demo.py and asserts the agentic behaviour: dedup, the triage
retry loop, specialist routing, the critic follow-up round, the validator,
official-data-first citations, the run-lock and cost accounting.
"""

import pytest

from ssi_blog_agent import demo, main
from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.crosscutting import budget, run_lock
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.models import MemberQuestion

demo.install()


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    demo.reset()
    monkeypatch.chdir(tmp_path)  # main writes artifacts/ relative to cwd


def _question(qid: str) -> MemberQuestion:
    return MemberQuestion(**next(q for q in demo.QUESTIONS if q["id"] == qid))


def test_full_run_publishes_cited_report(tmp_path):
    assert main._run() == "success"

    report = demo.STORE["reports"][-1]
    assert report.startswith("# ")
    assert "## Lähteet" in report and "[1]" in report
    assert "Paljonko" not in report  # near-duplicate question removed by dedup
    assert list(tmp_path.glob("artifacts/report_*.md"))
    assert budget.estimate_cost_eur(deepseek.usage_log) > 0


def test_critic_loop_routes_to_specialists_and_cites_official_data_first():
    state = build_graph().invoke({"question": _question("q1")})

    sheets = state["fact_sheets"]
    assert {"quant", "oracle"} <= {fs.specialist for fs in sheets}
    # The critic's follow-up query was researched in a second round.
    assert any("prosentteina" in fs.sub_query for fs in sheets)
    assert state["validation_note"]
    quant = next(fs for fs in sheets if fs.specialist == "quant")
    assert quant.sources[0] == demo.STATFI_URL


def test_triage_retry_recovers_from_invalid_plan():
    state = build_graph().invoke({"question": _question("q2")})

    assert state["triage_attempts"] == 1  # first plan rejected by Pydantic
    assert not state.get("triage_fallback_used")
    assert {sq.specialist.value for sq in state["research_plan"].sub_queries} == {"oracle", "catalyst"}


def test_run_lock_blocks_overlapping_run():
    assert run_lock.acquire()
    assert not run_lock.acquire()
    run_lock.release()
    assert run_lock.acquire()
    run_lock.release()
