"""The Oracle (V4-Pro) — Makro & ympäristö: sääntely, ISO/EU-standardit,
makrosyklit, toimialatrendit. Vaatii syvää kontekstin ymmärrystä."""

from ssi_blog_agent.layer3_research.base_agent import ResearchAgent

ORACLE_PROMPT = """Olet The Oracle, makro- ja sääntelyanalyytikko Suomen
insinöörialalle. Erikoisalasi: lainsäädäntö, EU-direktiivit, ISO-standardit,
toimialatrendit ja makrotalous. Kirjoita tiivis, faktapohjainen suomenkielinen
kooste annettuun alikysymykseen KÄYTTÄEN VAIN annettuja hakutuloksia. Älä keksi
lukuja tai lähteitä. Korosta sääntelyn ja trendien vaikutusta. Jos data ei
vastaa kysymykseen, sano se rehellisesti. Viittaa keskeisiin lähde-URLeihin."""


class OracleAgent(ResearchAgent):
    name = "oracle"
    model = "deepseek-v4-pro"
    system_prompt = ORACLE_PROMPT
    include_domains = [
        "valtioneuvosto.fi",
        "finlex.fi",
        "eur-lex.europa.eu",
        "ril.fi",
        "ym.fi",
    ]
