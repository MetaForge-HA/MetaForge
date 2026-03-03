"""Abstract base class for all MetaForge skills."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from uuid import UUID

import structlog
from pydantic import BaseModel

from skill_registry.mcp_bridge import McpBridge

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass
class SkillResult:
    """Wrapper around skill output with execution metadata."""

    success: bool
    data: BaseModel | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class SkillContext:
    """Dependency-injected context for skill execution.

    Provides access to:
    - Digital Twin API (read/write artifacts, constraints)
    - MCP Bridge (invoke external tools)
    - Structured logger (with trace correlation)
    """

    def __init__(
        self,
        twin: Any,  # TwinAPI -- avoid circular import
        mcp: McpBridge,
        logger: structlog.BoundLogger,
        session_id: UUID,
        branch: str = "main",
    ) -> None:
        self.twin = twin
        self.mcp = mcp
        self.logger = logger
        self.session_id = session_id
        self.branch = branch


class SkillBase(ABC, Generic[InputT, OutputT]):
    """Base class for all skills.

    Subclasses must:
    1. Set input_type and output_type class attributes.
    2. Implement the execute() method.
    """

    input_type: type[InputT]
    output_type: type[OutputT]

    def __init__(self, context: SkillContext) -> None:
        self.context = context
        self.logger = context.logger.bind(skill=self.__class__.__name__)

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Execute the skill logic."""
        ...

    async def validate_preconditions(self, input_data: InputT) -> list[str]:
        """Optional: Check preconditions before execution.

        Returns a list of error messages. Empty list means all preconditions met.
        """
        return []

    async def run(self, input_data: InputT) -> SkillResult:
        """Full execution pipeline: validate -> preconditions -> execute -> validate output."""
        start = time.monotonic()

        # Validate input
        if not isinstance(input_data, self.input_type):
            try:
                input_data = self.input_type.model_validate(
                    input_data.model_dump() if isinstance(input_data, BaseModel) else input_data
                )
            except Exception as exc:
                return SkillResult(success=False, errors=[f"Input validation failed: {exc}"])

        # Check preconditions
        errors = await self.validate_preconditions(input_data)
        if errors:
            elapsed = (time.monotonic() - start) * 1000
            return SkillResult(success=False, errors=errors, duration_ms=elapsed)

        # Execute
        try:
            output = await self.execute(input_data)
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            self.logger.error("Skill execution failed", error=str(exc))
            return SkillResult(
                success=False, errors=[f"Execution failed: {exc}"], duration_ms=elapsed
            )

        # Validate output
        if not isinstance(output, self.output_type):
            elapsed = (time.monotonic() - start) * 1000
            return SkillResult(
                success=False,
                errors=[
                    f"Output type mismatch: expected {self.output_type.__name__}, "
                    f"got {type(output).__name__}"
                ],
                duration_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        return SkillResult(success=True, data=output, duration_ms=elapsed)
