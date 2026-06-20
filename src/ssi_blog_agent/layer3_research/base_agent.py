"""Shared base for the Oracle / Catalyst / Quant micro-agents (Chunk 3).

Each agent's research flow:
  1. Qdrant freshness check (< 30 days) -> reuse cached summary if fresh.
  2. Source-biased external search via the common research-tools interface.
  3. Pointer pattern: raw text -> Supabase scratchpad, keep only doc_id +
     sources + compressed summary in state.
  4. Compress to a grounded summary using the agent's own model + mandate
     prompt.
  5. Upsert the result into the Qdrant freshness cache.

Subclasses set: name, model, system_prompt, include_domains.
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.layer3_research import qdrant_cache, research_tools
from ssi_blog_agent.models import FactSheet


class ResearchAgent:
    name: str = "base"
    model: str = "deepseek-v4-flash"
    system_prompt: str = "Olet tutkimusavustaja."
    include_domains: list[str] | None = None

    def research(self, query: str) -> FactSheet:
        # 1. Freshness cache
        cached = qdrant_cache.get_fresh(query)
        if cached is not None:
            return FactSheet(
                sub_query=query,
                summary=cached["summary"],
                sources=cached.get("sources", []),
                specialist=self.name,
                doc_id=cached.get("doc_id"),
                cache_hit=True,
            )

        # 2. Source-biased external search
        results = research_tools.search_sources(
            query, include_domains=self.include_domains
        )
        if not results:
            return FactSheet(
                sub_query=query,
                summary="Hakutuloksia ei löytynyt tälle alikysymykselle.",
                sources=[],
                specialist=self.name,
            )

        # 3. Pointer pattern
        doc_id, sources = research_tools.persist_raw(query, results, agent=self.name)

        # 4. Grounded compression (agent's own model + mandate)
        summary = self._summarize(query, results)

        # 5. Cache for freshness reuse
        qdrant_cache.put(query, summary, sources, doc_id=doc_id)

        return FactSheet(
            sub_query=query,
            summary=summary,
            sources=sources,
            specialist=self.name,
            doc_id=doc_id,
        )

    def _summarize(self, query: str, results: list[dict]) -> str:
        context = research_tools.format_results(results)
        return deepseek.chat(
            [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Alikysymys: {query}\n\n{research_tools.DATA_GUARD}\n\n"
                        f"=== HAKUTULOKSET ===\n{context}"
                    ),
                },
            ],
            model=self.model,
        )
