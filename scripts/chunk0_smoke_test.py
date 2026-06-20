"""Chunk 0 — prove the wiring works.

No LangGraph, no agents. One hardcoded question -> one DeepSeek call ->
write the result to a local markdown artifact, and (if Supabase is
reachable) into the `reports` table.

Run: python scripts/chunk0_smoke_test.py
"""

import datetime
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

HARDCODED_QUESTION = (
    "Mitkä ovat suurimmat muutokset Suomen rakennusalan ISO-standardeissa "
    "viimeisen vuoden aikana, ja miten ne vaikuttavat pieniin insinööritoimistoihin?"
)

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")


def call_deepseek(question: str) -> str:
    response = httpx.post(
        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": question}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def write_local_artifact(question: str, answer: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(OUTPUT_DIR, f"chunk0_{timestamp}.md")
    content = f"# Chunk 0 smoke test\n\n**Kysymys:** {question}\n\n---\n\n{answer}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def write_to_supabase(question: str, answer: str) -> tuple[bool, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return False, "SUPABASE_URL / SUPABASE_SERVICE_KEY not set"

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/rest/v1/reports",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={"content_md": answer},
            timeout=30,
        )
        if response.status_code >= 300:
            return False, f"HTTP {response.status_code}: {response.text}"
        return True, "ok"
    except httpx.HTTPError as exc:
        return False, str(exc)


def main() -> None:
    print("Calling DeepSeek...")
    answer = call_deepseek(HARDCODED_QUESTION)

    artifact_path = write_local_artifact(HARDCODED_QUESTION, answer)
    print(f"Local artifact written: {artifact_path}")

    supabase_ok, supabase_detail = write_to_supabase(HARDCODED_QUESTION, answer)
    if supabase_ok:
        print("Supabase write: OK")
    else:
        print(f"Supabase write: SKIPPED/FAILED -> {supabase_detail}", file=sys.stderr)

    print("\n--- DeepSeek response ---\n")
    print(answer)


if __name__ == "__main__":
    main()
