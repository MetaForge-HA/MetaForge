"""Input/output schemas for the retrieve_knowledge skill."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from digital_twin.knowledge.store import KnowledgeType


class RetrieveKnowledgeInput(BaseModel):
    """Input for the retrieve_knowledge skill."""

    query: str = Field(..., min_length=1, description="Natural-language search query")
    knowledge_type: KnowledgeType | None = Field(
        default=None, description="Optional filter by knowledge category"
    )
    limit: int = Field(default=5, ge=1, le=50, description="Maximum results to return")


class KnowledgeResult(BaseModel):
    """A single knowledge search result."""

    id: UUID = Field(..., description="Knowledge entry ID")
    content: str = Field(..., description="Text content")
    knowledge_type: KnowledgeType = Field(..., description="Category")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Entry metadata")
    source_artifact_id: UUID | None = Field(default=None, description="Source artifact")
    created_at: datetime = Field(..., description="When the entry was created")


class RetrieveKnowledgeOutput(BaseModel):
    """Output from the retrieve_knowledge skill."""

    results: list[KnowledgeResult] = Field(..., description="Ranked search results")
    query: str = Field(..., description="Echo of the original query")
    total_found: int = Field(..., description="Number of results returned")
