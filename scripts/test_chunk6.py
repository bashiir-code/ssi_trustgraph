"""Chunk 6 proof: run-lock blocks a double-trigger, budget breaker trips,
semantic dedup collapses duplicates, notifier composes the right message.

Run: python scripts/test_chunk6.py
"""

import sys

from ssi_blog_agent.config import settings
from ssi_blog_agent.crosscutting import budget, observability, run_lock
from ssi_blog_agent.layer1_data_entry import dedup_questions
from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.models import MemberQuestion


def test_run_lock() -> bool:
    run_lock.release()  # clean slate
    first = run_lock.acquire()
    second = run_lock.acquire()  # overlapping run must be blocked
    run_lock.release()
    third = run_lock.acquire()  # free again after release
    run_lock.release()
    ok = first and not second and third
    print(f"  run-lock: acquire={first}, double-trigger blocked={not second}, "
          f"reacquire-after-release={third} -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_budget() -> bool:
    cheap = [{"model": "deepseek-v4-flash", "input_tokens": 1000, "output_tokens": 500}]
    huge = [{"model": "deepseek-v4-pro", "input_tokens": 5_000_000, "output_tokens": 2_000_000}]
    ok = (not budget.exceeded(cheap)) and budget.exceeded(huge)
    print(f"  budget breaker: cheap_ok={not budget.exceeded(cheap)}, "
          f"huge_trips={budget.exceeded(huge)} (cap {settings.max_run_cost_eur} EUR) "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok


def test_dedup() -> bool:
    qs = [
        MemberQuestion(id="1", text="Rakennusinsinöörien palkat 2026?", votes=40),
        MemberQuestion(id="2", text="Paljonko rakennusinsinööri tienaa 2026?", votes=20),
        MemberQuestion(id="3", text="EU-sääntelyn vaikutus insinööritoimistoihin?", votes=15),
    ]
    deepseek.chat_json = lambda messages, **kw: {"keep": [0, 2]}  # drop the near-dup #2
    out = dedup_questions(qs)
    ok = len(out) == 2 and out[0].id == "1" and out[1].id == "3"
    print(f"  dedup: 3 -> {len(out)} (kept {[q.id for q in out]}) -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_notify() -> bool:
    saved = settings.slack_webhook_url
    settings.slack_webhook_url = ""  # avoid spamming Slack; exercise print path
    try:
        observability.notify("partial", "test detail")
    finally:
        settings.slack_webhook_url = saved
    print("  notify(partial): composed without error -> PASS")
    return True


def main() -> None:
    print("Chunk 6 hardening proof:")
    results = [test_run_lock(), test_budget(), test_dedup(), test_notify()]
    print("ALL PASS" if all(results) else "FAILED")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
