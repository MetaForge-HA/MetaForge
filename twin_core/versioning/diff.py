"""Diff computation for Digital Twin versions.

Computes differences between two versions by comparing artifact
content hashes and constraint changes.
"""

from uuid import UUID

from ..graph_engine import GraphEngine
from ..models import Artifact, ArtifactChange, Constraint, VersionDiff


class DiffEngine:
    """Computes diffs between versions.

    Diffs show what changed between two points in the version graph:
    - Added artifacts
    - Modified artifacts (different content hash)
    - Deleted artifacts
    - Added/removed constraints
    """

    def __init__(self, graph_engine: GraphEngine):
        """Initialize diff engine.

        Args:
            graph_engine: GraphEngine instance for queries.
        """
        self.graph = graph_engine

    async def diff(self, version_a: UUID, version_b: UUID) -> VersionDiff:
        """Compute diff between two versions.

        Args:
            version_a: First version UUID (base)
            version_b: Second version UUID (target)

        Returns:
            VersionDiff with artifact and constraint changes.
        """
        # 1. Load artifact snapshots for both versions
        artifacts_a = await self._get_artifacts_at_version(version_a)
        artifacts_b = await self._get_artifacts_at_version(version_b)

        # 2. Compute artifact changes
        changes = self._compute_artifact_changes(artifacts_a, artifacts_b)

        # 3. Compute constraint changes
        constraints_a = await self._get_constraints_at_version(version_a)
        constraints_b = await self._get_constraints_at_version(version_b)

        constraints_added = [c.id for c in constraints_b if c.id not in {ca.id for ca in constraints_a}]
        constraints_removed = [c.id for c in constraints_a if c.id not in {cb.id for cb in constraints_b}]

        return VersionDiff(
            version_a=version_a,
            version_b=version_b,
            changes=changes,
            constraints_added=constraints_added,
            constraints_removed=constraints_removed,
        )

    def _compute_artifact_changes(
        self, artifacts_a: list[Artifact], artifacts_b: list[Artifact]
    ) -> list[ArtifactChange]:
        """Compute changes between two artifact lists.

        Args:
            artifacts_a: Artifacts in version A
            artifacts_b: Artifacts in version B

        Returns:
            List of ArtifactChange instances.
        """
        changes = []

        # Create lookup maps
        map_a = {a.id: a for a in artifacts_a}
        map_b = {a.id: a for a in artifacts_b}

        # Find added artifacts (in B but not in A)
        for artifact_id, artifact_b in map_b.items():
            if artifact_id not in map_a:
                changes.append(
                    ArtifactChange(
                        artifact_id=artifact_id,
                        change_type="added",
                        old_content_hash=None,
                        new_content_hash=artifact_b.content_hash,
                    )
                )

        # Find deleted artifacts (in A but not in B)
        for artifact_id, artifact_a in map_a.items():
            if artifact_id not in map_b:
                changes.append(
                    ArtifactChange(
                        artifact_id=artifact_id,
                        change_type="deleted",
                        old_content_hash=artifact_a.content_hash,
                        new_content_hash=None,
                    )
                )

        # Find modified artifacts (in both, but different content hash)
        for artifact_id in set(map_a.keys()) & set(map_b.keys()):
            artifact_a = map_a[artifact_id]
            artifact_b = map_b[artifact_id]
            if artifact_a.content_hash != artifact_b.content_hash:
                changes.append(
                    ArtifactChange(
                        artifact_id=artifact_id,
                        change_type="modified",
                        old_content_hash=artifact_a.content_hash,
                        new_content_hash=artifact_b.content_hash,
                    )
                )

        return changes

    async def _get_artifacts_at_version(
        self, version_id: UUID
    ) -> list[Artifact]:
        """Get all artifacts at a specific version.

        Args:
            version_id: Version UUID

        Returns:
            List of Artifact instances at that version.
        """
        # TODO: Query artifacts linked to this version via VERSIONED_BY edges
        # MATCH (a:Artifact)-[:VERSIONED_BY]->(v:Version {id: $version_id})
        # RETURN a

        return []

    async def _get_constraints_at_version(
        self, version_id: UUID
    ) -> list[Constraint]:
        """Get all constraints at a specific version.

        Args:
            version_id: Version UUID

        Returns:
            List of Constraint instances at that version.
        """
        # TODO: Query constraints active at this version
        # (Constraints are global, but track when they were added/removed)

        return []
