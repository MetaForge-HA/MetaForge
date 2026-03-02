"""Constraint models for the Digital Twin.

Constraints are first-class graph nodes that represent rules to be evaluated
across one or more artifacts.
"""

import json
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ConstraintSeverity(StrEnum):
    """Severity levels for constraint violations."""

    ERROR = "error"  # Must be resolved  blocks commit
    WARNING = "warning"  # Should be resolved  does not block
    INFO = "info"  # Informational only


class ConstraintStatus(StrEnum):
    """Evaluation status of a constraint."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNEVALUATED = "unevaluated"
    SKIPPED = "skipped"  # Constraint not applicable to current state


class Constraint(BaseModel):
    """A constraint node in the Digital Twin graph.

    Attributes:
        id: Unique identifier (auto-generated)
        name: Human-readable name (e.g., "max_voltage_3v3")
        expression: Python expression evaluated against ConstraintContext
        severity: ERROR, WARNING, or INFO
        status: Current evaluation status
        domain: Primary domain (e.g., "electronics")
        cross_domain: Whether constraint spans multiple domains
        source: Origin: "user", "agent", or "system"
        message: Human-readable description
        last_evaluated: When the constraint was last checked
        metadata: Additional context
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    expression: str
    severity: ConstraintSeverity
    status: ConstraintStatus = ConstraintStatus.UNEVALUATED
    domain: str
    cross_domain: bool = False
    source: str
    message: str = ""
    last_evaluated: datetime | None = None
    metadata: dict = Field(default_factory=dict)

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j node properties."""
        return {
            "id": str(self.id),
            "name": self.name,
            "expression": self.expression,
            "severity": self.severity.value,
            "status": self.status.value,
            "domain": self.domain,
            "cross_domain": self.cross_domain,
            "source": self.source,
            "message": self.message,
            "last_evaluated": self.last_evaluated.isoformat() if self.last_evaluated else None,
            "metadata": json.dumps(self.metadata),  # JSON serialize
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "Constraint":
        """Create Constraint from Neo4j node properties."""
        # Deserialize metadata
        metadata = props.get("metadata", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return cls(
            id=UUID(props["id"]),
            name=props["name"],
            expression=props["expression"],
            severity=ConstraintSeverity(props["severity"]),
            status=ConstraintStatus(props["status"]),
            domain=props["domain"],
            cross_domain=props.get("cross_domain", False),
            source=props["source"],
            message=props.get("message", ""),
            last_evaluated=datetime.fromisoformat(props["last_evaluated"])
            if props.get("last_evaluated")
            else None,
            metadata=metadata,
        )


class ConstraintContext(BaseModel):
    """Context provided to constraint expressions during evaluation.

    This class is injected as 'ctx' into constraint expressions.
    It provides access to the current graph state for querying artifacts,
    components, and dependencies.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def artifact(self, name: str) -> "Artifact":  # noqa: F821
        """Retrieve an artifact by name from the current graph state.

        Args:
            name: Name of the artifact to retrieve.

        Returns:
            Artifact instance.

        Raises:
            KeyError: If artifact not found.
        """
        raise NotImplementedError("Must be implemented by concrete context")

    def artifacts(
        self,
        domain: str | None = None,
        artifact_type: "ArtifactType | None" = None,  # noqa: F821
    ) -> list["Artifact"]:  # noqa: F821
        """Query artifacts by domain and/or type.

        Args:
            domain: Filter by engineering domain (optional).
            artifact_type: Filter by artifact type (optional).

        Returns:
            List of matching artifacts.
        """
        raise NotImplementedError("Must be implemented by concrete context")

    def components(self) -> list["Component"]:  # noqa: F821
        """Retrieve all components in the current design.

        Returns:
            List of Component instances.
        """
        raise NotImplementedError("Must be implemented by concrete context")

    def dependents(self, artifact_id: UUID) -> list["Artifact"]:  # noqa: F821
        """Get all artifacts that depend on the given artifact.

        Args:
            artifact_id: UUID of the artifact.

        Returns:
            List of dependent artifacts.
        """
        raise NotImplementedError("Must be implemented by concrete context")


class ConstraintViolation(BaseModel):
    """A constraint violation result.

    Attributes:
        constraint_id: ID of the violated constraint
        constraint_name: Human-readable constraint name
        severity: Severity level of the violation
        message: Description of the violation
        artifact_ids: Artifacts involved in the violation
        expression: The constraint expression that failed
        evaluated_at: When the violation was detected
    """

    constraint_id: UUID
    constraint_name: str
    severity: ConstraintSeverity
    message: str
    artifact_ids: list[UUID]
    expression: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConstraintEvaluationResult(BaseModel):
    """Result of evaluating constraints on a proposed commit.

    Attributes:
        passed: Whether all ERROR-severity constraints passed
        violations: List of constraint violations (FAIL)
        warnings: List of constraint warnings (WARN)
        evaluated_count: Number of constraints evaluated
        skipped_count: Number of constraints skipped
        duration_ms: Evaluation duration in milliseconds
    """

    passed: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)
    warnings: list[ConstraintViolation] = Field(default_factory=list)
    evaluated_count: int
    skipped_count: int
    duration_ms: float
