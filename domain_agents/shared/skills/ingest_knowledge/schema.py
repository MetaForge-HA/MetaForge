"""Input/output schemas for the ingest_knowledge skill."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from digital_twin.knowledge.store import KnowledgeType


class IngestKnowledgeInput(BaseModel):
    """Input for the ingest_knowledge skill."""

    content: str = Field(..., min_length=1, description="Text content to ingest")
    knowledge_type: KnowledgeType = Field(..., description="Category of knowledge")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    source_artifact_id: UUID | None = Field(
        default=None, description="Source artifact in the Digital Twin"
    )


class IngestKnowledgeOutput(BaseModel):
    """Output from the ingest_knowledge skill."""

    entry_id: UUID = Field(..., description="ID of the created knowledge entry")
    embedded: bool = Field(..., description="Whether content was successfully embedded")
