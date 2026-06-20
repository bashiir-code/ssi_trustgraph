from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Domain(str, Enum):
    CONSTRUCTION = "construction"
    INDUSTRIAL = "industrial"
    ENERGY = "energy"
    OTHER = "other"


class AgentStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"


class MemberQuestion(BaseModel):
    id: str
    text: str
    votes: int = 0


# --- Chunk 1 vertical-slice models ---


class ResearchPlan(BaseModel):
    """Triage output: domain + focused sub-queries for the research agent.

    Doubles as the Pydantic schema validated against raw triage JSON:
    an invalid domain or empty sub_queries raises ValidationError, which
    drives the conditional-edge retry loop in Layer 2.
    """

    domain: Domain
    sub_queries: list[str] = Field(min_length=1)


class FactSheet(BaseModel):
    """One grounded research summary for a single sub-query, with sources."""

    sub_query: str
    summary: str
    sources: list[str] = Field(default_factory=list)


# --- Full-design models (Chunk 3 swarm, retained for later) ---


class ResearchChunk(BaseModel):
    chunk_id: str
    question_id: str
    domain: Domain
    research_prompt: str = Field(description="Selkeä, yksittäinen tutkimuskysymys")


class TriagePlan(BaseModel):
    chunks: list[ResearchChunk]


class SourcedFact(BaseModel):
    fact: str
    source_url: str
    document_id: str


class AgentResult(BaseModel):
    agent_name: str
    chunk_id: str
    status: AgentStatus
    facts: list[SourcedFact] = Field(default_factory=list)
    error: Optional[str] = None
