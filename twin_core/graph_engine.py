"""Graph Engine for Neo4j operations.

This module provides the core interface to the Neo4j database,
including CRUD operations for nodes and edges, schema initialization,
and query execution.
"""

from typing import Any
from uuid import UUID

from neo4j import GraphDatabase, Session
from pydantic import BaseModel

from .config import config
from .exceptions import (
    ArtifactNotFoundError,
    EdgeAlreadyExistsError,
    Neo4jConnectionError,
)
from .models import Artifact, Component, Constraint, EdgeBase, Version


class SubGraph(BaseModel):
    """Response model for subgraph queries.

    Attributes:
        nodes: List of nodes (Artifact, Constraint, Component, etc.)
        edges: List of edges between nodes
        root_id: ID of the root node
        depth: Maximum depth traversed
    """

    nodes: list[Any]
    edges: list[EdgeBase]
    root_id: UUID
    depth: int


class GraphEngine:
    """Neo4j graph database engine for the Digital Twin.

    This class provides low-level CRUD operations for all node and edge types.
    It manages connections, transactions, and schema initialization.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        """Initialize the graph engine.

        Args:
            uri: Neo4j URI (default: from config)
            user: Neo4j username (default: from config)
            password: Neo4j password (default: from config)

        Raises:
            Neo4jConnectionError: If connection fails.
        """
        self.uri = uri or config.neo4j_uri
        self.user = user or config.neo4j_user
        self.password = password or config.neo4j_password

        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # Test connection
            self.driver.verify_connectivity()
        except Exception as e:
            raise Neo4jConnectionError(self.uri, e)

    def close(self) -> None:
        """Close the database connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # ==================== Schema Initialization ====================

    def init_schema(self) -> None:
        """Initialize Neo4j schema with constraints and indexes.

        This method is idempotent and safe to run multiple times.
        Creates all constraints and indexes defined in the spec (Section 7).
        """
        with self.driver.session() as session:
            # Primary key constraints (unique IDs)
            session.run(
                "CREATE CONSTRAINT artifact_id IF NOT EXISTS "
                "FOR (a:Artifact) REQUIRE a.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT constraint_id IF NOT EXISTS "
                "FOR (c:Constraint) REQUIRE c.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT version_id IF NOT EXISTS "
                "FOR (v:Version) REQUIRE v.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT component_id IF NOT EXISTS "
                "FOR (p:Component) REQUIRE p.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT agent_id IF NOT EXISTS "
                "FOR (ag:Agent) REQUIRE ag.id IS UNIQUE"
            )

            # Lookup indexes
            session.run(
                "CREATE INDEX artifact_domain IF NOT EXISTS "
                "FOR (a:Artifact) ON (a.domain)"
            )
            session.run(
                "CREATE INDEX artifact_type IF NOT EXISTS "
                "FOR (a:Artifact) ON (a.type)"
            )
            session.run(
                "CREATE INDEX artifact_path IF NOT EXISTS "
                "FOR (a:Artifact) ON (a.file_path)"
            )
            session.run(
                "CREATE INDEX constraint_domain IF NOT EXISTS "
                "FOR (c:Constraint) ON (c.domain)"
            )
            session.run(
                "CREATE INDEX constraint_status IF NOT EXISTS "
                "FOR (c:Constraint) ON (c.status)"
            )
            session.run(
                "CREATE INDEX version_branch IF NOT EXISTS "
                "FOR (v:Version) ON (v.branch_name)"
            )
            session.run(
                "CREATE INDEX component_part IF NOT EXISTS "
                "FOR (p:Component) ON (p.part_number)"
            )
            session.run(
                "CREATE INDEX component_mfr IF NOT EXISTS "
                "FOR (p:Component) ON (p.manufacturer)"
            )

    def clear_all(self) -> None:
        """Clear all nodes and edges from the database.

        WARNING: This is destructive and cannot be undone.
        Use only for testing or reset operations.
        """
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    # ==================== Node Operations ====================

    async def create_node(self, node_type: str, properties: dict) -> UUID:
        """Create a node in the graph.

        Args:
            node_type: Node label (e.g., "Artifact", "Constraint")
            properties: Node properties as dictionary

        Returns:
            UUID of the created node.
        """
        with self.driver.session() as session:
            result = session.run(
                f"CREATE (n:{node_type} $props) RETURN n.id",
                props=properties,
            )
            record = result.single()
            return UUID(record["n.id"])

    async def get_node(self, node_id: UUID, node_type: str) -> dict | None:
        """Get a node by ID.

        Args:
            node_id: UUID of the node
            node_type: Node label

        Returns:
            Node properties as dict, or None if not found.
        """
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (n:{node_type} {{id: $id}}) RETURN n",
                id=str(node_id),
            )
            record = result.single()
            if record:
                return dict(record["n"])
            return None

    async def update_node(
        self, node_id: UUID, node_type: str, updates: dict
    ) -> dict:
        """Update a node's properties.

        Args:
            node_id: UUID of the node
            node_type: Node label
            updates: Dictionary of properties to update

        Returns:
            Updated node properties.

        Raises:
            ArtifactNotFoundError: If node not found.
        """
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (n:{node_type} {{id: $id}}) "
                "SET n += $updates "
                "RETURN n",
                id=str(node_id),
                updates=updates,
            )
            record = result.single()
            if not record:
                raise ArtifactNotFoundError(node_id)
            return dict(record["n"])

    async def delete_node(self, node_id: UUID, node_type: str) -> bool:
        """Delete a node and all its edges.

        Args:
            node_id: UUID of the node
            node_type: Node label

        Returns:
            True if deleted, False if not found.
        """
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (n:{node_type} {{id: $id}}) "
                "DETACH DELETE n "
                "RETURN count(n) as deleted",
                id=str(node_id),
            )
            record = result.single()
            return record["deleted"] > 0

    async def list_nodes(
        self, node_type: str, filters: dict | None = None
    ) -> list[dict]:
        """List nodes with optional filters.

        Args:
            node_type: Node label
            filters: Optional filter dictionary

        Returns:
            List of node properties.
        """
        with self.driver.session() as session:
            if filters:
                # Build WHERE clause from filters
                where_parts = [f"n.{k} = ${k}" for k in filters.keys()]
                where_clause = " AND ".join(where_parts)
                result = session.run(
                    f"MATCH (n:{node_type}) WHERE {where_clause} RETURN n",
                    **filters,
                )
            else:
                result = session.run(f"MATCH (n:{node_type}) RETURN n")

            return [dict(record["n"]) for record in result]

    # ==================== Edge Operations ====================

    async def create_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: str,
        properties: dict | None = None,
    ) -> EdgeBase:
        """Create an edge between two nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            edge_type: Edge type (e.g., "DEPENDS_ON")
            properties: Optional edge properties

        Returns:
            Created edge.

        Raises:
            EdgeAlreadyExistsError: If edge already exists.
        """
        props = properties or {}
        props["source_id"] = str(source_id)
        props["target_id"] = str(target_id)
        props["edge_type"] = edge_type

        with self.driver.session() as session:
            # Check if edge already exists
            existing = session.run(
                f"MATCH (a)-[r:{edge_type}]->(b) "
                "WHERE a.id = $source_id AND b.id = $target_id "
                "RETURN r",
                source_id=str(source_id),
                target_id=str(target_id),
            )
            if existing.single():
                raise EdgeAlreadyExistsError(source_id, target_id, edge_type)

            # Create edge
            result = session.run(
                f"MATCH (a), (b) "
                "WHERE a.id = $source_id AND b.id = $target_id "
                f"CREATE (a)-[r:{edge_type} $props]->(b) "
                "RETURN r",
                source_id=str(source_id),
                target_id=str(target_id),
                props=props,
            )
            record = result.single()
            return EdgeBase.from_neo4j_props(dict(record["r"]))

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
        with self.driver.session() as session:
            if direction == "outgoing":
                pattern = "(a)-[r]->(b)"
                where = "a.id = $node_id"
            elif direction == "incoming":
                pattern = "(a)<-[r]-(b)"
                where = "a.id = $node_id"
            else:  # both
                pattern = "(a)-[r]-(b)"
                where = "a.id = $node_id"

            if edge_type:
                pattern = pattern.replace("[r]", f"[r:{edge_type}]")

            result = session.run(
                f"MATCH {pattern} WHERE {where} RETURN r", node_id=str(node_id)
            )
            return [EdgeBase.from_neo4j_props(dict(record["r"])) for record in result]

    async def delete_edge(
        self, source_id: UUID, target_id: UUID, edge_type: str
    ) -> bool:
        """Delete an edge between two nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            edge_type: Edge type

        Returns:
            True if deleted, False if not found.
        """
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (a)-[r:{edge_type}]->(b) "
                "WHERE a.id = $source_id AND b.id = $target_id "
                "DELETE r "
                "RETURN count(r) as deleted",
                source_id=str(source_id),
                target_id=str(target_id),
            )
            record = result.single()
            return record["deleted"] > 0

    # ==================== Query Operations ====================

    async def get_subgraph(
        self,
        root_id: UUID,
        depth: int = 2,
        edge_types: list[str] | None = None,
    ) -> SubGraph:
        """Extract a subgraph starting from a root node.

        Args:
            root_id: Root node UUID
            depth: Maximum traversal depth
            edge_types: Optional list of edge types to traverse

        Returns:
            SubGraph containing nodes and edges.
        """
        with self.driver.session() as session:
            # Build edge type filter
            edge_filter = ""
            if edge_types:
                edge_filter = "|".join(edge_types)
                edge_filter = f":{edge_filter}"

            # Query subgraph
            result = session.run(
                f"MATCH path = (root)-[{edge_filter}*1..{depth}]-(node) "
                "WHERE root.id = $root_id "
                "RETURN nodes(path) as nodes, relationships(path) as edges",
                root_id=str(root_id),
            )

            all_nodes = []
            all_edges = []
            for record in result:
                all_nodes.extend([dict(n) for n in record["nodes"]])
                all_edges.extend([dict(e) for e in record["edges"]])

            # Deduplicate
            unique_nodes = {n["id"]: n for n in all_nodes}.values()
            unique_edges = {
                (e.get("source_id"), e.get("target_id"), e.get("edge_type")): e
                for e in all_edges
            }.values()

            return SubGraph(
                nodes=list(unique_nodes),
                edges=[EdgeBase.from_neo4j_props(e) for e in unique_edges],
                root_id=root_id,
                depth=depth,
            )

    async def query_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """Execute a raw Cypher query (read-only).

        Args:
            query: Cypher query string
            params: Optional query parameters

        Returns:
            List of result records as dictionaries.
        """
        with self.driver.session() as session:
            result = session.run(query, **(params or {}))
            return [dict(record) for record in result]

    # ==================== Batch Operations ====================

    async def create_nodes_batch(
        self, nodes: list[tuple[str, dict]]
    ) -> list[UUID]:
        """Create multiple nodes in a single transaction.

        Args:
            nodes: List of (node_type, properties) tuples

        Returns:
            List of created node UUIDs.
        """
        node_ids = []
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for node_type, props in nodes:
                    result = tx.run(
                        f"CREATE (n:{node_type} $props) RETURN n.id",
                        props=props,
                    )
                    record = result.single()
                    node_ids.append(UUID(record["n.id"]))
                tx.commit()
        return node_ids

    async def create_edges_batch(
        self, edges: list[tuple[UUID, UUID, str, dict]]
    ) -> list[EdgeBase]:
        """Create multiple edges in a single transaction.

        Args:
            edges: List of (source_id, target_id, edge_type, properties) tuples

        Returns:
            List of created edges.
        """
        created_edges = []
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for source_id, target_id, edge_type, props in edges:
                    props["source_id"] = str(source_id)
                    props["target_id"] = str(target_id)
                    props["edge_type"] = edge_type

                    result = tx.run(
                        f"MATCH (a), (b) "
                        "WHERE a.id = $source_id AND b.id = $target_id "
                        f"CREATE (a)-[r:{edge_type} $props]->(b) "
                        "RETURN r",
                        source_id=str(source_id),
                        target_id=str(target_id),
                        props=props,
                    )
                    record = result.single()
                    created_edges.append(EdgeBase.from_neo4j_props(dict(record["r"])))
                tx.commit()
        return created_edges
