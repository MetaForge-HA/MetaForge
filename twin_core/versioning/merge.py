"""Merge logic for Digital Twin versions.

Implements three-way merge with conflict detection for:
- Content conflicts (same artifact modified differently)
- Structural conflicts (deleted artifact with dependencies)
"""

from uuid import UUID, uuid4

from ..exceptions import MergeConflict, MergeConflictError
from ..graph_engine import GraphEngine
from ..models import Version, VersionDiff, compute_snapshot_hash
from .diff import DiffEngine


class MergeEngine:
    """Handles merging branches in the Digital Twin version graph.

    Implements Git-like three-way merge:
    1. Find merge base (common ancestor)
    2. Compute diffs: base->source, base->target
    3. Detect conflicts
    4. If clean: apply changes and create merge commit
    5. If conflicts: raise MergeConflictError
    """

    def __init__(self, graph_engine: GraphEngine):
        """Initialize merge engine.

        Args:
            graph_engine: GraphEngine instance for queries.
        """
        self.graph = graph_engine
        self.diff_engine = DiffEngine(graph_engine)

    async def merge(
        self, source_branch: str, target_branch: str, message: str, author: str
    ) -> Version:
        """Merge source branch into target branch.

        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into
            message: Merge commit message
            author: Author of the merge

        Returns:
            Merge commit version.

        Raises:
            MergeConflictError: If conflicts are detected.
        """
        # 1. Get HEAD versions of both branches
        # TODO: source_head = await self.branch_manager.get_head(source_branch)
        # TODO: target_head = await self.branch_manager.get_head(target_branch)

        # 2. Find merge base (common ancestor)
        # merge_base = await self._find_merge_base(source_head.id, target_head.id)

        # 3. Compute diffs
        # base_to_source = await self.diff_engine.diff(merge_base, source_head.id)
        # base_to_target = await self.diff_engine.diff(merge_base, target_head.id)

        # 4. Detect conflicts
        # conflicts = self._detect_conflicts(base_to_source, base_to_target)
        # if conflicts:
        #     raise MergeConflictError(conflicts)

        # 5. Apply changes and create merge commit
        # TODO: Apply non-conflicting changes from source to target
        # TODO: Create merge commit with two parents

        # Placeholder return
        raise NotImplementedError("Merge not yet implemented")

    async def _find_merge_base(
        self, version_a: UUID, version_b: UUID
    ) -> UUID:
        """Find the lowest common ancestor of two versions.

        Uses graph traversal to find the merge base.

        Args:
            version_a: First version UUID
            version_b: Second version UUID

        Returns:
            UUID of the merge base version.
        """
        # TODO: Implement graph traversal to find LCA
        # Algorithm:
        # 1. Traverse ancestors of version_a, marking visited
        # 2. Traverse ancestors of version_b, stop at first marked node
        # 3. That node is the merge base

        raise NotImplementedError("Merge base computation not yet implemented")

    def _detect_conflicts(
        self, base_to_source: VersionDiff, base_to_target: VersionDiff
    ) -> list[MergeConflict]:
        """Detect conflicts between two diffs.

        Args:
            base_to_source: Diff from merge base to source
            base_to_target: Diff from merge base to target

        Returns:
            List of conflicts detected.
        """
        conflicts = []

        # Build maps of changed artifacts
        source_changes = {c.artifact_id: c for c in base_to_source.changes}
        target_changes = {c.artifact_id: c for c in base_to_target.changes}

        # Find artifacts modified in both branches
        common_artifacts = set(source_changes.keys()) & set(target_changes.keys())

        for artifact_id in common_artifacts:
            source_change = source_changes[artifact_id]
            target_change = target_changes[artifact_id]

            # Content conflict: both modified with different hashes
            if (
                source_change.change_type == "modified"
                and target_change.change_type == "modified"
                and source_change.new_content_hash != target_change.new_content_hash
            ):
                conflicts.append(
                    MergeConflict(
                        conflict_type="content",
                        artifact_id=artifact_id,
                        source_hash=source_change.new_content_hash,
                        target_hash=target_change.new_content_hash,
                        description="Artifact modified differently in both branches",
                    )
                )

            # Structural conflict: deleted in one, modified in other
            if (
                source_change.change_type == "deleted"
                and target_change.change_type == "modified"
            ) or (
                source_change.change_type == "modified"
                and target_change.change_type == "deleted"
            ):
                conflicts.append(
                    MergeConflict(
                        conflict_type="structural",
                        artifact_id=artifact_id,
                        source_hash=source_change.new_content_hash,
                        target_hash=target_change.new_content_hash,
                        description="Artifact deleted in one branch, modified in other",
                    )
                )

        # TODO: Check for structural conflicts (deleted artifact with dependencies)

        return conflicts

    async def _apply_merge_changes(
        self,
        target_branch: str,
        source_diff: VersionDiff,
        target_head: UUID,
        source_head: UUID,
        message: str,
        author: str,
    ) -> Version:
        """Apply merge changes and create merge commit.

        Args:
            target_branch: Target branch name
            source_diff: Changes from source branch
            target_head: Target HEAD version UUID
            source_head: Source HEAD version UUID
            message: Merge commit message
            author: Author of merge

        Returns:
            Merge commit version.
        """
        # TODO: Apply changes from source_diff to target
        # TODO: Create new version with two parents (target_head, source_head)

        # Compute new snapshot hash
        # artifact_hashes = [...]  # Collect from updated graph
        # snapshot_hash = compute_snapshot_hash(artifact_hashes)

        merge_version = Version(
            branch_name=target_branch,
            parent_id=target_head,
            merge_parent_id=source_head,
            commit_message=message,
            snapshot_hash="",  # TODO: compute
            author=author,
            artifact_ids=[],  # TODO: collect modified artifacts
        )

        # TODO: Save to graph

        return merge_version
