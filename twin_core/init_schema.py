#!/usr/bin/env python3
"""Initialize Neo4j schema for the Digital Twin.

This script creates all constraints and indexes required by the Digital Twin.
It is idempotent and safe to run multiple times.

Usage:
    python -m twin_core.init_schema
"""

from twin_core.config import config
from twin_core.graph_engine import GraphEngine


def main():
    """Initialize Neo4j schema."""
    print(f"Connecting to Neo4j at {config.neo4j_uri}...")

    try:
        with GraphEngine() as graph:
            print("Initializing schema (constraints and indexes)...")
            graph.init_schema()
            print("✓ Schema initialized successfully!")

            # Verify connection by listing constraints
            result = graph.driver.session().run(
                "SHOW CONSTRAINTS"
            )
            constraints = list(result)
            print(f"✓ Found {len(constraints)} constraints")

            # Verify indexes
            result = graph.driver.session().run(
                "SHOW INDEXES"
            )
            indexes = list(result)
            print(f"✓ Found {len(indexes)} indexes")

            print("\nSchema initialization complete!")
            print("\nYou can now use the Digital Twin API:")
            print("  from twin_core.api import Neo4jTwinAPI")
            print("  api = Neo4jTwinAPI()")

    except Exception as e:
        print(f"✗ Error initializing schema: {e}")
        print("\nPlease ensure:")
        print("  1. Neo4j is running")
        print("  2. Connection settings in .env are correct:")
        print(f"     TWIN_NEO4J_URI={config.neo4j_uri}")
        print(f"     TWIN_NEO4J_USER={config.neo4j_user}")
        print("     TWIN_NEO4J_PASSWORD=***")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
