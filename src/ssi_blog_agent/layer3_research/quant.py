"""The Quant (V4-Flash) — Resurssit & arvo: hinnat, palkat, kustannukset,
kilpailija-hinnoittelu. Pelkkää numeerista vertailua -> Flash riittää.

Niche edge: for salary/earnings sub-queries the Quant pulls OFFICIAL
Tilastokeskus figures (PxWeb) as the primary source — exact numbers at
near-zero token cost — instead of relying on web salary aggregators.
"""

from ssi_blog_agent.layer3_research import statfi_source
from ssi_blog_agent.layer3_research.base_agent import ResearchAgent

QUANT_PROMPT = """Olet The Quant, numeerinen analyytikko Suomen insinöörialalle.
Erikoisalasi: palkat, hinnat, kustannukset ja numeeriset vertailut. Kirjoita
tiivis, faktapohjainen suomenkielinen kooste annettuun alikysymykseen KÄYTTÄEN
VAIN annettuja tietoja. Jos virallista Tilastokeskuksen dataa on annettu, käytä
sitä ENSISIJAISESTI ja viittaa siihen. POIMI konkreettiset luvut (eurot,
prosentit, vaihteluvälit) ja niiden lähteet. ÄLÄ koskaan keksi tai pyöristä
lukuja, joita tiedoissa ei ole. Jos lukuja ei löydy, sano se rehellisesti."""

# Sub-query keywords that warrant official salary data.
_SALARY_KEYWORDS = (
    "palk", "ansio", "euro", "€", "kustannus", "tulot", "mediaani", "keskiansi"
)


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

    def primary_data(self, query: str) -> tuple[str, str] | None:
        if any(k in query.lower() for k in _SALARY_KEYWORDS):
            return statfi_source.engineering_salaries()
        return None
