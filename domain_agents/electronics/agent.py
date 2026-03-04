"""Electronics engineering domain agent.

Orchestrates skill execution for electronics design validation:
ERC checking, DRC checking, and power budget analysis.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel

from skill_registry.mcp_bridge import McpBridge
from skill_registry.skill_base import SkillContext

logger = structlog.get_logger()


class TaskRequest(BaseModel):
    """A request for the electronics agent to perform a task."""

    task_type: str  # "run_erc", "run_drc", "check_power_budget", "full_validation"
    artifact_id: UUID
    parameters: dict[str, Any] = {}
    branch: str = "main"


class TaskResult(BaseModel):
    """Result of an electronics agent task."""

    task_type: str
    artifact_id: UUID
    success: bool
    skill_results: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    model_config = {"arbitrary_types_allowed": True}


class ElectronicsAgent:
    """Electronics engineering domain agent.

    Orchestrates skill execution for electronics design validation:
    ERC checking, DRC checking, power budget analysis.

    The agent is stateless -- all state lives in the Digital Twin.

    Usage:
        twin = InMemoryTwinAPI.create()
        mcp = InMemoryMcpBridge()
        agent = ElectronicsAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(TaskRequest(
            task_type="run_erc",
            artifact_id=artifact.id,
            parameters={"schematic_file": "eda/kicad/main.kicad_sch"},
        ))
    """

    SUPPORTED_TASKS = {"run_erc", "run_drc", "check_power_budget", "full_validation"}

    def __init__(
        self,
        twin: Any,  # TwinAPI -- avoid circular import at module level
        mcp: McpBridge,
        session_id: UUID | None = None,
    ) -> None:
        self.twin = twin
        self.mcp = mcp
        self.session_id = session_id or uuid4()
        self.logger = logger.bind(agent="electronics", session_id=str(self.session_id))

    async def run_task(self, request: TaskRequest) -> TaskResult:
        """Execute an electronics engineering task.

        Routes to the appropriate handler based on task_type.
        """
        self.logger.info(
            "Running task",
            task_type=request.task_type,
            artifact_id=str(request.artifact_id),
        )

        if request.task_type not in self.SUPPORTED_TASKS:
            return TaskResult(
                task_type=request.task_type,
                artifact_id=request.artifact_id,
                success=False,
                errors=[
                    f"Unsupported task type: {request.task_type}. "
                    f"Supported: {', '.join(sorted(self.SUPPORTED_TASKS))}"
                ],
            )

        # Verify artifact exists
        artifact = await self.twin.get_artifact(request.artifact_id, branch=request.branch)
        if artifact is None:
            return TaskResult(
                task_type=request.task_type,
                artifact_id=request.artifact_id,
                success=False,
                errors=[
                    f"Artifact {request.artifact_id} not found on branch '{request.branch}'"
                ],
            )

        # Route to handler
        handler = self._get_handler(request.task_type)
        return await handler(request)

    def _get_handler(
        self, task_type: str
    ) -> Callable[[TaskRequest], Coroutine[Any, Any, TaskResult]]:
        """Return the handler coroutine function for the given task type."""
        handlers: dict[str, Callable[[TaskRequest], Coroutine[Any, Any, TaskResult]]] = {
            "run_erc": self._run_erc,
            "run_drc": self._run_drc,
            "check_power_budget": self._run_check_power_budget,
            "full_validation": self._run_full_validation,
        }
        return handlers[task_type]

    async def _run_erc(self, request: TaskRequest) -> TaskResult:
        """Run Electrical Rules Check on a schematic file.

        Requires 'schematic_file' in request.parameters.
        Currently returns a stub error since the ERC skill is not yet implemented.
        """
        schematic_file: str = request.parameters.get("schematic_file", "")
        if not schematic_file:
            return TaskResult(
                task_type=request.task_type,
                artifact_id=request.artifact_id,
                success=False,
                errors=["Missing required parameter: schematic_file"],
            )

        self.logger.info("ERC requested", schematic_file=schematic_file)

        return TaskResult(
            task_type=request.task_type,
            artifact_id=request.artifact_id,
            success=False,
            errors=["run_erc skill is not yet implemented"],
            skill_results=[
                {
                    "skill": "run_erc",
                    "status": "not_implemented",
                    "schematic_file": schematic_file,
                }
            ],
        )

    async def _run_drc(self, request: TaskRequest) -> TaskResult:
        """Run Design Rules Check on a PCB layout file.

        Requires 'pcb_file' in request.parameters.
        Currently returns a stub error since the DRC skill is not yet implemented.
        """
        pcb_file: str = request.parameters.get("pcb_file", "")
        if not pcb_file:
            return TaskResult(
                task_type=request.task_type,
                artifact_id=request.artifact_id,
                success=False,
                errors=["Missing required parameter: pcb_file"],
            )

        self.logger.info("DRC requested", pcb_file=pcb_file)

        return TaskResult(
            task_type=request.task_type,
            artifact_id=request.artifact_id,
            success=False,
            errors=["run_drc skill is not yet implemented"],
            skill_results=[
                {
                    "skill": "run_drc",
                    "status": "not_implemented",
                    "pcb_file": pcb_file,
                }
            ],
        )

    async def _run_check_power_budget(self, request: TaskRequest) -> TaskResult:
        """Check power budget against component power ratings.

        Requires 'components' in request.parameters (list of components with
        power ratings).
        Currently returns a stub error since the skill is not yet implemented.
        """
        components: list[dict[str, Any]] = request.parameters.get("components", [])
        if not components:
            return TaskResult(
                task_type=request.task_type,
                artifact_id=request.artifact_id,
                success=False,
                errors=["Missing required parameter: components"],
            )

        self.logger.info("Power budget check requested", num_components=len(components))

        return TaskResult(
            task_type=request.task_type,
            artifact_id=request.artifact_id,
            success=False,
            errors=["check_power_budget skill is not yet implemented"],
            skill_results=[
                {
                    "skill": "check_power_budget",
                    "status": "not_implemented",
                    "num_components": len(components),
                }
            ],
        )

    async def _run_full_validation(self, request: TaskRequest) -> TaskResult:
        """Run full electronics validation (ERC + DRC + power budget).

        Runs all three checks sequentially and aggregates results.
        Returns success only if all checks pass.
        Skips individual checks if their required parameters are not provided.
        """
        all_results: list[dict[str, Any]] = []
        all_errors: list[str] = []
        all_warnings: list[str] = []
        overall_success = True
        checks_run = 0

        # Run ERC if schematic_file is provided
        if request.parameters.get("schematic_file"):
            erc_result = await self._run_erc(request)
            all_results.extend(erc_result.skill_results)
            all_errors.extend(erc_result.errors)
            all_warnings.extend(erc_result.warnings)
            if not erc_result.success:
                overall_success = False
            checks_run += 1

        # Run DRC if pcb_file is provided
        if request.parameters.get("pcb_file"):
            drc_result = await self._run_drc(request)
            all_results.extend(drc_result.skill_results)
            all_errors.extend(drc_result.errors)
            all_warnings.extend(drc_result.warnings)
            if not drc_result.success:
                overall_success = False
            checks_run += 1

        # Run power budget check if components are provided
        if request.parameters.get("components"):
            power_result = await self._run_check_power_budget(request)
            all_results.extend(power_result.skill_results)
            all_errors.extend(power_result.errors)
            all_warnings.extend(power_result.warnings)
            if not power_result.success:
                overall_success = False
            checks_run += 1

        # If no checks were run, report an error
        if checks_run == 0:
            return TaskResult(
                task_type="full_validation",
                artifact_id=request.artifact_id,
                success=False,
                errors=[
                    "No validation checks could be run. "
                    "Provide at least one of: schematic_file, pcb_file, components"
                ],
            )

        return TaskResult(
            task_type="full_validation",
            artifact_id=request.artifact_id,
            success=overall_success,
            skill_results=all_results,
            errors=all_errors,
            warnings=all_warnings,
        )

    def _create_skill_context(self, branch: str = "main") -> SkillContext:
        """Create a SkillContext for skill execution."""
        return SkillContext(
            twin=self.twin,
            mcp=self.mcp,
            logger=self.logger,
            session_id=self.session_id,
            branch=branch,
        )
