"""Schema validation for skill definition.json files and skill I/O."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolRef(BaseModel):
    """Reference to an MCP tool required by a skill."""

    tool_id: str = Field(..., description="MCP tool identifier (e.g., 'calculix.run_fea')")
    capability: str = Field(..., description="Specific capability needed from the tool")
    required: bool = Field(default=True, description="Whether the tool must be available")


class SkillDefinition(BaseModel):
    """Validated skill definition from definition.json."""

    name: str = Field(
        ..., pattern=r"^[a-z][a-z0-9_]*$", description="Unique skill identifier (snake_case)"
    )
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Semantic version")
    domain: str = Field(..., description="Engineering domain")
    agent: str = Field(..., description="Agent that owns this skill")
    description: str = Field(..., min_length=10, description="One-line description")
    phase: int = Field(..., ge=1, le=3, description="Minimum phase required")
    tools_required: list[ToolRef] = Field(default_factory=list)
    input_schema: str = Field(..., description="Dotted path to input Pydantic model")
    output_schema: str = Field(..., description="Dotted path to output Pydantic model")
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    retries: int = Field(default=0, ge=0, le=5)
    idempotent: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)


class SchemaValidator:
    """Validates skill definitions and input/output data."""

    @staticmethod
    def validate_definition(data: dict[str, Any]) -> SkillDefinition:
        """Validate a raw definition.json dict. Raises ValidationError on failure."""
        return SkillDefinition.model_validate(data)

    @staticmethod
    def validate_input(schema_class: type[BaseModel], data: Any) -> BaseModel:
        """Validate skill input data against its schema."""
        if isinstance(data, schema_class):
            return data
        if isinstance(data, dict):
            return schema_class.model_validate(data)
        if isinstance(data, BaseModel):
            return schema_class.model_validate(data.model_dump())
        raise TypeError(
            f"Cannot validate input: expected dict or {schema_class.__name__}, "
            f"got {type(data).__name__}"
        )

    @staticmethod
    def validate_output(schema_class: type[BaseModel], data: Any) -> BaseModel:
        """Validate skill output data against its schema."""
        if isinstance(data, schema_class):
            return data
        if isinstance(data, dict):
            return schema_class.model_validate(data)
        if isinstance(data, BaseModel):
            return schema_class.model_validate(data.model_dump())
        raise TypeError(
            f"Cannot validate output: expected dict or {schema_class.__name__}, "
            f"got {type(data).__name__}"
        )
