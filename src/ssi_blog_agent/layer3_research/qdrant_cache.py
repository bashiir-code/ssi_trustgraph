"""Qdrant freshness cache (Chunk 3): skip a fresh external search if the same
sub-query was researched within the last 30 days.

Keying is deterministic (UUID5 of the normalised sub-query), so this is an
exact-match freshness cache rather than semantic similarity. Vectors are
placeholders (size 1); upgrading to real embeddings for semantic lookup is a
later enhancement that also feeds Chunk 6's semantic dedup. All operations
degrade gracefully — a Qdrant outage must never crash research.
"""

import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from ssi_blog_agent.config import settings

COLLECTION = "research_cache"
FRESHNESS_DAYS = settings.qdrant_freshness_days  # 30
_NAMESPACE = uuid.UUID("6f1c9b2e-0000-4000-8000-000000000003")

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    return _client


def _ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config=qm.VectorParams(size=1, distance=qm.Distance.COSINE),
        )


def _point_id(query: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, query.strip().lower()))


def get_fresh(query: str) -> dict | None:
    """Return cached {summary, sources, doc_id} if researched < 30 days ago."""
    try:
        client = _get_client()
        _ensure_collection(client)
        points = client.retrieve(COLLECTION, ids=[_point_id(query)], with_payload=True)
        if not points:
            return None
        payload = points[0].payload or {}
        ts = datetime.datetime.fromisoformat(payload["ts"])
        age = datetime.datetime.now(datetime.UTC) - ts
        if age.days < FRESHNESS_DAYS:
            return {
                "summary": payload["summary"],
                "sources": payload.get("sources", []),
                "doc_id": payload.get("doc_id"),
            }
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] qdrant get_fresh failed: {exc}")
        return None


def put(query: str, summary: str, sources: list[str], doc_id: str | None) -> None:
    try:
        client = _get_client()
        _ensure_collection(client)
        client.upsert(
            COLLECTION,
            points=[
                qm.PointStruct(
                    id=_point_id(query),
                    vector=[0.0],
                    payload={
                        "query": query,
                        "summary": summary,
                        "sources": sources,
                        "doc_id": doc_id,
                        "ts": datetime.datetime.now(datetime.UTC).isoformat(),
                    },
                )
            ],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] qdrant put failed: {exc}")
