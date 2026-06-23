"""Entrypoint — weekly report over the top voted questions, hardened (Chunk 6).

Cross-cutting: Redis run-lock (no double-publish), semantic dedup, a token/cost
circuit breaker that halts research gracefully, and a Slack notification of the
run result (success / partial / failed / skipped).

Phase 1 (per question): research graph (triage + retry -> swarm -> critic loop
-> validator) collects grounded fact sheets.
Phase 2 (global): analyst (V4-Pro) reasons across all topics, writer (V4-Flash)
renders one cited report -> artifact + Supabase.
"""

import datetime
import os
import sys

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.crosscutting import budget, observability, run_lock
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.layer1_data_entry import dedup_questions, fetch_top_questions
from ssi_blog_agent.layer4_presentation import synthesize, write_report
from ssi_blog_agent.models import AgentStatus, QuestionResearch

ARTIFACT_DIR = "artifacts"
NUM_QUESTIONS = 5


def _run() -> str:
    """Returns run status: success | partial | failed."""
    questions = fetch_top_questions(limit=NUM_QUESTIONS)
    if not questions:
        print("Ei kysymyksiä Supabasessa — ajo keskeytyy.", file=sys.stderr)
        return "failed"

    questions = dedup_questions(questions)
    app = build_graph()
    bundle: list[QuestionResearch] = []
    fallbacks: list[str] = []
    failures: list[str] = []
    budget_hit = False

    # Phase 1 — iterative deep research per question.
    for i, question in enumerate(questions, start=1):
        if budget.exceeded(deepseek.usage_log):
            print(f"  [budget] cap reached (~{budget.estimate_cost_eur(deepseek.usage_log):.2f} EUR)"
                  " — halting further research", file=sys.stderr)
            budget_hit = True
            break
        print(f"[{i}/{len(questions)}] research: {question.text[:60]}...")
        try:
            state = app.invoke({"question": question}, {"recursion_limit": 50})
            bundle.append(QuestionResearch(
                question=question,
                fact_sheets=state.get("fact_sheets", []),
                coverage=state.get("coverage", 0),
                rounds=state.get("research_round", 1),
                validation_note=state.get("validation_note", ""),
            ))
            if state.get("triage_fallback_used"):
                fallbacks.append(question.id)
        except Exception as exc:  # one bad question must not kill the batch
            print(f"  [warn] kysymys epäonnistui: {exc}", file=sys.stderr)
            failures.append(question.id)

    if not bundle:
        return "failed"

    # Phase 2 — global synthesis.
    print("Synthesis: analyst (V4-Pro) + writer (V4-Flash)...")
    try:
        brief = synthesize(bundle)
    except Exception as exc:
        print(f"  [warn] analyst failed, writing without brief: {exc}", file=sys.stderr)
        brief = ""
    report = write_report(bundle, brief)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = os.path.join(ARTIFACT_DIR, f"report_{timestamp}.md")
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(report)
    supabase_client.insert_report(report)

    failed_sheets = sum(1 for qr in bundle for fs in qr.fact_sheets if fs.status == AgentStatus.FAILED)
    total_in = sum(u["input_tokens"] for u in deepseek.usage_log)
    total_out = sum(u["output_tokens"] for u in deepseek.usage_log)
    cost = budget.estimate_cost_eur(deepseek.usage_log)

    print(f"\nArtifact: {artifact_path}")
    print(f"Researched {len(bundle)}/{len(questions)} | fallbacks {len(fallbacks)} | "
          f"failures {len(failures)} | failed sheets {failed_sheets} | budget_hit {budget_hit}")
    print(f"Tokens: {total_in} in / {total_out} out (~{cost:.2f} EUR)")

    degraded = bool(failures or failed_sheets or fallbacks or budget_hit)
    return "partial" if degraded else "success"


def main() -> None:
    if not run_lock.acquire():
        print("Ajo ohitettu: edellinen ajo on yhä kesken (run-lukko).", file=sys.stderr)
        observability.notify("skipped_locked")
        return

    status = "failed"
    detail = ""
    try:
        status = _run()
    except Exception as exc:  # last-resort guard
        detail = str(exc)
        print(f"[fatal] {exc}", file=sys.stderr)
    finally:
        run_lock.release()

    cost = budget.estimate_cost_eur(deepseek.usage_log)
    observability.notify(status, detail=detail or f"~{cost:.2f} EUR, {len(deepseek.usage_log)} LLM-kutsua")
    if status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
