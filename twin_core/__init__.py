"""Digital Twin Core package.

The Digital Twin is the single source of design truth in MetaForge.
It is a versioned, directed property graph stored in Neo4j that captures
every artifact, constraint, relationship, and version in a hardware design.

Main components:
- Models: Pydantic models for all graph nodes and edges
- Graph Engine: Neo4j CRUD operations
- Constraint Engine: Constraint evaluation and validation
- Validation Engine: Schema validation for artifacts
- Versioning: Git-like version control (branch, merge, diff)
- Twin API: Public interface for all graph operations
"""

from .config import TwinCoreConfig, config
from .exceptions import (
    ArtifactNotFoundError,
    BranchNotFoundError,
    CircularDependencyError,
    ComponentNotFoundError,
    ConstraintNotFoundError,
    ConstraintViolationError,
    EdgeAlreadyExistsError,
    MergeConflict,
    MergeConflictError,
    Neo4jConnectionError,
    TwinCoreError,
    ValidationError,
    VersionNotFoundError,
)
from .models import (
    AgentNode,
    Artifact,
    ArtifactChange,
    ArtifactType,
    Component,
    ComponentLifecycle,
    ConstrainedByEdge,
    Constraint,
    ConstraintContext,
    ConstraintEvaluationResult,
    ConstraintSeverity,
    ConstraintStatus,
    ConstraintViolation,
    DependsOnEdge,
    EdgeBase,
    EdgeType,
    UsesComponentEdge,
    Version,
    VersionDiff,
    compute_content_hash,
    compute_snapshot_hash,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Config
    "TwinCoreConfig",
    "config",
    # Exceptions
    "TwinCoreError",
    "ArtifactNotFoundError",
    "ConstraintNotFoundError",
    "VersionNotFoundError",
    "ComponentNotFoundError",
    "BranchNotFoundError",
    "ConstraintViolationError",
    "MergeConflict",
    "MergeConflictError",
    "ValidationError",
    "Neo4jConnectionError",
    "EdgeAlreadyExistsError",
    "CircularDependencyError",
    # Models - Artifacts
    "Artifact",
    "ArtifactType",
    "compute_content_hash",
    # Models - Constraints
    "Constraint",
    "ConstraintSeverity",
    "ConstraintStatus",
    "ConstraintContext",
    "ConstraintViolation",
    "ConstraintEvaluationResult",
    # Models - Versions
    "Version",
    "ArtifactChange",
    "VersionDiff",
    "compute_snapshot_hash",
    # Models - Relationships
    "EdgeBase",
    "EdgeType",
    "DependsOnEdge",
    "UsesComponentEdge",
    "ConstrainedByEdge",
    # Models - Components
    "Component",
    "ComponentLifecycle",
    # Models - Agents
    "AgentNode",
]
