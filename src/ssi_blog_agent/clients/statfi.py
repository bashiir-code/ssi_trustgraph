"""Statistics Finland (Tilastokeskus) PxWeb API client.

Official, structured statistics — exact figures at near-zero token cost, the
core of the niche accuracy advantage. No API key needed; CC BY 4.0 (attribute
"Tilastokeskus"). See docs/source_compatibility.md (Chunk 0.5).
"""

import itertools

import httpx

PXWEB_BASE = "https://pxdata.stat.fi/PXWeb/api/v1/fi/StatFin"


def query_table(path: str, query: list[dict], timeout: float = 30.0) -> list[dict]:
    """POST a PxWeb query to a table (e.g. "pra/15au.px"); return flat rows.

    Each row: {"dims": {dim_code: (value_code, value_label)}, "value": <num>}.
    """
    resp = httpx.post(
        f"{PXWEB_BASE}/{path}",
        json={"query": query, "response": {"format": "json-stat2"}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return _parse_jsonstat2(resp.json())


def _parse_jsonstat2(d: dict) -> list[dict]:
    dims = d["id"]
    sizes = d["size"]
    values = d["value"]

    # position -> (code, label) per dimension
    pos_maps: dict[str, dict[int, tuple[str, str]]] = {}
    for dim in dims:
        category = d["dimension"][dim]["category"]
        index = category["index"]
        labels = category.get("label", {})
        pos_map: dict[int, tuple[str, str]] = {}
        if isinstance(index, dict):
            for code, pos in index.items():
                pos_map[pos] = (code, labels.get(code, code))
        else:  # list of codes in order
            for pos, code in enumerate(index):
                pos_map[pos] = (code, labels.get(code, code))
        pos_maps[dim] = pos_map

    rows = []
    for n, combo in enumerate(itertools.product(*[range(s) for s in sizes])):
        value = values[n] if isinstance(values, list) else values.get(str(n))
        dim_values = {dims[i]: pos_maps[dims[i]][combo[i]] for i in range(len(dims))}
        rows.append({"dims": dim_values, "value": value})
    return rows
