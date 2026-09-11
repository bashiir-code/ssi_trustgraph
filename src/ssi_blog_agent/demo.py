"""Offline demo mode: runs the whole agent system with no API keys.

Every external service is replaced by a deterministic in-process fake —
Supabase (questions in, report out), Tavily + Firecrawl, Statistics Finland,
Upstash Redis (run-lock + 7-day cache) and the DeepSeek LLM. The fake LLM
answers per role (dedup, triage, specialists, critic, validator, analyst,
writer), so the real LangGraph wiring runs end to end: triage retry loop,
specialist routing, critic follow-up round, validator, pointer pattern,
numbered citations and cost accounting.

All figures and URLs are synthetic (``*.demo.invalid``) and the report is
labelled as a demo run. Enable with DEMO_MODE=1, or call install() directly.
"""

import json
import re
import threading

from ssi_blog_agent.clients import deepseek, search, supabase_client
from ssi_blog_agent.crosscutting import run_lock
from ssi_blog_agent.layer3_research import redis_cache, statfi_source, supervisor

QUESTIONS = [
    {"id": "q1", "text": "Miten rakennusinsinöörien palkat kehittyvät vuonna 2026?", "votes": 42},
    {"id": "q2", "text": "Miten EU:n rakennustuoteasetus muuttaa insinööritoimistojen työtä?", "votes": 31},
    {"id": "q3", "text": "Mitä tietomallinnusosaamista (BIM) työnantajat vaativat 2026?", "votes": 25},
    # Near-duplicate of q1 — the dedup layer should drop it.
    {"id": "q4", "text": "Paljonko rakennusinsinööri tienaa 2026?", "votes": 18},
]

STATFI_URL = "https://pxdata-stat-fi.demo.invalid/pra/15au.px"

# Triage plans per topic keyword (matched against the question text).
_PLANS = {
    "palkat": {"domain": "construction", "sub_queries": [
        {"query": "Rakennusalan erityisasiantuntijoiden mediaanipalkka (Tilastokeskus)", "specialist": "quant"},
        {"query": "Rakennusalan insinöörityövoiman kysyntä Suomessa 2026", "specialist": "oracle"},
    ]},
    "rakennustuoteasetus": {"domain": "construction", "sub_queries": [
        {"query": "EU:n uuden rakennustuoteasetuksen (CPR) siirtymäajat", "specialist": "oracle"},
        {"query": "Rakennustuotteiden digitaalinen tuotepassi ja tietovaatimukset", "specialist": "catalyst"},
    ]},
    "tietomallinnus": {"domain": "construction", "sub_queries": [
        {"query": "BIM-osaamisen vaatimukset insinöörien työpaikkailmoituksissa", "specialist": "catalyst"},
        {"query": "Tietomallinnusasiantuntijoiden palkkataso", "specialist": "quant"},
    ]},
}

# Critic verdicts per topic; topics not listed are judged sufficiently covered.
_CRITIQUES = {
    "palkat": {"coverage": 70, "gaps": ["Palkkojen vuosimuutos puuttuu"], "follow_up_queries": [
        {"query": "Insinöörien ansiotason muutos prosentteina", "specialist": "quant"},
    ]},
    "tietomallinnus": {"coverage": 75, "gaps": ["Julkisten tilaajien vaatimukset puuttuvat"], "follow_up_queries": [
        {"query": "Julkisten hankintojen tietomallivaatimukset", "specialist": "oracle"},
    ]},
}

STORE: dict = {"questions": [dict(q) for q in QUESTIONS], "reports": [], "scratchpad": {}}

_redis: dict[str, str] = {}
_redis_lock = threading.Lock()
_installed = False


def _topic(text: str) -> str | None:
    return next((key for key in _PLANS if key in text.lower()), None)


