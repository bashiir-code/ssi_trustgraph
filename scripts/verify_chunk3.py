"""Chunk 3 definition-of-done check.

Runs a civil/regulatory question and a salary question through the swarm and
reports:
  1. Supervisor routing — which specialist handled each sub-query.
  2. State size (token estimate) — proves the pointer pattern keeps state small.
  3. Pointer-pattern compression — raw scratchpad chars vs state summary chars
     (only if the research_scratchpad table exists).

Run: python scripts/verify_chunk3.py
"""

from ssi_blog_agent.clients import deepseek, supabase_client
from ssi_blog_agent.graph import build_graph
from ssi_blog_agent.layer1_data_entry import fetch_top_questions


def est_tokens(text: str) -> int:
    return len(text) // 4  # rough chars/4 heuristic


def pick(questions, keyword):
    for q in questions:
        if keyword in q.text.lower():
            return q
    return None


def main() -> None:
    questions = fetch_top_questions(limit=10)
    salary_q = pick(questions, "palkk")
    reg_q = pick(questions, "sääntely")
    if not salary_q or not reg_q:
        raise SystemExit("Need a salary ('palkk') and a regulatory ('sääntely') question seeded.")

    app = build_graph()
    all_specialists: set[str] = set()

    for label, q in [("SALARY", salary_q), ("REGULATORY", reg_q)]:
        deepseek.usage_log.clear()
        state = app.invoke({"question": q})
        fact_sheets = state["fact_sheets"]

        print(f"\n=== {label} QUESTION ===")
        print(f"  {q.text[:90]}")
        print("  Supervisor routing:")
        for fs in fact_sheets:
            all_specialists.add(fs.specialist)
            print(f"    - [{fs.specialist:8}] cache_hit={fs.cache_hit} "
                  f"sources={len(fs.sources)} :: {fs.sub_query[:60]}")

        state_chars = sum(len(fs.summary) for fs in fact_sheets)
        in_tok = sum(u["input_tokens"] for u in deepseek.usage_log)
        out_tok = sum(u["output_tokens"] for u in deepseek.usage_log)
        print(f"  State (summaries) ~= {est_tokens(' '.join(fs.summary for fs in fact_sheets))} tokens "
              f"({state_chars} chars)")
        print(f"  LLM token usage this question: {in_tok} in / {out_tok} out")

        doc_ids = [fs.doc_id for fs in fact_sheets if fs.doc_id]
        rows = supabase_client.get_scratchpad(doc_ids)
        if rows:
            raw_chars = sum(len(r["raw_content"]) for r in rows)
            ratio = raw_chars / max(state_chars, 1)
            print(f"  Pointer pattern: {raw_chars} raw chars in scratchpad vs "
                  f"{state_chars} summary chars in state -> {ratio:.1f}x kept out of state")
        else:
            print("  Pointer pattern: scratchpad rows not found "
                  "(run scripts/chunk3_create_scratchpad.sql to enable persistence)")

    print(f"\nDISTINCT specialists used across both questions: {sorted(all_specialists)}")
    print("PASS: routing sent sub-queries to multiple specialists"
          if len(all_specialists) >= 2 else "WARN: only one specialist used")


if __name__ == "__main__":
    main()
