"""Tests for the electronics engineering domain agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from domain_agents.electronics.agent import ElectronicsAgent, TaskRequest, TaskResult
from skill_registry.mcp_bridge import InMemoryMcpBridge


@pytest.fixture
def mock_twin() -> AsyncMock:
    twin = AsyncMock()
    # Default: artifact exists
    twin.get_artifact.return_value = MagicMock(
        id=uuid4(), name="drone-fc-pcb", domain="electronics"
    )
    return twin


@pytest.fixture
def mcp_bridge() -> InMemoryMcpBridge:
    bridge = InMemoryMcpBridge()
    # Register tools that will be used once skills are implemented
    bridge.register_tool("kicad.run_erc", "erc_check")
    bridge.register_tool("kicad.run_drc", "drc_check")
    return bridge


@pytest.fixture
def agent(mock_twin: AsyncMock, mcp_bridge: InMemoryMcpBridge) -> ElectronicsAgent:
    return ElectronicsAgent(twin=mock_twin, mcp=mcp_bridge)


# --- ElectronicsAgent construction and metadata ---


class TestElectronicsAgent:
    """Basic agent construction and properties."""

    async def test_agent_creation(self, mock_twin: AsyncMock, mcp_bridge: InMemoryMcpBridge):
        agent = ElectronicsAgent(twin=mock_twin, mcp=mcp_bridge)
        assert agent.twin is mock_twin
        assert agent.mcp is mcp_bridge
        assert agent.session_id is not None

    async def test_agent_creation_with_session_id(
        self, mock_twin: AsyncMock, mcp_bridge: InMemoryMcpBridge
    ):
        sid = uuid4()
        agent = ElectronicsAgent(twin=mock_twin, mcp=mcp_bridge, session_id=sid)
        assert agent.session_id == sid

    async def test_supported_tasks(self):
        assert ElectronicsAgent.SUPPORTED_TASKS == {
            "run_erc",
            "run_drc",
            "check_power_budget",
            "full_validation",
        }

    async def test_unsupported_task_type_fails(self, agent: ElectronicsAgent):
        request = TaskRequest(
            task_type="do_magic",
            artifact_id=uuid4(),
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("Unsupported task type" in e for e in result.errors)
        assert "do_magic" in result.errors[0]

    async def test_missing_artifact(self, agent: ElectronicsAgent, mock_twin: AsyncMock):
        """Missing artifact should produce an error."""
        mock_twin.get_artifact.return_value = None
        request = TaskRequest(
            task_type="run_erc",
            artifact_id=uuid4(),
            parameters={"schematic_file": "eda/kicad/main.kicad_sch"},
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("not found" in e for e in result.errors)


# --- ERC checking ---


class TestRunErc:
    """Tests for the run_erc task type."""

    async def test_not_yet_implemented(self, agent: ElectronicsAgent):
        """ERC should return a not-yet-implemented stub error."""
        request = TaskRequest(
            task_type="run_erc",
            artifact_id=uuid4(),
            parameters={"schematic_file": "eda/kicad/main.kicad_sch"},
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("not yet implemented" in e for e in result.errors)
        assert result.task_type == "run_erc"
        assert len(result.skill_results) == 1
        assert result.skill_results[0]["skill"] == "run_erc"
        assert result.skill_results[0]["status"] == "not_implemented"

    async def test_missing_schematic_file(self, agent: ElectronicsAgent):
        """ERC should fail when schematic_file parameter is missing."""
        request = TaskRequest(
            task_type="run_erc",
            artifact_id=uuid4(),
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("schematic_file" in e for e in result.errors)


# --- DRC checking ---


class TestRunDrc:
    """Tests for the run_drc task type."""

    async def test_not_yet_implemented(self, agent: ElectronicsAgent):
        """DRC should return a not-yet-implemented stub error."""
        request = TaskRequest(
            task_type="run_drc",
            artifact_id=uuid4(),
            parameters={"pcb_file": "eda/kicad/main.kicad_pcb"},
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("not yet implemented" in e for e in result.errors)
        assert result.task_type == "run_drc"
        assert len(result.skill_results) == 1
        assert result.skill_results[0]["skill"] == "run_drc"
        assert result.skill_results[0]["status"] == "not_implemented"

    async def test_missing_pcb_file(self, agent: ElectronicsAgent):
        """DRC should fail when pcb_file parameter is missing."""
        request = TaskRequest(
            task_type="run_drc",
            artifact_id=uuid4(),
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("pcb_file" in e for e in result.errors)


# --- Power budget checking ---


class TestCheckPowerBudget:
    """Tests for the check_power_budget task type."""

    async def test_not_yet_implemented(self, agent: ElectronicsAgent):
        """Power budget check should return a not-yet-implemented stub error."""
        request = TaskRequest(
            task_type="check_power_budget",
            artifact_id=uuid4(),
            parameters={
                "components": [
                    {"name": "MCU", "power_mw": 150.0},
                    {"name": "IMU", "power_mw": 25.0},
                    {"name": "Radio", "power_mw": 200.0},
                ]
            },
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("not yet implemented" in e for e in result.errors)
        assert result.task_type == "check_power_budget"
        assert len(result.skill_results) == 1
        assert result.skill_results[0]["skill"] == "check_power_budget"
        assert result.skill_results[0]["status"] == "not_implemented"
        assert result.skill_results[0]["num_components"] == 3

    async def test_missing_components(self, agent: ElectronicsAgent):
        """Power budget check should fail when components parameter is missing."""
        request = TaskRequest(
            task_type="check_power_budget",
            artifact_id=uuid4(),
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("components" in e for e in result.errors)


# --- Full validation ---


class TestFullValidation:
    """Tests for the full_validation task type."""

    async def test_full_validation_runs_all_checks(self, agent: ElectronicsAgent):
        """Full validation should run ERC + DRC + power budget and aggregate results."""
        artifact_id = uuid4()
        request = TaskRequest(
            task_type="full_validation",
            artifact_id=artifact_id,
            parameters={
                "schematic_file": "eda/kicad/main.kicad_sch",
                "pcb_file": "eda/kicad/main.kicad_pcb",
                "components": [
                    {"name": "MCU", "power_mw": 150.0},
                    {"name": "IMU", "power_mw": 25.0},
                ],
            },
        )
        result = await agent.run_task(request)

        assert result.task_type == "full_validation"
        assert result.artifact_id == artifact_id
        # All stubs return not-implemented, so overall should fail
        assert result.success is False
        # Should have results from all three checks
        assert len(result.skill_results) == 3
        skills_run = {r["skill"] for r in result.skill_results}
        assert skills_run == {"run_erc", "run_drc", "check_power_budget"}

    async def test_full_validation_partial_parameters(self, agent: ElectronicsAgent):
        """Full validation should only run checks for which parameters are provided."""
        request = TaskRequest(
            task_type="full_validation",
            artifact_id=uuid4(),
            parameters={
                "schematic_file": "eda/kicad/main.kicad_sch",
                # No pcb_file or components
            },
        )
        result = await agent.run_task(request)

        assert result.task_type == "full_validation"
        # Only ERC ran
        assert len(result.skill_results) == 1
        assert result.skill_results[0]["skill"] == "run_erc"

    async def test_full_validation_no_parameters(self, agent: ElectronicsAgent):
        """Full validation with no parameters should error."""
        request = TaskRequest(
            task_type="full_validation",
            artifact_id=uuid4(),
        )
        result = await agent.run_task(request)

        assert result.success is False
        assert any("No validation checks could be run" in e for e in result.errors)


# --- TaskRequest model ---


class TestTaskRequest:
    """Tests for the TaskRequest Pydantic model."""

    def test_task_request_defaults(self):
        artifact_id = uuid4()
        req = TaskRequest(task_type="run_erc", artifact_id=artifact_id)
        assert req.branch == "main"
        assert req.parameters == {}

    def test_task_request_with_parameters(self):
        artifact_id = uuid4()
        params = {"schematic_file": "eda/kicad/main.kicad_sch"}
        req = TaskRequest(
            task_type="run_erc",
            artifact_id=artifact_id,
            parameters=params,
            branch="feature-1",
        )
        assert req.branch == "feature-1"
        assert req.parameters == params
        assert req.artifact_id == artifact_id


# --- TaskResult model ---


class TestTaskResult:
    """Tests for the TaskResult Pydantic model."""

    def test_task_result_defaults(self):
        artifact_id = uuid4()
        res = TaskResult(
            task_type="run_erc",
            artifact_id=artifact_id,
            success=True,
        )
        assert res.skill_results == []
        assert res.errors == []
        assert res.warnings == []

    def test_task_result_with_data(self):
        artifact_id = uuid4()
        res = TaskResult(
            task_type="run_erc",
            artifact_id=artifact_id,
            success=False,
            errors=["Something failed"],
            warnings=["Check schematic version"],
            skill_results=[{"skill": "run_erc", "data": {}}],
        )
        assert not res.success
        assert len(res.errors) == 1
        assert len(res.warnings) == 1
        assert len(res.skill_results) == 1
