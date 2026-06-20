"""Chunk 1 vertical-slice entrypoint.

Runs the LangGraph pipeline for the single top-voted question, then writes
the report to a local artifact and the Supabase reports table.
"""

import datetime
import os
import sys

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.graph import build_graph

ARTIFACT_DIR = "artifacts"


def main() -> None:
    app = build_graph()
    final_state = app.invoke({})

    report = final_state.get("final_report")
    if final_state.get("error"):
        print(f"[warn] {final_state['error']}", file=sys.stderr)

    if not report:
        print("Raporttia ei syntynyt — ajo epäonnistui.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = os.path.join(ARTIFACT_DIR, f"report_{timestamp}.md")
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Artifact written: {artifact_path}")

    supabase_client.insert_report(report)
    print("Supabase: report inserted")

    total_in = sum(u["input_tokens"] for u in deepseek.usage_log)
    total_out = sum(u["output_tokens"] for u in deepseek.usage_log)
    print(f"Token usage: {total_in} in / {total_out} out across {len(deepseek.usage_log)} calls")

    print("\n--- REPORT ---\n")
    print(report)


if __name__ == "__main__":
    main()
