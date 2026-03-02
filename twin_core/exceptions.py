"""Custom exceptions for the Digital Twin Core."""

from uuid import UUID


class TwinCoreError(Exception):
    """Base exception for all Twin Core errors."""

    pass


class ArtifactNotFoundError(TwinCoreError):
    """Raised when an artifact cannot be found."""

    def __init__(self, artifact_id: UUID):
        self.artifact_id = artifact_id
        super().__init__(f"Artifact not found: {artifact_id}")


class ConstraintNotFoundError(TwinCoreError):
    """Raised when a constraint cannot be found."""

    def __init__(self, constraint_id: UUID):
        self.constraint_id = constraint_id
        super().__init__(f"Constraint not found: {constraint_id}")


class VersionNotFoundError(TwinCoreError):
    """Raised when a version cannot be found."""

    def __init__(self, version_id: UUID):
        self.version_id = version_id
        super().__init__(f"Version not found: {version_id}")


class ComponentNotFoundError(TwinCoreError):
    """Raised when a component cannot be found."""

    def __init__(self, component_id: UUID):
        self.component_id = component_id
        super().__init__(f"Component not found: {component_id}")


class BranchNotFoundError(TwinCoreError):
    """Raised when a branch cannot be found."""

    def __init__(self, branch_name: str):
        self.branch_name = branch_name
        super().__init__(f"Branch not found: {branch_name}")


class ConstraintViolationError(TwinCoreError):
    """Raised when constraints fail validation and block a commit."""

    def __init__(self, violations: list):
        self.violations = violations
        violation_messages = "\n".join([f"- {v.message}" for v in violations])
        super().__init__(f"Constraint violations detected:\n{violation_messages}")


class MergeConflict(Exception):
    """Represents a single merge conflict."""

    def __init__(
        self,
        conflict_type: str,
        artifact_id: UUID,
        source_hash: str | None = None,
        target_hash: str | None = None,
        description: str = "",
    ):
        self.conflict_type = conflict_type  # "content" or "structural"
        self.artifact_id = artifact_id
        self.source_hash = source_hash
        self.target_hash = target_hash
        self.description = description


class MergeConflictError(TwinCoreError):
    """Raised when merge conflicts are detected."""

    def __init__(self, conflicts: list[MergeConflict]):
        self.conflicts = conflicts
        conflict_messages = "\n".join(
            [
                f"- [{c.conflict_type}] Artifact {c.artifact_id}: {c.description}"
                for c in conflicts
            ]
        )
        super().__init__(f"Merge conflicts detected:\n{conflict_messages}")


class ValidationError(TwinCoreError):
    """Raised when artifact validation fails."""

    def __init__(self, artifact_id: UUID, errors: list[str]):
        self.artifact_id = artifact_id
        self.errors = errors
        error_messages = "\n".join([f"- {e}" for e in errors])
        super().__init__(f"Validation failed for artifact {artifact_id}:\n{error_messages}")


class Neo4jConnectionError(TwinCoreError):
    """Raised when Neo4j connection fails."""

    def __init__(self, uri: str, original_error: Exception):
        self.uri = uri
        self.original_error = original_error
        super().__init__(f"Failed to connect to Neo4j at {uri}: {original_error}")


class EdgeAlreadyExistsError(TwinCoreError):
    """Raised when attempting to create an edge that already exists."""

    def __init__(self, source_id: UUID, target_id: UUID, edge_type: str):
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        super().__init__(
            f"Edge already exists: {source_id} --[{edge_type}]--> {target_id}"
        )


class CircularDependencyError(TwinCoreError):
    """Raised when a circular dependency is detected."""

    def __init__(self, artifact_ids: list[UUID]):
        self.artifact_ids = artifact_ids
        cycle = " -> ".join([str(aid) for aid in artifact_ids])
        super().__init__(f"Circular dependency detected: {cycle}")
