"""Curated Statistics Finland data for the Finnish engineering niche.

A hand-picked map of the RIGHT official tables + occupation codes — this is
the niche moat: we query exact figures Google merely paraphrases from
aggregator sites. Results are lru-cached (annual data) so a whole run makes at
most one PxWeb call per dataset → high accuracy, negligible tokens.
"""

from functools import lru_cache

from ssi_blog_agent.clients import statfi

# Wage structure, monthly earnings by occupation (Ammattiluokitus 2010).
_SALARY_TABLE = "pra/15au.px"
_SALARY_YEAR = "2024"
_SALARY_URL = "https://pxdata.stat.fi/PXWeb/api/v1/fi/StatFin/pra/15au.px"

# Curated engineering occupations for this niche (code -> Finnish label).
ENGINEERING_OCCUPATIONS = {
    "214": "Tekniikan erityisasiantuntijat (yhteensä)",
    "2142": "Maa- ja vesirakentamisen erityisasiantuntijat",
    "2144": "Konetekniikan erityisasiantuntijat",
    "2151": "Sähkötekniikan erityisasiantuntijat",
    "2141": "Teollisen valmistuksen ja tuotantotekniikan",
    "3112": "Rakentamisen asiantuntijat (AMK-taso)",
}


@lru_cache(maxsize=1)
def engineering_salaries() -> tuple[str, str]:
    """Official monthly earnings for curated engineering occupations.

    Returns (markdown_table, source_url). Cached for the process.
    """
    query = [
        {"code": "timeperiod_y", "selection": {"filter": "item", "values": [_SALARY_YEAR]}},
        {"code": "sektoriluokitus_7_20230101", "selection": {"filter": "item", "values": ["S0"]}},
        {"code": "ammatti_19_20180101", "selection": {"filter": "item", "values": list(ENGINEERING_OCCUPATIONS)}},
        {"code": "sukupuoli_9_20180101", "selection": {"filter": "item", "values": ["SSS"]}},
        {"code": "contentscode", "selection": {"filter": "item", "values": ["koko_psaaja_lkm", "koko_psaaja_kans_ka", "koko_psaaja_kans_med"]}},
    ]
    rows = statfi.query_table(_SALARY_TABLE, query)

    by_occ: dict[str, dict[str, float]] = {}
    for row in rows:
        occ_code = row["dims"]["ammatti_19_20180101"][0]
        metric = row["dims"]["contentscode"][0]
        by_occ.setdefault(occ_code, {})[metric] = row["value"]

    lines = [
        f"Tilastokeskus, palkkarakenne {_SALARY_YEAR} — kokoaikaisten palkansaajien "
        "kokonaisansio (€/kk, molemmat sukupuolet, kaikki sektorit):",
        "",
        "| Ammattiryhmä | Lukumäärä | Keskiarvo €/kk | Mediaani €/kk |",
        "|---|---|---|---|",
    ]
    for code, label in ENGINEERING_OCCUPATIONS.items():
        m = by_occ.get(code, {})
        lines.append(
            f"| {label} | {m.get('koko_psaaja_lkm', '-')} | "
            f"{m.get('koko_psaaja_kans_ka', '-')} | {m.get('koko_psaaja_kans_med', '-')} |"
        )
    return "\n".join(lines), _SALARY_URL
