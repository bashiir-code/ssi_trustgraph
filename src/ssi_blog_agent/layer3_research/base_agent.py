"""Shared base for the Oracle / Catalyst / Quant micro-agents (Chunk 3 +
depth + official-data upgrade).

Each agent's research flow:
  1. Qdrant freshness check (< 30 days) -> reuse cached summary if fresh.
  2. Optional PRIMARY DATA hook — an authoritative structured source (e.g.
     Tilastokeskus PxWeb official figures) fetched precisely for this query.
     Exact numbers at near-zero token cost; prioritised over web snippets.
  3. Source-biased + broad external search via the common research-tools layer.
  4. Pointer pattern: raw text -> Supabase scratchpad, keep only doc_id +
     sources + compressed summary in state.
  5. Compress to a grounded summary using the agent's own model + mandate.
  6. Upsert into the Qdrant freshness cache.

Subclasses set: name, model, system_prompt, include_domains; and may override
primary_data() to inject an authoritative structured source.
"""

from ssi_blog_agent.clients import deepseek
from ssi_blog_agent.layer3_research import qdrant_cache, research_tools
from ssi_blog_agent.models import FactSheet


class ResearchAgent:
    name: str = "base"
    model: str = "deepseek-v4-flash"
    system_prompt: str = "Olet tutkimusavustaja."
    include_domains: list[str] | None = None

    def primary_data(self, query: str) -> tuple[str, str] | None:
        """Optional authoritative structured source for this query.

        Returns (data_text, source_url) or None. Overridden by specialists
        (e.g. Quant -> Tilastokeskus official figures)."""
        return None

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

        # 2. Authoritative primary data (exact, cheap)
        try:
            primary = self.primary_data(query)
        except Exception as exc:  # noqa: BLE001 — official source must not crash research
            print(f"  [warn] primary data failed ({self.name}): {exc}")
            primary = None

        # 3. Source-biased + broad external search
        results = research_tools.search_sources(query, include_domains=self.include_domains)
        if not results and primary is None:
            return FactSheet(
                sub_query=query,
                summary="Hakutuloksia ei löytynyt tälle alikysymykselle.",
                sources=[],
                specialist=self.name,
            )

        # 4. Full text of the top authoritative source + pointer pattern
        full_texts = research_tools.fetch_full_text(results) if results else []
        if results:
            doc_id, sources = research_tools.persist_raw(query, results, agent=self.name)
        else:
            doc_id, sources = None, []
        if primary is not None:
            # Official source cited first.
            sources = [primary[1]] + [s for s in sources if s != primary[1]]

        # 5. Grounded compression (agent's own model + mandate)
        summary = self._summarize(query, results, full_texts, primary)

        # 6. Cache for freshness reuse
        qdrant_cache.put(query, summary, sources, doc_id=doc_id)

        return FactSheet(
            sub_query=query,
            summary=summary,
            sources=sources,
            specialist=self.name,
            doc_id=doc_id,
        )

    def _summarize(
        self,
        query: str,
        results: list[dict],
        full_texts: list[dict] | None = None,
        primary: tuple[str, str] | None = None,
    ) -> str:
        context = research_tools.format_results(results, full_texts)
        primary_block = ""
        if primary is not None:
            primary_block = (
                "=== VIRALLINEN TILASTODATA (ENSISIJAINEN LÄHDE — käytä näitä "
                "lukuja ja priorisoi ne verkkohakua vastaan) ===\n"
                f"{primary[0]}\nLähde: {primary[1]}\n\n"
            )
        return deepseek.chat(
            [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Alikysymys: {query}\n\n{research_tools.DATA_GUARD}\n\n"
                        "Poimi mahdollisimman monta konkreettista lukua (eurot, "
                        "prosentit, päivämäärät, lukumäärät) ja merkitse kunkin "
                        "väitteen lähde-URL. Jos virallista tilastodataa on "
                        "annettu, käytä sitä ensisijaisesti. Ole tiivis mutta "
                        "tietopitoinen.\n\n"
                        f"{primary_block}=== HAKUTULOKSET ===\n{context}"
                    ),
                },
            ],
            model=self.model,
        )
