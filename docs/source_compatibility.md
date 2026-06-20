# Chunk 0.5 — Source Compatibility Table

Validated against real Firecrawl/Tavily calls and the live Tilastokeskus API
on 2026-06-20. Scripts: [scripts/chunk0_5_source_probe.py](../scripts/chunk0_5_source_probe.py),
[scripts/chunk0_5_followup.py](../scripts/chunk0_5_followup.py). Raw results:
[artifacts/chunk0_5_probe_results.json](../artifacts/chunk0_5_probe_results.json).

| Source | URL | Access method | Status | Decision |
|---|---|---|---|---|
| Tilastokeskus | `pxdata.stat.fi/PXWeb/api/v1/fi/StatFin/pra` | Real structured API (PxWeb) | ✅ Works | Call the API directly, never scrape. Salary/earnings tables confirmed under `StatFin/pra` (e.g. table `15au.px`). |
| Teknologiateollisuus — palkat | teknologiateollisuus.fi/.../tilastot/palkat/ | Firecrawl scrape | ✅ Works | Clean markdown (5.4K chars), use as-is. |
| Teknologiateollisuus — talousnäkymät | teknologiateollisuus.fi/.../talousnakymat/ | Firecrawl scrape | ✅ Works | Clean markdown (15.8K chars), use as-is. |
| SKOL reports | teknologiateollisuus.fi/skol/ | Firecrawl scrape index page, then follow discovered PDF link | ✅ Works, with caveat | The guessed URL pattern (`suhdannekatsaus-{N}-{YYYY}`) is wrong. Real path is `.../skol/wp-content/uploads/sites/6/{upload-YYYY}/{upload-MM}/<ReportName>_<N>_<YYYY>...pdf` — not predictable from N/YYYY alone. **Always discover the latest report URL from the index page each run, never construct it.** |
| RIL (ROTI report) | ril.fi (site) + PDF found via Tavily search | Firecrawl scrape (site) + Tavily search (locate latest PDF) + Firecrawl (extract PDF text) | ✅ Works well | Tavily search for "RIL ROTI raportti" reliably finds the current year's PDF. Firecrawl extracted 69K chars of clean, structured text from the PDF (headings, body all intact). |
| Insinööriliitto IL | ilry.fi/tyoelaman-tilanteet/palkka-asiat/ | Firecrawl scrape | ✅ Works, URL stale | Original URL 301-redirects to `/edut-ja-palvelut/palkkapalvelut/` — site was restructured. Update the bookmarked URL; Firecrawl follows the redirect fine either way. |
| Työmarkkinatori | tyomarkkinatori.fi/henkiloasiakkaat/avoimet-tyopaikat | Firecrawl scrape **with `waitFor: 8000`** | ✅ Works (was broken) | Default scrape (no wait) returns only `"Ladataan"` (8 chars) — the A-TMT SPA hasn't rendered yet. With `waitFor: 8000` ms, returns real current job listings (verified: real company names, today's date `20.6.2026`, engineering-relevant titles like "LVI-asentaja", "Työnjohtaja"). No custom Playwright script needed — just always set `waitFor >= 8000` for this domain. |
| TEM Toimialaraportit | julkaisut.valtioneuvosto.fi | Tavily search (per topic) -> Firecrawl (extract PDF) | ✅ Works | No single fixed URL; search per research topic (e.g. "TEM toimialaraportti rakennusala") and extract whichever PDF comes back. |
| Tekniikka&Talous | tekniikkatalous.fi | — | 🚫 Excluded | Alma Media title. Homepage teasers scrape fine, but per user decision (2026-06-20), Alma Media paywalled titles are excluded entirely regardless of technical feasibility — see Talouselämä note below. |
| Talouselämä | talouselama.fi | — | 🚫 Excluded | **Tested and confirmed Firecrawl returns full subscriber-only article text** (30.6K chars, complete body) even from a page marked "Tilaajille". Technically possible, but likely violates Alma Media's ToS. User decided (2026-06-20) to exclude Alma Media paywalled titles entirely rather than rely on teaser-only or claim a licensing exception. |
| Rakennuslehti | rakennuslehti.fi | — | 🚫 Excluded | Same policy as above — RIL-member-gated through Alma's login system. Not individually re-tested at article level since the exclusion decision already covers it. |

## Rate limits

Deliberate stress test: 10 rapid sequential Firecrawl calls with no delay
between them, all returned `HTTP 200` — no `429` triggered. The free-tier
throughput tolerance is higher than the architecture plan's conservative
2-5s stagger assumption. The stagger/sleep is still worth keeping as a
safety margin for sustained weekly-batch volume, but isn't strictly required
at this scale.

## Net effect on Layer 3 design

- Drop the three Alma Media sources from any agent's source list entirely.
- Qdrant/Firecrawl tool calls for SKOL, RIL, and TEM must do a **discovery
  step first** (scrape index page / Tavily search) before fetching the
  actual report — none of these have a stable, predictable direct URL.
- Työmarkkinatori calls must always pass `waitFor: 8000` (or higher) in the
  Firecrawl request options.
- Tilastokeskus should bypass Firecrawl/Tavily entirely and hit the PxWeb
  API directly — it's free, structured, faster, and CC BY 4.0 licensed.
