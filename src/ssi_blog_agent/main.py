"""Entrypoint — weekly report over the top 5 voted questions.

Phase 1 (per question): run the research graph (triage + retry -> swarm)
to collect grounded fact sheets.
Phase 2 (global, once): analyst (V4-Pro) reasons across ALL topics, then the
writer (V4-Flash) renders one coherent expert report. Output -> local
artifact + Supabase reports table.
"""

import datetime
import os
import sys

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.layer1_data_entry import fetch_top_questions
from ssi_blog_agent.layer4_presentation import synthesize, write_report
from ssi_blog_agent.models import AgentStatus, QuestionResearch

ARTIFACT_DIR = "artifacts"
NUM_QUESTIONS = 5


def main() -> None:
    questions = fetch_top_questions(limit=NUM_QUESTIONS)
    if not questions:
        print("Ei kysymyksiä Supabasessa — ajo keskeytyy.", file=sys.stderr)
        sys.exit(1)

    app = build_graph()
    bundle: list[QuestionResearch] = []
    fallbacks: list[str] = []
    failures: list[str] = []

    # Phase 1 — iterative deep research per question (sequential; Chunk 4 adds
    # throttling). Each question loops research -> critic -> research more.
    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] research: {question.text[:65]}...")
        try:
            state = app.invoke({"question": question}, {"recursion_limit": 50})
            sheets = state.get("fact_sheets", [])
            rounds = state.get("research_round", 1)
            coverage = state.get("coverage", 0)
            bundle.append(
                QuestionResearch(
                    question=question,
                    fact_sheets=sheets,
                    coverage=coverage,
                    rounds=rounds,
                    validation_note=state.get("validation_note", ""),
                )
            )
            print(f"  -> {len(sheets)} fact sheets, {rounds} round(s), coverage {coverage}%")
            if state.get("triage_fallback_used"):
                fallbacks.append(question.id)
        except Exception as exc:  # one bad question must not kill the batch
            print(f"  [warn] kysymys epäonnistui: {exc}", file=sys.stderr)
            failures.append(question.id)

    if not bundle:
        print("Yksikään kysymys ei tuottanut tutkimusta — ajo epäonnistui.", file=sys.stderr)
        sys.exit(1)

    # Phase 2 — global synthesis (analyst -> writer).
    print("Synthesis: analyst (V4-Pro) reasoning across all topics...")
    try:
        analyst_brief = synthesize(bundle)
    except Exception as exc:
        print(f"  [warn] analyst pass failed, writing without brief: {exc}", file=sys.stderr)
        analyst_brief = ""

    print("Synthesis: writer (V4-Flash) composing report...")
    report = write_report(bundle, analyst_brief)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = os.path.join(ARTIFACT_DIR, f"report_{timestamp}.md")
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(report)

    supabase_client.insert_report(report)

    total_in = sum(u["input_tokens"] for u in deepseek.usage_log)
    total_out = sum(u["output_tokens"] for u in deepseek.usage_log)
    failed_sheets = sum(
        1 for qr in bundle for fs in qr.fact_sheets if fs.status == AgentStatus.FAILED
    )

    print(f"\nArtifact: {artifact_path}")
    print("Supabase: report inserted")
    print(f"Researched: {len(bundle)}/{len(questions)} | "
          f"triage fallbacks: {len(fallbacks)} | question failures: {len(failures)} | "
          f"failed fact sheets (degraded): {failed_sheets}")
    print(f"Token usage: {total_in} in / {total_out} out across {len(deepseek.usage_log)} calls")


if __name__ == "__main__":
    main()
