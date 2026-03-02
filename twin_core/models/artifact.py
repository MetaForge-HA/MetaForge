"""Artifact models for the Digital Twin.

An Artifact represents any design output: schematic, BOM, PCB layout,
firmware source file, test plan, simulation result, or manufacturing file.
"""

import json
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ArtifactType(StrEnum):
    """Types of artifacts in the design."""

    SCHEMATIC = "schematic"
    PCB_LAYOUT = "pcb_layout"
    BOM = "bom"
    CAD_MODEL = "cad_model"
    FIRMWARE_SOURCE = "firmware_source"
    SIMULATION_RESULT = "simulation_result"
    TEST_PLAN = "test_plan"
    TEST_RESULT = "test_result"
    MANUFACTURING_FILE = "manufacturing_file"
    CONSTRAINT_SET = "constraint_set"
    PRD = "prd"
    PINMAP = "pinmap"
    GERBER = "gerber"
    PICK_AND_PLACE = "pick_and_place"
    DOCUMENTATION = "documentation"


class Artifact(BaseModel):
    """An artifact in the Digital Twin graph.

    Attributes:
        id: Unique identifier (auto-generated)
        name: Human-readable name (e.g., "main_schematic")
        type: Artifact type from ArtifactType enum
        domain: Engineering domain (e.g., "mechanical", "electronics")
        file_path: Relative path within the project directory
        content_hash: SHA-256 hash of file contents
        format: File format (e.g., "kicad_sch", "step", "json")
        metadata: Domain-specific key-value pairs
        created_at: Creation timestamp (auto-generated)
        updated_at: Last modification timestamp (auto-generated)
        created_by: Agent ID or "human"
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    type: ArtifactType
    domain: str
    file_path: str
    content_hash: str
    format: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate that file path is relative and does not contain '..'."""
        if ".." in v:
            raise ValueError("file_path must not contain '..'")
        if v.startswith("/"):
            raise ValueError("file_path must be relative, not absolute")
        return v

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, v: str) -> str:
        """Validate that content hash looks like a SHA-256 hash."""
        if len(v) != 64:
            raise ValueError("content_hash must be 64 characters (SHA-256)")
        # Basic hex check
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("content_hash must be hexadecimal")
        return v

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j node properties.

        Returns:
            Dictionary of properties suitable for Neo4j storage.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type.value,
            "domain": self.domain,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "format": self.format,
            "metadata": json.dumps(self.metadata),  # JSON serialize for Neo4j
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "Artifact":
        """Create Artifact from Neo4j node properties.

        Args:
            props: Dictionary of properties from Neo4j node.

        Returns:
            Artifact instance.
        """
        # Deserialize metadata JSON string
        metadata = props.get("metadata", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return cls(
            id=UUID(props["id"]),
            name=props["name"],
            type=ArtifactType(props["type"]),
            domain=props["domain"],
            file_path=props["file_path"],
            content_hash=props["content_hash"],
            format=props["format"],
            metadata=metadata,
            created_at=datetime.fromisoformat(props["created_at"]),
            updated_at=datetime.fromisoformat(props["updated_at"]),
            created_by=props["created_by"],
        )


def compute_content_hash(file_path: str) -> str:
    """Compute SHA-256 hash of file contents.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal SHA-256 hash string.
    """
    import hashlib

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
