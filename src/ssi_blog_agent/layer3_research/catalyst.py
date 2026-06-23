"""The Catalyst — Kyvykkyys & toteutus: teknologiapinot, työnkulut, työkalut,
kompetenssit. Summarointi on pohjustettua poimintaa -> V4-Flash riittää;
raskas päättely tapahtuu critic- ja analyst-kerroksissa (V4-Pro)."""

from ssi_blog_agent.layer3_research.base_agent import ResearchAgent

CATALYST_PROMPT = """Olet The Catalyst, teknologia- ja kyvykkyysanalyytikko
Suomen insinöörialalle. Erikoisalasi: teknologiapinot, ohjelmistot ja työkalut,
työnkulut, automaatio sekä osaamis- ja kompetenssitarpeet. Kirjoita tiivis,
faktapohjainen suomenkielinen kooste annettuun alikysymykseen KÄYTTÄEN VAIN
annettuja hakutuloksia. Älä keksi lukuja tai lähteitä. Korosta käytännön
toteutusta ja osaamista. Jos data ei vastaa kysymykseen, sano se rehellisesti.
Viittaa keskeisiin lähde-URLeihin."""


class CatalystAgent(ResearchAgent):
    name = "catalyst"
    model = "deepseek-v4-flash"
    system_prompt = CATALYST_PROMPT
    include_domains = ["teknologiateollisuus.fi", "tek.fi"]
