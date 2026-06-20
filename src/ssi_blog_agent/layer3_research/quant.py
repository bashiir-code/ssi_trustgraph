"""The Quant — Resurssit & arvo: hinnat, palkat, kustannukset. Pelkkää numeerista
vertailua -> V4-Flash riittää, ei vaadi V4-Pron raskasta päättelyä."""

from ssi_blog_agent.layer3_research.base_agent import ResearchAgent


class QuantAgent(ResearchAgent):
    name = "quant"
    model = "deepseek-v4-flash"