def _field(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


# --- Fake LLM: one scripted answer per agent role ---


def _dedup(user: str) -> dict:
    keep = [int(i) for i, text in re.findall(r"^(\d+): (.*)$", user, re.M) if not text.startswith("Paljonko")]
    return {"keep": keep}


def _triage(messages: list[dict]) -> dict:
    question = messages[1]["content"]
    retried = any("Edellinen yrityksesi" in m["content"] for m in messages)
    topic = _topic(question)
    if topic == "rakennustuoteasetus" and not retried:
        # Invalid domain + empty plan: Pydantic rejects it and the graph retries.
        return {"domain": "infrastructure", "sub_queries": []}
    if topic is None:
        return {"domain": "other", "sub_queries": [{"query": question, "specialist": "oracle"}]}
    return _PLANS[topic]


def _critic(user: str) -> dict:
    topic = _topic(_field(r"Jäsenkysymys: (.*)", user))
    return _CRITIQUES.get(topic, {"coverage": 90, "gaps": [], "follow_up_queries": []})


def _specialist(system: str, user: str) -> str:
    name = _field(r"Olet (The \w+)", system)
    query = _field(r"Alikysymys: (.*)", user)
    sources = len(re.findall(r"\]\(https://", user))
    summary = f"{name}: demokooste alikysymykseen \"{query}\" ({sources} hakutulosta)."
    if "VIRALLINEN TILASTODATA" in user:
        summary += " Tilastokeskuksen demodatan mukaan mediaani on 4 600–5 200 €/kk."
    return summary + " Luvut ovat synteettisiä."


def _writer(user: str) -> str:
    questions = re.findall(r"^## Kysymys \d+: (.*)$", user, re.M)
    refs = sorted({int(n) for n in re.findall(r"\[(\d+)\]", user)}) or [1]
    lines = [
        "# Viikon insinöörimarkkina-analyysi (demoajo)",
        "",
        "> **Demoajo:** kaikki luvut ja lähteet ovat synteettistä testidataa. Raportti "
        "näyttää agenttijärjestelmän rakenteen, ei todellista markkinatietoa.",
        "",
        "## Tiivistelmä & synteesi",
        "",
        f"Sääntely, tietomallinnusosaaminen ja palkat kytkeytyvät toisiinsa [{refs[0]}].",
    ]
    for i, question in enumerate(questions):
        lines += ["", f"## {question}", "", f"**Demohavainto** kysymykseen, katso lähde [{refs[i % len(refs)]}]."]
    return "\n".join(lines)


def _respond(messages: list[dict]) -> dict | str:
    system = messages[0]["content"] if messages[0]["role"] == "system" else ""
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    if "Tunnista lähes identtiset" in system:
        return _dedup(user)
    if "triage-avustaja" in system:
        return _triage(messages)
    if "tutkimuksen kriitikko" in system:
        return _critic(user)
    if "faktantarkistaja" in system:
        return "Demo-validointi: keskeiset väitteet on sidottu lähteisiin. KOKONAISLUOTTAMUS: keskitaso."
    if "vanhempi markkina-analyytikko" in system:
        return "Demo-muistio: sääntely (CPR) lisää tietomallinnusosaamisen kysyntää, mikä tukee palkkoja."
    if "asiantuntijatoimittaja" in system:
        return _writer(user)
    if system.startswith("Olet The "):
        return _specialist(system, user)
    return "demo"


def _fake_chat(messages, model=deepseek.DEFAULT_MODEL, response_format=None, temperature=0.3, timeout=None):
    reply = _respond(messages)
    text = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
    deepseek.usage_log.append({
        "model": model,
        "input_tokens": sum(len(m["content"]) for m in messages) // 4,
        "output_tokens": len(text) // 4,
    })
    return text


# --- Fake research sources ---


def _fake_search(query, max_results=5, include_domains=None, search_depth="basic"):
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40]
    return [
        {
            "title": f"Demolähde: {query[:60]}",
            "url": f"https://{domain.replace('.', '-')}.demo.invalid/{slug}",
            "content": f"Synteettinen hakutulos alikysymykseen \"{query}\".",
        }
        for domain in (include_domains or ["uutiset", "toimiala"])[:2]
    ]


def _fake_scrape(url, wait_for=0, timeout=25.0):
    return f"# {url}\n\nSynteettinen koko teksti demoajoa varten."


def _fake_salaries() -> tuple[str, str]:
    lines = ["Tilastokeskus-demodata (synteettinen), kokonaisansio €/kk:", "",
             "| Ammattiryhmä | Mediaani €/kk |", "|---|---|"]
    for i, label in enumerate(statfi_source.ENGINEERING_OCCUPATIONS.values()):
        lines.append(f"| {label} | {4600 + 120 * i} |")
    return "\n".join(lines), STATFI_URL


# --- Fake Supabase + Upstash Redis ---


def _top_questions(limit: int = 1) -> list[dict]:
    return [dict(q) for q in STORE["questions"][:limit]]


def _insert_questions(rows: list[dict]) -> list[dict]:
    STORE["questions"].extend(rows)
    return rows


def _insert_report(content_md: str) -> list[dict]:
    STORE["reports"].append(content_md)
    return [{"id": len(STORE["reports"])}]


def _insert_scratchpad(doc_id, sub_query, raw_content, sources, agent) -> None:
    STORE["scratchpad"][doc_id] = {"id": doc_id, "sub_query": sub_query, "raw_content": raw_content, "agent": agent}


def _get_scratchpad(doc_ids: list[str]) -> list[dict]:
    return [STORE["scratchpad"][d] for d in doc_ids if d in STORE["scratchpad"]]


def _fake_redis(command: list) -> dict:
    op, key, *rest = command
    with _redis_lock:
        if op == "GET":
            return {"result": _redis.get(key)}
        if op == "DEL":
            return {"result": int(_redis.pop(key, None) is not None)}
        if op == "SET":
            if "NX" in rest and key in _redis:
                return {"result": None}
            _redis[key] = rest[0]
            return {"result": "OK"}
    raise ValueError(f"unsupported redis command: {op}")


def install() -> None:
    """Swap every external client for its offline fake (idempotent)."""
    global _installed
    if _installed:
        return
    deepseek.chat = _fake_chat  # chat_json goes through chat, so JSON calls are covered too
    search.tavily_search = _fake_search
    search.firecrawl_scrape = _fake_scrape
    statfi_source.engineering_salaries = _fake_salaries
    supabase_client.top_questions = _top_questions
    supabase_client.insert_questions = _insert_questions
    supabase_client.insert_report = _insert_report
    supabase_client.insert_scratchpad = _insert_scratchpad
    supabase_client.get_scratchpad = _get_scratchpad
    run_lock._command = _fake_redis
    redis_cache._command = _fake_redis
    supervisor.STAGGER_SECONDS = 0  # no free-tier rate limits to smooth offline
    _installed = True


def reset() -> None:
    """Clear fake state between runs (used by the tests)."""
    with _redis_lock:
        _redis.clear()
    STORE["reports"].clear()
    STORE["scratchpad"].clear()
    deepseek.usage_log.clear()
