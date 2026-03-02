"""Configuration for the Digital Twin Core."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class TwinCoreConfig(BaseSettings):
    """Configuration for Digital Twin Core.

    All settings can be overridden via environment variables with TWIN_ prefix.
    For example: TWIN_NEO4J_URI, TWIN_NEO4J_USER, TWIN_NEO4J_PASSWORD

    Attributes:
        neo4j_uri: Neo4j database URI (bolt://host:port)
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        constraint_eval_timeout_ms: Timeout for constraint evaluation (ms)
        max_subgraph_depth: Maximum depth for subgraph queries
        enable_query_logging: Enable logging of all Cypher queries
    """

    model_config = ConfigDict(
        env_file=".env",
        env_prefix="TWIN_",
        case_sensitive=False,
    )

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "test"

    constraint_eval_timeout_ms: int = 5000
    max_subgraph_depth: int = 10
    enable_query_logging: bool = False


# Global config instance
config = TwinCoreConfig()
