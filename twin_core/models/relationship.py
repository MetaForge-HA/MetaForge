"""Relationship (edge) models for the Digital Twin graph."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EdgeType(StrEnum):
    """Types of edges in the Digital Twin graph."""

    DEPENDS_ON = "DEPENDS_ON"  # Artifact � Artifact
    IMPLEMENTS = "IMPLEMENTS"  # Artifact � Artifact
    VALIDATES = "VALIDATES"  # Artifact � Artifact
    CONTAINS = "CONTAINS"  # Artifact � Artifact
    VERSIONED_BY = "VERSIONED_BY"  # Artifact � Version
    CONSTRAINED_BY = "CONSTRAINED_BY"  # Artifact � Constraint
    PRODUCED_BY = "PRODUCED_BY"  # Artifact � Agent
    USES_COMPONENT = "USES_COMPONENT"  # Artifact � Component
    PARENT_OF = "PARENT_OF"  # Version � Version
    CONFLICTS_WITH = "CONFLICTS_WITH"  # Constraint � Constraint


class EdgeBase(BaseModel):
    """Base class for all edges in the Digital Twin graph.

    Attributes:
        source_id: UUID of the source node
        target_id: UUID of the target node
        edge_type: Type of edge (from EdgeType enum)
        created_at: Edge creation timestamp
        metadata: Additional edge-specific properties
    """

    source_id: UUID
    target_id: UUID
    edge_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j edge properties."""
        return {
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "edge_type": self.edge_type,
            "created_at": self.created_at.isoformat(),
            **self.metadata,
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "EdgeBase":
        """Create EdgeBase from Neo4j edge properties."""
        metadata = {k: v for k, v in props.items() if k not in ["source_id", "target_id", "edge_type", "created_at"]}
        return cls(
            source_id=UUID(props["source_id"]),
            target_id=UUID(props["target_id"]),
            edge_type=props["edge_type"],
            created_at=datetime.fromisoformat(props["created_at"]) if isinstance(props.get("created_at"), str) else datetime.utcnow(),
            metadata=metadata,
        )


class DependsOnEdge(EdgeBase):
    """Edge representing artifact dependency.

    Additional Properties:
        dependency_type: "hard" or "soft"
        description: Human-readable dependency description
    """

    dependency_type: str = "hard"  # "hard" or "soft"
    description: str = ""

    def __init__(self, **data):
        """Initialize with edge_type set to DEPENDS_ON."""
        data["edge_type"] = EdgeType.DEPENDS_ON
        # Move additional fields to metadata
        metadata = data.get("metadata", {})
        if "dependency_type" in data:
            metadata["dependency_type"] = data.pop("dependency_type")
        if "description" in data:
            metadata["description"] = data.pop("description")
        data["metadata"] = metadata
        super().__init__(**data)


class UsesComponentEdge(EdgeBase):
    """Edge representing artifact using a component.

    Additional Properties:
        reference_designator: Component reference (e.g., "R1", "U3")
        quantity: Number of this component used
    """

    reference_designator: str = ""
    quantity: int = 1

    def __init__(self, **data):
        """Initialize with edge_type set to USES_COMPONENT."""
        data["edge_type"] = EdgeType.USES_COMPONENT
        # Move additional fields to metadata
        metadata = data.get("metadata", {})
        if "reference_designator" in data:
            metadata["reference_designator"] = data.pop("reference_designator")
        if "quantity" in data:
            metadata["quantity"] = data.pop("quantity")
        data["metadata"] = metadata
        super().__init__(**data)


class ConstrainedByEdge(EdgeBase):
    """Edge representing artifact constrained by a constraint.

    Additional Properties:
        scope: "local" or "global"
        priority: Constraint priority (higher = evaluated first)
    """

    scope: str = "local"  # "local" or "global"
    priority: int = 0

    def __init__(self, **data):
        """Initialize with edge_type set to CONSTRAINED_BY."""
        data["edge_type"] = EdgeType.CONSTRAINED_BY
        # Move additional fields to metadata
        metadata = data.get("metadata", {})
        if "scope" in data:
            metadata["scope"] = data.pop("scope")
        if "priority" in data:
            metadata["priority"] = data.pop("priority")
        data["metadata"] = metadata
        super().__init__(**data)
