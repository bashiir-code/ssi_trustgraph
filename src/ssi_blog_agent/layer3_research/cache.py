"""Upstash Redis -semanttinen välimuisti ulkoisille hauille (7 pv tuoreus)."""

from ssi_blog_agent.config import settings


def get_cached_research(chunk_research_prompt: str) -> str | None:
    """TODO: hae semanttisesti samankaltainen aiempi haku Upstash Redisistä.

    Palauttaa kompressoidun faktakoosteen jos cache hit viimeisen
    settings.cache_freshness_days päivän ajalta, muuten None.
    """
    return None


def set_cached_research(chunk_research_prompt: str, compressed_facts: str) -> None:
    """TODO: tallenna kompressoitu tulos Upstash Redisiin TTL:llä (7 pv)."""
    return None
