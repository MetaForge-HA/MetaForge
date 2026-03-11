"""Common type aliases used across the MetaForge platform.

These aliases provide semantic meaning for UUIDs and timestamps
used throughout domain models, making function signatures more
self-documenting.
"""

from datetime import datetime
from uuid import UUID

import structlog

from observability.tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer("shared.types.common")

# Semantic type aliases for domain identifiers
NodeId = UUID
"""Unique identifier for a graph node in the Digital Twin."""

VersionId = UUID
"""Unique identifier for a version snapshot."""

ArtifactId = UUID
"""Unique identifier for a design artifact."""

ConstraintId = UUID
"""Unique identifier for a constraint."""

ComponentId = UUID
"""Unique identifier for a hardware component."""

SessionId = UUID
"""Unique identifier for an agent session."""

Timestamp = datetime
"""ISO 8601 timestamp used across events and models."""

__all__ = [
    "ArtifactId",
    "ComponentId",
    "ConstraintId",
    "NodeId",
    "SessionId",
    "Timestamp",
    "VersionId",
]
