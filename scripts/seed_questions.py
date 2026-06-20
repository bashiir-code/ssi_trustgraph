"""Seed representative Finnish engineering member questions into Supabase.

Idempotent: does nothing if the questions table already has rows.
Run: python scripts/seed_questions.py
"""

from ssi_blog_agent.clients import supabase_client

QUESTIONS = [
    {
        "text": (
            "Mikä on rakennus- ja rakennetekniikan insinöörien palkkakehitys "
            "Suomessa 2025-2026, ja miten pääkaupunkiseutu vertautuu muuhun maahan?"
        ),
        "votes": 42,
    },
    {
        "text": (
            "Miten tekoäly ja BIM-automaatio muuttavat suunnittelu- ja "
            "insinööritoimistojen työnkulkuja ja osaamistarpeita seuraavan "
            "kahden vuoden aikana?"
        ),
        "votes": 37,
    },
    {
        "text": (
            "Mitkä EU- ja kansalliset sääntelymuutokset (esim. rakennustuoteasetus, "
            "energiatehokkuusdirektiivi) vaikuttavat eniten pieniin "
            "insinööritoimistoihin 2026?"
        ),
        "votes": 29,
    },
]


def main() -> None:
    existing = supabase_client.top_questions(limit=100)
    if existing:
        print(f"{len(existing)} kysymystä jo olemassa — ei seedata uudelleen.")
        return

    rows = supabase_client.insert_questions(QUESTIONS)
    print(f"Seedattu {len(rows)} kysymystä:")
    for row in rows:
        print(f"  [{row['votes']}] {row['text'][:70]}...")


if __name__ == "__main__":
    main()
