from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Domain(str, Enum):
    CONSTRUCTION = "construction"
    INDUSTRIAL = "industrial"
    ENERGY = "energy"
    OTHER = "other"


class Specialist(str, Enum):
    """Which micro-agent handles a sub-query (Chunk 3 swarm)."""

    ORACLE = "oracle"  # macro / regulatory / standards / trends
    CATALYST = "catalyst"  # capability / tooling / workflows / competence
    QUANT = "quant"  # numeric / pricing / salaries / costs


class AgentStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"


class MemberQuestion(BaseModel):
    id: str
    text: str
    votes: int = 0


# --- Triage / research-plan models ---


class SubQuery(BaseModel):
    query: str
    specialist: Specialist


class ResearchPlan(BaseModel):
    """Triage output, also the Pydantic schema validated against raw triage
    JSON: an invalid domain/specialist or empty sub_queries raises
    ValidationError, which drives the conditional-edge retry loop in Layer 2.
    """

    domain: Domain
    sub_queries: list[SubQuery] = Field(min_length=1)


class FactSheet(BaseModel):
    """One grounded research summary for a single sub-query.

    Pointer pattern: raw content lives in the Supabase scratchpad under
    doc_id; only the compressed summary + sources + pointer reach state.
    """

    sub_query: str
    summary: str
    sources: list[str] = Field(default_factory=list)
    specialist: Optional[str] = None
    doc_id: Optional[str] = None
    cache_hit: bool = False


# --- Retained for later chunks ---


class SourcedFact(BaseModel):
    fact: str
    source_url: str
    document_id: str
