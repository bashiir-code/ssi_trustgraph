# SSI Blog Agent

Viikoittainen, 4-kerroksinen agenttiputki, joka poimii jäsenkysymyksiä, tutkii
Suomen insinöörimarkkinaa ja julkaisee Markdown-raportin insinoorit.fi:lle.
Katso arkkitehtuurin täysi kuvaus suunnitelmadokumentista (Layer 1-4 +
cross-cutting).

## Tila

Tämä on **runnable skeleton**: LangGraph-tilakone, Pydantic-mallit ja kaikkien
kerrosten solmut ovat paikoillaan ja ajettavissa päästä päähän, mutta
ulkoiset integraatiot (Supabase, Qdrant, Upstash, Firecrawl/Tavily, DeepSeek)
ovat `TODO`-merkittyjä stubbeja. Aja `python -m ssi_blog_agent.main`
nähdäksesi tilakoneen kulkevan läpi kaikki kerrokset stub-datalla.

## Setup-checklist (ennen tuotantokäyttöä)

1. **Python**: `python3 -m venv .venv && source .venv/bin/activate && pip install -e . -r requirements.txt`
2. **Supabase**: luo projekti, taulu jäsenkysymyksille + `run_lock`-taulu/rivi
   idempotenssia varten. Täytä `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`.
3. **DeepSeek**: hae API-avain, täytä `DEEPSEEK_API_KEY`. Toteuta
   [layer2_triage.py](src/ssi_blog_agent/layer2_triage.py) ja
   [layer4_presentation.py](src/ssi_blog_agent/layer4_presentation.py)
   oikealla structured-output-kutsulla.
4. **Qdrant Cloud (free tier)**: luo cluster, täytä `QDRANT_URL` /
   `QDRANT_API_KEY`. Toteuta `query_vector_db` agenttien pohjaluokassa
   ([base_agent.py](src/ssi_blog_agent/layer3_research/base_agent.py)).
5. **Upstash Redis**: luo REST-tietokanta, täytä `UPSTASH_REDIS_REST_URL` /
   `UPSTASH_REDIS_REST_TOKEN`. Toteuta
   [cache.py](src/ssi_blog_agent/layer3_research/cache.py) (semanttinen
   7 päivän välimuisti) ja run-lukko
   ([layer1_data_entry.py](src/ssi_blog_agent/layer1_data_entry.py)).
6. **Firecrawl / Tavily**: hae API-avaimet, täytä `FIRECRAWL_API_KEY` /
   `TAVILY_API_KEY`. Toteuta `scrape_external` — muista
   `UNTRUSTED_DATA_GUARD`-rajain jokaisessa promptissa, joka käsittelee
   skreipattua sisältöä.
7. **Slack-hälytys**: luo incoming webhook, täytä `SLACK_WEBHOOK_URL`.
8. **GitHub Secrets**: lisää kaikki yllä olevat avaimet repon
   Settings → Secrets and variables → Actions, samoilla nimillä kuin
   `.env.example`:ssä.
9. **Semanttinen dedup**: toteuta embedding-cosine-vertailu
   `dedup_questions`-funktiossa ([layer1_data_entry.py](src/ssi_blog_agent/layer1_data_entry.py)).
10. **Budjettikatkaisija**: kytke
    [budget.py](src/ssi_blog_agent/crosscutting/budget.py) `BudgetTracker`
    todelliseen API-vastausten `usage`-kenttään ja katkaise ajo, jos
    `exceeded()` palauttaa `True`.

## Ajaminen paikallisesti

```bash
cp .env.example .env  # täytä avaimet
python -m ssi_blog_agent.main
```

## Ajaminen GitHub Actionsissa

`.github/workflows/weekly_report.yml` ajaa koko putken kerran viikossa
(maanantaisin) tai manuaalisesti (`workflow_dispatch`). Nykyinen versio ajaa
kaikki kerrokset yhdessä jobissa — kun research-kerros (Layer 3) on
toteutettu oikeilla integraatioilla ja ajoaika kasvaa, pilko se erillisiin
matrix-jobeihin per research chunk (ks. suunnitelman kohta 4e) niin että
yksittäinen hidas kysymys ei vie koko 6h-budjettia muilta.

## Rakenne

```
src/ssi_blog_agent/
  config.py                 Ympäristömuuttujat
  models.py                 Pydantic-mallit (Domain, ResearchChunk, AgentResult, ...)
  state.py                  LangGraph GraphState
  layer1_data_entry.py      Run-lukko, kysymysten haku, dedup
  layer2_triage.py          DeepSeek-triage + retry loop + fallback
  layer3_research/
    base_agent.py           Yhteinen agenttipohja + injection guard
    oracle.py, catalyst.py, quant.py
    cache.py                Upstash-välimuisti
    supervisor.py           Rinnakkaisuuden hallinta
  layer4_presentation.py    State pruning + raportin kirjoitus
  crosscutting/
    observability.py        Slack-hälytys
    budget.py                Kustannuslaskuri
  graph.py                  LangGraph-kokoonpano
  main.py                   Entrypoint
```
