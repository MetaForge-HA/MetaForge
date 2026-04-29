"""Constraint engine MCP adapter (MET-383).

Exposes the existing ``twin_core.constraint_engine`` as an MCP tool so
external harnesses can pre-flight constraint validation before
committing graph changes. Without this, the only way to learn about
violations was to write the change and read the gate-engine score —
which is too late for a reconciliation skill that wants to abort the
proposal up front.

The single tool is ``constraint.validate`` — accepts a list of
``work_product_id``s, returns a structured ``ConstraintEvaluationResult``
shape (passed/violations/warnings/evaluated_count/duration_ms).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from observability.tracing import get_tracer
from tool_registry.mcp_server.handlers import ResourceLimits, ToolManifest
from tool_registry.mcp_server.server import McpToolServer
from twin_core.constraint_engine.validator import ConstraintEngine

logger = structlog.get_logger()
tracer = get_tracer("tool_registry.tools.constraint.adapter")


class ConstraintServer(McpToolServer):
    """MCP adapter for the constraint engine.

    The handler delegates to ``ConstraintEngine.evaluate`` — the engine
    instance is injected at construction (so the same engine the
    gateway uses for its own gate scoring is the one the MCP tool
    consults).
    """

    def __init__(self, engine: ConstraintEngine) -> None:
        super().__init__(adapter_id="constraint", version="0.1.0")
        self._engine = engine
        self._register_tools()

    def _register_tools(self) -> None:
        self.register_tool(
            manifest=ToolManifest(
                tool_id="constraint.validate",
                adapter_id="constraint",
                name="Validate Constraints",
                description=(
                    "Pre-flight constraint validation for a set of work_products. "
                    "Returns the list of violations + warnings without mutating the "
                    "graph — safe for reconciliation skills to call before emitting "
                    "a proposal."
                ),
                capability="constraint_validation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "work_product_ids": {
                            "type": "array",
                            "items": {"type": "string", "format": "uuid"},
                            "description": (
                                "UUIDs of work_products to evaluate constraints for. "
                                "Constraints are resolved transitively via "
                                "``CONSTRAINED_BY`` edges in the graph."
                            ),
                        },
                    },
                    "required": ["work_product_ids"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "passed": {"type": "boolean"},
                        "violations": {"type": "array"},
                        "warnings": {"type": "array"},
                        "evaluated_count": {"type": "integer"},
                        "skipped_count": {"type": "integer"},
                        "duration_ms": {"type": "number"},
                    },
                },
                phase=1,
                resource_limits=ResourceLimits(
                    max_memory_mb=512, max_cpu_seconds=30, max_disk_mb=64
                ),
            ),
            handler=self.validate,
        )

    async def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run ``ConstraintEngine.evaluate`` against the given work_product_ids."""
        raw_ids = arguments.get("work_product_ids")
        if not isinstance(raw_ids, list):
            raise ValueError("work_product_ids must be a list of UUID strings")

        try:
            work_product_ids = [UUID(str(x)) for x in raw_ids]
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"work_product_ids must be valid UUIDs: {exc}") from exc

        with tracer.start_as_current_span("constraint.validate") as span:
            span.set_attribute("constraint.work_product_count", len(work_product_ids))
            result = await self._engine.evaluate(work_product_ids)
            span.set_attribute("constraint.passed", result.passed)
            span.set_attribute("constraint.violation_count", len(result.violations))
            span.set_attribute("constraint.warning_count", len(result.warnings))

            logger.info(
                "constraint_validate",
                work_product_count=len(work_product_ids),
                passed=result.passed,
                violations=len(result.violations),
                warnings=len(result.warnings),
                duration_ms=result.duration_ms,
            )

            # Serialise via pydantic so UUIDs / datetimes / enums encode
            # cleanly to JSON. ``mode="json"`` is the safe wire format.
            return result.model_dump(mode="json")
