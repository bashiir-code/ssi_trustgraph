"""Seed representative Finnish engineering member questions into Supabase.

Idempotent per-question: inserts only questions whose exact text isn't
already present, so re-running it tops up missing ones.
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
    {
        "text": (
            "Mitkä ovat suurimmat kasvavat osaamisalueet ja rekrytointitarpeet "
            "Suomen energia- ja sähköverkkoinsinööreille 2026?"
        ),
        "votes": 25,
    },
    {
        "text": (
            "Miten teollisuuden automaatio- ja kunnossapitoinsinöörien kysyntä ja "
            "palkkataso kehittyvät Suomessa 2025-2026?"
        ),
        "votes": 21,
    },
]


def main() -> None:
    existing = supabase_client.top_questions(limit=1000)
    existing_texts = {row["text"] for row in existing}

    missing = [q for q in QUESTIONS if q["text"] not in existing_texts]
    if not missing:
        print(f"Kaikki {len(QUESTIONS)} kysymystä jo olemassa — ei muutoksia.")
        return

    rows = supabase_client.insert_questions(missing)
    print(f"Seedattu {len(rows)} uutta kysymystä (yhteensä nyt "
          f"{len(existing) + len(rows)}):")
    for row in rows:
        print(f"  [{row['votes']}] {row['text'][:65]}...")


if __name__ == "__main__":
    main()
