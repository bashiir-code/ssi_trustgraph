"""The Quant (V4-Flash) — Resurssit & arvo: hinnat, palkat, kustannukset,
kilpailija-hinnoittelu. Pelkkää numeerista vertailua -> Flash riittää, ei
vaadi V4-Pron raskasta päättelyä (merkittävä token-säästö)."""

from ssi_blog_agent.layer3_research.base_agent import ResearchAgent

QUANT_PROMPT = """Olet The Quant, numeerinen analyytikko Suomen insinöörialalle.
Erikoisalasi: palkat, hinnat, kustannukset ja numeeriset vertailut. Kirjoita
tiivis, faktapohjainen suomenkielinen kooste annettuun alikysymykseen KÄYTTÄEN
VAIN annettuja hakutuloksia. POIMI konkreettiset luvut (eurot, prosentit,
vaihteluvälit) ja niiden lähteet. ÄLÄ koskaan keksi tai pyöristä lukuja, joita
hakutuloksissa ei ole. Jos lukuja ei löydy, sano se rehellisesti. Viittaa
keskeisiin lähde-URLeihin."""


class QuantAgent(ResearchAgent):
    name = "quant"
    model = "deepseek-v4-flash"
    system_prompt = QUANT_PROMPT
    include_domains = [
        "tilastokeskus.fi",
        "stat.fi",
        "teknologiateollisuus.fi",
        "tek.fi",
    ]
