
"""Twin API - Public interface for all Digital Twin operations.

This is the ONLY interface through which agents, the orchestrator,
and the gateway should interact with the Digital Twin graph.

All operations go through this API: artifact CRUD, constraint evaluation,
versioning, component management, and graph queries.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from .config import config
from .constraint_engine.validator import ConstraintValidator
from .exceptions import (
    ArtifactNotFoundError,
    ComponentNotFoundError,
    ConstraintNotFoundError,
)
from .graph_engine import GraphEngine, SubGraph
from .models import (
    Artifact,
    ArtifactType,
    Component,
    Constraint,
    ConstraintEvaluationResult,
    EdgeBase,
    Version,
    VersionDiff,
)
from .validation_engine.schema_validator import ArtifactSchemaValidator
from .versioning.branch import BranchManager
from .versioning.diff import DiffEngine
from .versioning.merge import MergeEngine


class TwinAPI(ABC):
    """Abstract base class for the Digital Twin API.

    Defines the contract for all Twin operations. Concrete implementations
    (e.g., Neo4jTwinAPI) provide the actual functionality.
    """

    # ==================== Artifact Operations ====================

    @abstractmethod
    async def create_artifact(
        self, artifact: Artifact, branch: str = "main"
    ) -> Artifact:
        """Create a new artifact.

        Args:
            artifact: Artifact to create
            branch: Branch to create artifact on

        Returns:
            Created artifact with generated ID.
        """
        ...

    @abstractmethod
    async def get_artifact(
        self, artifact_id: UUID, branch: str = "main"
    ) -> Artifact | None:
        """Get an artifact by ID.

        Args:
            artifact_id: Artifact UUID
            branch: Branch to query

        Returns:
            Artifact if found, None otherwise.
        """
        ...

    @abstractmethod
    async def update_artifact(
        self, artifact_id: UUID, updates: dict, branch: str = "main"
    ) -> Artifact:
        """Update an artifact's properties.

        Args:
            artifact_id: Artifact UUID
            updates: Dictionary of properties to update
            branch: Branch to update on

        Returns:
            Updated artifact.

        Raises:
            ArtifactNotFoundError: If artifact not found.
        """
        ...

    @abstractmethod
    async def delete_artifact(
        self, artifact_id: UUID, branch: str = "main"
    ) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: Artifact UUID
            branch: Branch to delete from

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def list_artifacts(
        self,
        branch: str = "main",
        domain: str | None = None,
        artifact_type: ArtifactType | None = None,
    ) -> list[Artifact]:
        """List artifacts with optional filters.

        Args:
            branch: Branch to query
            domain: Filter by domain (optional)
            artifact_type: Filter by type (optional)

        Returns:
            List of artifacts matching filters.
        """
        ...

    # ==================== Constraint Operations ====================

    @abstractmethod
    async def create_constraint(self, constraint: Constraint) -> Constraint:
        """Create a new constraint.

        Args:
            constraint: Constraint to create

        Returns:
            Created constraint.
        """
        ...

    @abstractmethod
    async def get_constraint(
        self, constraint_id: UUID
    ) -> Constraint | None:
        """Get a constraint by ID.

        Args:
            constraint_id: Constraint UUID

        Returns:
            Constraint if found, None otherwise.
        """
        ...

    @abstractmethod
    async def evaluate_constraints(
        self, branch: str = "main"
    ) -> ConstraintEvaluationResult:
        """Evaluate all constraints on a branch.

        Args:
            branch: Branch to evaluate

        Returns:
            Constraint evaluation result.
        """
        ...

    # ==================== Component Operations ====================

    @abstractmethod
    async def add_component(self, component: Component) -> Component:
        """Add a component to the design.

        Args:
            component: Component to add

        Returns:
            Added component.
        """
        ...

    @abstractmethod
    async def get_component(
        self, component_id: UUID
    ) -> Component | None:
        """Get a component by ID.

        Args:
            component_id: Component UUID

        Returns:
            Component if found, None otherwise.
        """
        ...

    @abstractmethod
    async def find_components(self, query: dict) -> list[Component]:
        """Find components matching a query.

        Args:
            query: Query filters (e.g., {"manufacturer": "TI", "package": "QFP-48"})

        Returns:
            List of matching components.
        """
        ...

    # ==================== Relationship Operations ====================

    @abstractmethod
    async def add_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: str,
        metadata: dict | None = None,
    ) -> EdgeBase:
        """Add an edge between two nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            edge_type: Edge type (e.g., "DEPENDS_ON")
            metadata: Optional edge properties

        Returns:
            Created edge.
        """
        ...

    @abstractmethod
    async def get_edges(
        self,
        node_id: UUID,
        direction: str = "outgoing",
        edge_type: str | None = None,
    ) -> list[EdgeBase]:
        """Get edges connected to a node.

        Args:
            node_id: Node UUID
            direction: "outgoing", "incoming", or "both"
            edge_type: Optional edge type filter

        Returns:
            List of edges.
        """
        ...

    @abstractmethod
    async def remove_edge(
        self, source_id: UUID, target_id: UUID, edge_type: str
    ) -> bool:
        """Remove an edge.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            edge_type: Edge type

        Returns:
            True if removed, False if not found.
        """
        ...

    # ==================== Query Operations ====================

    @abstractmethod
    async def get_subgraph(
        self,
        root_id: UUID,
        depth: int = 2,
        edge_types: list[str] | None = None,
    ) -> SubGraph:
        """Extract a subgraph from a root node.

        Args:
            root_id: Root node UUID
            depth: Maximum traversal depth
            edge_types: Optional list of edge types to traverse

        Returns:
            SubGraph containing nodes and edges.
        """
        ...

    @abstractmethod
    async def query_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """Execute a raw Cypher query (read-only).

        Args:
            query: Cypher query string
            params: Optional query parameters

        Returns:
            List of result records.
        """
        ...

    # ==================== Versioning Operations ====================

    @abstractmethod
    async def create_branch(
        self, name: str, from_branch: str = "main"
    ) -> str:
        """Create a new branch.

        Args:
            name: Branch name
            from_branch: Branch to branch from

        Returns:
            Created branch name.
        """
        ...

    @abstractmethod
    async def commit(
        self, branch: str, message: str, author: str
    ) -> Version:
        """Create a commit on a branch.

        Args:
            branch: Branch name
            message: Commit message
            author: Commit author

        Returns:
            Created version.
        """
        ...

    @abstractmethod
    async def merge(
        self, source: str, target: str, message: str, author: str
    ) -> Version:
        """Merge source branch into target branch.

        Args:
            source: Source branch name
            target: Target branch name
            message: Merge commit message
            author: Merge author

        Returns:
            Merge commit version.
        """
        ...

    @abstractmethod
    async def diff(self, branch_a: str, branch_b: str) -> VersionDiff:
        """Compute diff between two branches.

        Args:
            branch_a: First branch name
            branch_b: Second branch name

        Returns:
            VersionDiff showing changes.
        """
        ...

    @abstractmethod
    async def log(
        self, branch: str = "main", limit: int = 50
    ) -> list[Version]:
        """Get version history for a branch.

        Args:
            branch: Branch name
            limit: Maximum number of versions

        Returns:
            List of versions in reverse chronological order.
        """
        ...


class Neo4jTwinAPI(TwinAPI):
    """Neo4j implementation of the Twin API.

    This is the concrete implementation that uses Neo4j as the backend.
    """

    def __init__(
        self,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ):
        """Initialize Neo4j Twin API.

        Args:
            neo4j_uri: Neo4j URI (default: from config)
            neo4j_user: Neo4j username (default: from config)
            neo4j_password: Neo4j password (default: from config)
        """
        self.graph = GraphEngine(neo4j_uri, neo4j_user, neo4j_password)
        self.constraint_validator = ConstraintValidator(self.graph)
        self.validator = ArtifactSchemaValidator()
        self.branch_manager = BranchManager(self.graph)
        self.diff_engine = DiffEngine(self.graph)
        self.merge_engine = MergeEngine(self.graph)

    def close(self) -> None:
        """Close database connections."""
        self.graph.close()

    # ==================== Artifact Operations ====================

    async def create_artifact(
        self, artifact: Artifact, branch: str = "main"
    ) -> Artifact:
        """Create a new artifact."""
        # 1. Validate artifact schema
        validation_result = self.validator.validate_artifact(artifact)
        if not validation_result.valid:
            from .exceptions import ValidationError
            raise ValidationError(artifact.id, validation_result.errors)

        # 2. Create artifact node in graph
        props = artifact.to_neo4j_props()
        artifact_id = await self.graph.create_node("Artifact", props)

        # 3. Return created artifact
        artifact.id = artifact_id
        return artifact

    async def get_artifact(
        self, artifact_id: UUID, branch: str = "main"
    ) -> Artifact | None:
        """Get an artifact by ID."""
        props = await self.graph.get_node(artifact_id, "Artifact")
        if props:
            return Artifact.from_neo4j_props(props)
        return None

    async def update_artifact(
        self, artifact_id: UUID, updates: dict, branch: str = "main"
    ) -> Artifact:
        """Update an artifact."""
        props = await self.graph.update_node(artifact_id, "Artifact", updates)
        return Artifact.from_neo4j_props(props)

    async def delete_artifact(
        self, artifact_id: UUID, branch: str = "main"
    ) -> bool:
        """Delete an artifact."""
        return await self.graph.delete_node(artifact_id, "Artifact")

    async def list_artifacts(
        self,
        branch: str = "main",
        domain: str | None = None,
        artifact_type: ArtifactType | None = None,
    ) -> list[Artifact]:
        """List artifacts with filters."""
        filters = {}
        if domain:
            filters["domain"] = domain
        if artifact_type:
            filters["type"] = artifact_type.value

        props_list = await self.graph.list_nodes("Artifact", filters)
        return [Artifact.from_neo4j_props(props) for props in props_list]

    # ==================== Constraint Operations ====================

    async def create_constraint(self, constraint: Constraint) -> Constraint:
        """Create a new constraint."""
        props = constraint.to_neo4j_props()
        constraint_id = await self.graph.create_node("Constraint", props)
        constraint.id = constraint_id
        return constraint

    async def get_constraint(
        self, constraint_id: UUID
    ) -> Constraint | None:
        """Get a constraint by ID."""
        props = await self.graph.get_node(constraint_id, "Constraint")
        if props:
            return Constraint.from_neo4j_props(props)
        return None

    async def evaluate_constraints(
        self, branch: str = "main"
    ) -> ConstraintEvaluationResult:
        """Evaluate all constraints."""
        # TODO: Get all artifacts on branch and evaluate constraints
        return await self.constraint_validator.evaluate_constraints_for_commit(
            branch, []
        )

    # ==================== Component Operations ====================

    async def add_component(self, component: Component) -> Component:
        """Add a component."""
        props = component.to_neo4j_props()
        component_id = await self.graph.create_node("Component", props)
        component.id = component_id
        return component

    async def get_component(
        self, component_id: UUID
    ) -> Component | None:
        """Get a component by ID."""
        props = await self.graph.get_node(component_id, "Component")
        if props:
            return Component.from_neo4j_props(props)
        return None

    async def find_components(self, query: dict) -> list[Component]:
        """Find components matching query."""
        props_list = await self.graph.list_nodes("Component", query)
        return [Component.from_neo4j_props(props) for props in props_list]

    # ==================== Relationship Operations ====================

    async def add_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: str,
        metadata: dict | None = None,
    ) -> EdgeBase:
        """Add an edge."""
        return await self.graph.create_edge(
            source_id, target_id, edge_type, metadata
        )

    async def get_edges(
        self,
        node_id: UUID,
        direction: str = "outgoing",
        edge_type: str | None = None,
    ) -> list[EdgeBase]:
        """Get edges for a node."""
        return await self.graph.get_edges(node_id, direction, edge_type)

    async def remove_edge(
        self, source_id: UUID, target_id: UUID, edge_type: str
    ) -> bool:
        """Remove an edge."""
        return await self.graph.delete_edge(source_id, target_id, edge_type)

    # ==================== Query Operations ====================

    async def get_subgraph(
        self,
        root_id: UUID,
        depth: int = 2,
        edge_types: list[str] | None = None,
    ) -> SubGraph:
        """Get subgraph from root node."""
        return await self.graph.get_subgraph(root_id, depth, edge_types)

    async def query_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """Execute raw Cypher query."""
        return await self.graph.query_cypher(query, params)

    # ==================== Versioning Operations ====================

    async def create_branch(
        self, name: str, from_branch: str = "main"
    ) -> str:
        """Create a new branch."""
        # Get HEAD of from_branch
        head = await self.branch_manager.get_head(from_branch)
        return await self.branch_manager.create_branch(name, head.id)

    async def commit(
        self, branch: str, message: str, author: str
    ) -> Version:
        """Create a commit."""
        # TODO: Collect modified artifacts, compute snapshot hash
        raise NotImplementedError("Commit not yet implemented")

    async def merge(
        self, source: str, target: str, message: str, author: str
    ) -> Version:
        """Merge branches."""
        return await self.merge_engine.merge(source, target, message, author)

    async def diff(self, branch_a: str, branch_b: str) -> VersionDiff:
        """Compute diff between branches."""
        head_a = await self.branch_manager.get_head(branch_a)
        head_b = await self.branch_manager.get_head(branch_b)
        return await self.diff_engine.diff(head_a.id, head_b.id)

    async def log(
        self, branch: str = "main", limit: int = 50
    ) -> list[Version]:
        """Get version history."""
        return await self.branch_manager.log(branch, limit)
