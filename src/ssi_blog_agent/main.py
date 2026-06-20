"""Chunk 2 entrypoint — process the top 5 voted questions sequentially.

For each question: run the per-question graph (triage + retry loop ->
research -> report section). Combine the 5 sections into one weekly report,
write it to a local artifact and the Supabase reports table.
"""

import datetime
import os
import sys

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.layer1_data_entry import fetch_top_questions

ARTIFACT_DIR = "artifacts"
NUM_QUESTIONS = 5


def main() -> None:
    questions = fetch_top_questions(limit=NUM_QUESTIONS)
    if not questions:
        print("Ei kysymyksiä Supabasessa — ajo keskeytyy.", file=sys.stderr)
        sys.exit(1)

    app = build_graph()
    sections: list[str] = []
    fallbacks: list[str] = []
    failures: list[str] = []

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.text[:70]}...")
        try:
            state = app.invoke({"question": question})
            sections.append(state["final_report"])
            if state.get("triage_fallback_used"):
                fallbacks.append(question.id)
        except Exception as exc:  # one bad question must not kill the batch
            print(f"  [warn] kysymys epäonnistui: {exc}", file=sys.stderr)
            failures.append(question.id)

    if not sections:
        print("Yksikään kysymys ei tuottanut osiota — ajo epäonnistui.", file=sys.stderr)
        sys.exit(1)

    date_str = datetime.date.today().isoformat()
    header = (
        f"# Viikon insinöörimarkkina-analyysi\n\n"
        f"_{len(sections)} jäsenkysymystä · {date_str}_\n"
    )
    report = header + "\n" + "\n\n---\n\n".join(sections)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = os.path.join(ARTIFACT_DIR, f"report_{timestamp}.md")
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(report)

    supabase_client.insert_report(report)

    total_in = sum(u["input_tokens"] for u in deepseek.usage_log)
    total_out = sum(u["output_tokens"] for u in deepseek.usage_log)

    print(f"\nArtifact: {artifact_path}")
    print("Supabase: report inserted")
    print(f"Sections: {len(sections)}/{len(questions)} | "
          f"triage fallbacks: {len(fallbacks)} | failures: {len(failures)}")
    print(f"Token usage: {total_in} in / {total_out} out across {len(deepseek.usage_log)} calls")


if __name__ == "__main__":
    main()
