"""Basic smoke tests for Twin Core skeleton.

These tests verify that all models can be imported and instantiated.
They do NOT require a running Neo4j instance.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from twin_core.models import (
    Artifact,
    ArtifactType,
    Constraint,
    ConstraintSeverity,
    ConstraintStatus,
    Version,
    Component,
    ComponentLifecycle,
    AgentNode,
    EdgeBase,
    EdgeType,
    DependsOnEdge,
)


def test_artifact_creation():
    """Test creating an Artifact instance."""
    artifact = Artifact(
        name="test_artifact",
        type=ArtifactType.CAD_MODEL,
        domain="mechanical",
        file_path="models/test.step",
        content_hash="a" * 64,  # 64-char hex string
        format="step",
        created_by="test_agent",
    )

    assert artifact.id is not None
    assert artifact.name == "test_artifact"
    assert artifact.type == ArtifactType.CAD_MODEL
    assert artifact.domain == "mechanical"


def test_artifact_validation_file_path():
    """Test that file path validation works."""
    # Should reject paths with '..'
    with pytest.raises(ValueError, match="must not contain"):
        Artifact(
            name="bad_artifact",
            type=ArtifactType.CAD_MODEL,
            domain="mechanical",
            file_path="../etc/passwd",  # Invalid
            content_hash="a" * 64,
            format="step",
            created_by="test",
        )


def test_artifact_validation_content_hash():
    """Test that content hash validation works."""
    # Should reject non-64-char hashes
    with pytest.raises(ValueError, match="must be 64 characters"):
        Artifact(
            name="bad_artifact",
            type=ArtifactType.CAD_MODEL,
            domain="mechanical",
            file_path="models/test.step",
            content_hash="tooshort",  # Invalid
            format="step",
            created_by="test",
        )


def test_constraint_creation():
    """Test creating a Constraint instance."""
    constraint = Constraint(
        name="max_stress",
        expression="ctx.artifact('simulation').metadata.get('max_stress_mpa', 0) < 500",
        severity=ConstraintSeverity.ERROR,
        domain="mechanical",
        source="user",
        message="Maximum stress must be under 500 MPa",
    )

    assert constraint.id is not None
    assert constraint.name == "max_stress"
    assert constraint.severity == ConstraintSeverity.ERROR
    assert constraint.status == ConstraintStatus.UNEVALUATED


def test_version_creation():
    """Test creating a Version instance."""
    version = Version(
        branch_name="main",
        commit_message="Initial commit",
        snapshot_hash="b" * 64,
        author="human",
    )

    assert version.id is not None
    assert version.branch_name == "main"
    assert version.parent_id is None
    assert not version.is_merge_commit()


def test_version_branch_name_validation():
    """Test branch name validation."""
    # Valid: main
    v1 = Version(
        branch_name="main",
        commit_message="Test",
        snapshot_hash="a" * 64,
        author="test",
    )
    assert v1.branch_name == "main"

    # Valid: agent/<domain>/<task>
    v2 = Version(
        branch_name="agent/mechanical/stress-fix",
        commit_message="Test",
        snapshot_hash="a" * 64,
        author="test",
    )
    assert v2.branch_name == "agent/mechanical/stress-fix"

    # Invalid: wrong format
    with pytest.raises(ValueError, match="branch_name must be"):
        Version(
            branch_name="feature/xyz",  # Invalid format
            commit_message="Test",
            snapshot_hash="a" * 64,
            author="test",
        )


def test_component_creation():
    """Test creating a Component instance."""
    component = Component(
        part_number="STM32F103C8T6",
        manufacturer="STMicroelectronics",
        description="32-bit MCU",
        package="LQFP-48",
        lifecycle=ComponentLifecycle.ACTIVE,
        unit_cost=2.50,
    )

    assert component.id is not None
    assert component.part_number == "STM32F103C8T6"
    assert component.lifecycle == ComponentLifecycle.ACTIVE
    assert component.unit_cost == 2.50


def test_agent_node_creation():
    """Test creating an AgentNode instance."""
    agent = AgentNode(
        agent_type="mechanical",
        domain="mechanical",
        session_id=uuid4(),
        skills_used=["validate_stress", "generate_mesh"],
    )

    assert agent.id is not None
    assert agent.agent_type == "mechanical"
    assert agent.status == "running"
    assert len(agent.skills_used) == 2


def test_agent_lifecycle():
    """Test agent status transitions."""
    agent = AgentNode(
        agent_type="electronics",
        domain="electronics",
        session_id=uuid4(),
    )

    assert agent.status == "running"
    assert agent.completed_at is None

    agent.mark_completed()
    assert agent.status == "completed"
    assert agent.completed_at is not None


def test_edge_creation():
    """Test creating edges."""
    source_id = uuid4()
    target_id = uuid4()

    # Base edge
    edge = EdgeBase(
        source_id=source_id,
        target_id=target_id,
        edge_type=EdgeType.DEPENDS_ON,
    )

    assert edge.source_id == source_id
    assert edge.target_id == target_id
    assert edge.edge_type == EdgeType.DEPENDS_ON


def test_depends_on_edge():
    """Test creating DependsOnEdge."""
    source_id = uuid4()
    target_id = uuid4()

    edge = DependsOnEdge(
        source_id=source_id,
        target_id=target_id,
        dependency_type="hard",
        description="PCB depends on schematic",
    )

    assert edge.edge_type == EdgeType.DEPENDS_ON
    assert edge.metadata["dependency_type"] == "hard"
    assert edge.metadata["description"] == "PCB depends on schematic"


def test_artifact_neo4j_serialization():
    """Test Artifact to/from Neo4j properties."""
    import json

    original = Artifact(
        name="test",
        type=ArtifactType.BOM,
        domain="electronics",
        file_path="bom/test.csv",
        content_hash="c" * 64,
        format="csv",
        metadata={"total_cost": 45.50},
        created_by="test",
    )

    # Serialize
    props = original.to_neo4j_props()
    assert props["name"] == "test"
    assert props["type"] == "bom"
    # Metadata is now JSON-serialized for Neo4j compatibility
    assert isinstance(props["metadata"], str)
    metadata_dict = json.loads(props["metadata"])
    assert metadata_dict["total_cost"] == 45.50

    # Deserialize - round trip should restore original values
    restored = Artifact.from_neo4j_props(props)
    assert restored.name == original.name
    assert restored.type == original.type
    assert restored.metadata == original.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
