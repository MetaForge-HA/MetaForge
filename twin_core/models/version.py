"""Version models for the Digital Twin.

Versions represent point-in-time snapshots of the artifact graph,
forming a Git-like DAG that supports branching and merging.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Version(BaseModel):
    """A version (commit) in the Digital Twin graph.

    Attributes:
        id: Unique identifier (auto-generated)
        branch_name: Branch this version belongs to
        parent_id: Parent version (null for initial version)
        merge_parent_id: Second parent (for merge commits)
        commit_message: Description of changes
        snapshot_hash: Hash of the complete graph state at this version
        author: Agent ID, "human", or "system"
        created_at: Version creation timestamp
        artifact_ids: Artifacts modified in this version
    """

    id: UUID = Field(default_factory=uuid4)
    branch_name: str
    parent_id: UUID | None = None
    merge_parent_id: UUID | None = None
    commit_message: str
    snapshot_hash: str
    author: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    artifact_ids: list[UUID] = Field(default_factory=list)

    @field_validator("branch_name")
    @classmethod
    def validate_branch_name(cls, v: str) -> str:
        """Validate branch name format.

        Valid formats:
        - main
        - agent/<domain>/<task>
        - review/<id>
        """
        if v == "main":
            return v
        if v.startswith("agent/") and v.count("/") == 2:
            return v
        if v.startswith("review/") and v.count("/") == 1:
            return v
        raise ValueError(
            "branch_name must be 'main', 'agent/<domain>/<task>', or 'review/<id>'"
        )

    def is_merge_commit(self) -> bool:
        """Check if this is a merge commit (has two parents).

        Returns:
            True if this is a merge commit, False otherwise.
        """
        return self.merge_parent_id is not None

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j node properties."""
        return {
            "id": str(self.id),
            "branch_name": self.branch_name,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "merge_parent_id": str(self.merge_parent_id) if self.merge_parent_id else None,
            "commit_message": self.commit_message,
            "snapshot_hash": self.snapshot_hash,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "artifact_ids": [str(aid) for aid in self.artifact_ids],
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "Version":
        """Create Version from Neo4j node properties."""
        return cls(
            id=UUID(props["id"]),
            branch_name=props["branch_name"],
            parent_id=UUID(props["parent_id"]) if props.get("parent_id") else None,
            merge_parent_id=UUID(props["merge_parent_id"])
            if props.get("merge_parent_id")
            else None,
            commit_message=props["commit_message"],
            snapshot_hash=props["snapshot_hash"],
            author=props["author"],
            created_at=datetime.fromisoformat(props["created_at"]),
            artifact_ids=[UUID(aid) for aid in props.get("artifact_ids", [])],
        )


class ArtifactChange(BaseModel):
    """Represents a change to an artifact in a version diff.

    Attributes:
        artifact_id: ID of the changed artifact
        change_type: "added", "modified", or "deleted"
        old_content_hash: Content hash before change (None for added)
        new_content_hash: Content hash after change (None for deleted)
    """

    artifact_id: UUID
    change_type: str  # "added", "modified", "deleted"
    old_content_hash: str | None = None
    new_content_hash: str | None = None

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v: str) -> str:
        """Validate change type is one of the allowed values."""
        if v not in ["added", "modified", "deleted"]:
            raise ValueError("change_type must be 'added', 'modified', or 'deleted'")
        return v


class VersionDiff(BaseModel):
    """Difference between two versions.

    Attributes:
        version_a: First version ID (base)
        version_b: Second version ID (target)
        changes: List of artifact changes
        constraints_added: Constraint IDs added in version_b
        constraints_removed: Constraint IDs removed in version_b
    """

    version_a: UUID
    version_b: UUID
    changes: list[ArtifactChange]
    constraints_added: list[UUID] = Field(default_factory=list)
    constraints_removed: list[UUID] = Field(default_factory=list)


def compute_snapshot_hash(artifact_hashes: list[str]) -> str:
    """Compute snapshot hash from artifact content hashes.

    Args:
        artifact_hashes: List of artifact content hashes.

    Returns:
        SHA-256 hash of all artifact hashes combined.
    """
    import hashlib

    # Sort for deterministic ordering
    sorted_hashes = sorted(artifact_hashes)
    combined = "".join(sorted_hashes)
    return hashlib.sha256(combined.encode()).hexdigest()
