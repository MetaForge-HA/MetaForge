"""Pydantic schemas for the CAD conversion API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConversionStatus(StrEnum):
    """Status of a conversion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityLevel(StrEnum):
    """Tessellation quality tier for CAD-to-GLB conversion."""

    PREVIEW = "preview"
    STANDARD = "standard"
    FINE = "fine"


class BoundingBox(BaseModel):
    """Axis-aligned bounding box for a part."""

    min_x: float = Field(default=0.0, description="Minimum X coordinate.")
    min_y: float = Field(default=0.0, description="Minimum Y coordinate.")
    min_z: float = Field(default=0.0, description="Minimum Z coordinate.")
    max_x: float = Field(default=0.0, description="Maximum X coordinate.")
    max_y: float = Field(default=0.0, description="Maximum Y coordinate.")
    max_z: float = Field(default=0.0, description="Maximum Z coordinate.")


class PartTreeNode(BaseModel):
    """A single node in the hierarchical part tree from a STEP file."""

    name: str = Field(description="Part or assembly name.")
    mesh_name: str = Field(default="", description="Name of the corresponding mesh in GLB.")
    children: list[PartTreeNode] = Field(
        default_factory=list,
        description="Child parts or sub-assemblies.",
    )
    bounding_box: BoundingBox = Field(
        default_factory=BoundingBox,
        description="Axis-aligned bounding box.",
    )


class ModelStats(BaseModel):
    """Aggregate statistics for the converted model."""

    triangle_count: int = Field(default=0, description="Total number of triangles.")
    file_size: int = Field(default=0, description="GLB file size in bytes.")
    vertex_count: int = Field(default=0, description="Total number of vertices.")


class PartTreeMetadata(BaseModel):
    """Hierarchical part tree and statistics extracted from a STEP file."""

    parts: list[PartTreeNode] = Field(
        default_factory=list,
        description="Top-level parts and assemblies.",
    )
    materials: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Materials referenced in the model.",
    )
    stats: ModelStats = Field(
        default_factory=ModelStats,
        description="Aggregate model statistics.",
    )


class ConversionRequest(BaseModel):
    """Query parameters for a conversion request."""

    quality: str = Field(
        default="standard",
        pattern="^(preview|standard|fine)$",
        description="Tessellation quality tier.",
    )


class ConversionResult(BaseModel):
    """Response payload for a completed conversion."""

    hash: str = Field(description="SHA-256 content hash of the source file.")
    glb_url: str = Field(description="URL to download the GLB file.")
    metadata: dict[str, Any] = Field(description="Part tree, stats, materials.")
    cached: bool = Field(description="True if result was served from cache.")


class ConversionJob(BaseModel):
    """Status of a conversion job (for future async support)."""

    job_id: str
    status: ConversionStatus = Field(
        default=ConversionStatus.PENDING,
        description="Current status of the conversion job.",
    )
    result: ConversionResult | None = None
