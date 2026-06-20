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


class ResearchChunk(BaseModel):
    """One alikyselyiksi puretun jäsenkysymyksen tutkimustehtävä."""

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
