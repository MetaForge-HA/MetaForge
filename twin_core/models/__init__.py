"""Digital Twin models package.

This package contains all Pydantic models for the Digital Twin graph:
- Artifacts: Design outputs (schematics, BOMs, CAD, firmware, etc.)
- Constraints: Rules evaluated across artifacts
- Versions: Git-like version control for the graph
- Relationships: Edges between nodes
- Components: Physical parts with supply chain metadata
- Agents: Agent execution provenance
"""

from .agent import AgentNode
from .artifact import Artifact, ArtifactType, compute_content_hash
from .component import Component, ComponentLifecycle
from .constraint import (
    Constraint,
    ConstraintContext,
    ConstraintEvaluationResult,
    ConstraintSeverity,
    ConstraintStatus,
    ConstraintViolation,
)
from .relationship import (
    ConstrainedByEdge,
    DependsOnEdge,
    EdgeBase,
    EdgeType,
    UsesComponentEdge,
)
from .version import ArtifactChange, Version, VersionDiff, compute_snapshot_hash

__all__ = [
    # Artifacts
    "Artifact",
    "ArtifactType",
    "compute_content_hash",
    # Constraints
    "Constraint",
    "ConstraintSeverity",
    "ConstraintStatus",
    "ConstraintContext",
    "ConstraintViolation",
    "ConstraintEvaluationResult",
    # Versions
    "Version",
    "ArtifactChange",
    "VersionDiff",
    "compute_snapshot_hash",
    # Relationships
    "EdgeBase",
    "EdgeType",
    "DependsOnEdge",
    "UsesComponentEdge",
    "ConstrainedByEdge",
    # Components
    "Component",
    "ComponentLifecycle",
    # Agents
    "AgentNode",
]
