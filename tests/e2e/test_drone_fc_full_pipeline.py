"""E2E tests for the drone flight controller full multi-agent pipeline.

Validates that all 6 domain agents execute correctly, produce valid
results, and the gate engine evaluates readiness properly.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest

from digital_twin.thread.gate_engine.engine import GateEngine
from digital_twin.thread.gate_engine.models import GateStage, ReadinessScore
from domain_agents.compliance.agent import ComplianceAgent
from domain_agents.compliance.agent import TaskRequest as ComplianceTaskRequest
from domain_agents.electronics.agent import ElectronicsAgent
from domain_agents.electronics.agent import TaskRequest as EETaskRequest
from domain_agents.firmware.agent import FirmwareAgent
from domain_agents.firmware.agent import TaskRequest as FWTaskRequest
from domain_agents.mechanical.agent import MechanicalAgent
from domain_agents.mechanical.agent import TaskRequest as MechTaskRequest
from domain_agents.mechanical.agent import TaskResult as MechTaskResult
from domain_agents.simulation.agent import SimulationAgent
from domain_agents.simulation.agent import TaskRequest as SimTaskRequest
from domain_agents.supply_chain.agent import SupplyChainAgent
from domain_agents.supply_chain.agent import TaskRequest as SCTaskRequest
from skill_registry.mcp_bridge import InMemoryMcpBridge
from twin_core.api import InMemoryTwinAPI
from twin_core.models.artifact import Artifact
from twin_core.models.enums import ArtifactType

# ---------------------------------------------------------------------------
# Mock FEA results
# ---------------------------------------------------------------------------
MOCK_FEA_RESULT = {
    "max_von_mises": {
        "bracket_body": 85.3,
        "bracket_mount": 42.1,
        "fillet_region": 120.7,
    },
    "solver_time": 14.2,
    "mesh_elements": 52000,
    "node_count": 18500,
}

DRONE_BOM_PARTS = [
    {
        "mpn": "STM32F405RGT6",
        "manufacturer": "STMicroelectronics",
        "description": "ARM Cortex-M4 MCU",
        "quantity": 1,
        "unit_price_usd": 8.50,
        "lifecycle": "active",
        "lead_time_weeks": 12,
        "num_sources": 3,
    },
    {
        "mpn": "IST8310",
        "manufacturer": "Isentek",
        "description": "3-axis magnetometer",
        "quantity": 1,
        "unit_price_usd": 1.80,
        "lifecycle": "nrnd",
        "lead_time_weeks": 16,
        "num_sources": 1,
    },
    {
        "mpn": "TPS62160",
        "manufacturer": "Texas Instruments",
        "description": "3.3V step-down converter",
        "quantity": 2,
        "unit_price_usd": 1.50,
        "lifecycle": "active",
        "lead_time_weeks": 4,
        "num_sources": 3,
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def event_loop():
    """Create a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def twin() -> InMemoryTwinAPI:
    return InMemoryTwinAPI.create()


MOCK_ERC_RESULT = {
    "violations": [
        {
            "rule_id": "ERC_WARN_001",
            "severity": "warning",
            "message": "Unconnected pin on U3 pad 14",
            "sheet": "main",
            "component": "U3",
            "pin": "14",
        }
    ],
}

MOCK_SIM_FEA_RESULT = {
    "max_stress_mpa": 95.4,
    "max_displacement_mm": 0.12,
    "safety_factor": 2.89,
    "solver_time_s": 18.3,
}


@pytest.fixture()
def mcp() -> InMemoryMcpBridge:
    bridge = InMemoryMcpBridge()
    bridge.register_tool_response("calculix.run_fea", MOCK_FEA_RESULT)
    bridge.register_tool_response("kicad.run_erc", MOCK_ERC_RESULT)
    # Simulation agent's FEA handler also uses calculix.run_fea but expects
    # different keys; register a second response that satisfies the schema.
    # Since InMemoryMcpBridge uses a dict, the last registration wins.
    # We need to provide a response that works for BOTH the mechanical agent
    # (which reads max_von_mises) and the simulation agent (which reads
    # max_stress_mpa). Merge both sets of keys.
    merged_fea = {**MOCK_FEA_RESULT, **MOCK_SIM_FEA_RESULT}
    bridge.register_tool_response("calculix.run_fea", merged_fea)
    return bridge


@pytest.fixture()
async def artifacts(twin: InMemoryTwinAPI) -> dict[str, Artifact]:
    """Create all project artifacts in the twin."""
    cad = await twin.create_artifact(
        Artifact(
            name="motor-mount-bracket-v1",
            type=ArtifactType.CAD_MODEL,
            domain="mechanical",
            file_path="models/motor_mount_bracket.step",
            content_hash="sha256:a1b2c3",
            format="step",
            created_by="test",
            metadata={"material": "Al6061-T6", "yield_strength_mpa": 276.0},
        )
    )
    schematic = await twin.create_artifact(
        Artifact(
            name="drone-fc-schematic-v1",
            type=ArtifactType.SCHEMATIC,
            domain="electronics",
            file_path="eda/kicad/drone_fc.kicad_sch",
            content_hash="sha256:b2c3d4",
            format="kicad_sch",
            created_by="test",
        )
    )
    firmware = await twin.create_artifact(
        Artifact(
            name="drone-fc-firmware-v1",
            type=ArtifactType.FIRMWARE_SOURCE,
            domain="firmware",
            file_path="firmware/src/main.c",
            content_hash="sha256:c3d4e5",
            format="c",
            created_by="test",
        )
    )
    bom = await twin.create_artifact(
        Artifact(
            name="drone-fc-bom-v1",
            type=ArtifactType.BOM,
            domain="supply_chain",
            file_path="bom/drone_fc_bom.csv",
            content_hash="sha256:d4e5f6",
            format="csv",
            created_by="test",
        )
    )
    await twin.create_branch("main")
    await twin.commit("main", "Add test artifacts", "test")
    return {"cad": cad, "schematic": schematic, "firmware": firmware, "bom": bom}


# ---------------------------------------------------------------------------
# Tests: Individual agent execution
# ---------------------------------------------------------------------------

class TestMechanicalAgent:
    """Tests for MechanicalAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_stress_validation_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = MechanicalAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            MechTaskRequest(
                task_type="validate_stress",
                artifact_id=artifacts["cad"].id,
                parameters={
                    "mesh_file_path": "models/bracket.inp",
                    "load_case": "hover_3g",
                    "constraints": [{"max_von_mises_mpa": 276.0, "safety_factor": 1.5}],
                },
            )
        )
        assert isinstance(result, MechTaskResult)
        assert result.task_type == "validate_stress"
        assert len(result.skill_results) > 0

    @pytest.mark.asyncio
    async def test_stress_produces_fea_result(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = MechanicalAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            MechTaskRequest(
                task_type="validate_stress",
                artifact_id=artifacts["cad"].id,
                parameters={
                    "mesh_file_path": "models/bracket.inp",
                    "load_case": "hover_3g",
                    "constraints": [{"max_von_mises_mpa": 276.0, "safety_factor": 1.5}],
                },
            )
        )
        sr = result.skill_results[0]
        assert "fea_result" in sr
        assert "constraint_results" in sr
        assert sr["fea_result"]["mesh_elements"] == 52000


class TestElectronicsAgent:
    """Tests for ElectronicsAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_erc_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = ElectronicsAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            EETaskRequest(
                task_type="run_erc",
                artifact_id=artifacts["schematic"].id,
                parameters={"schematic_file": "eda/kicad/drone_fc.kicad_sch"},
            )
        )
        assert result.task_type == "run_erc"
        assert len(result.skill_results) > 0

    @pytest.mark.asyncio
    async def test_erc_produces_result(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = ElectronicsAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            EETaskRequest(
                task_type="run_erc",
                artifact_id=artifacts["schematic"].id,
                parameters={"schematic_file": "eda/kicad/drone_fc.kicad_sch"},
            )
        )
        sr = result.skill_results[0]
        assert sr["skill"] == "run_erc"
        assert "total_violations" in sr
        assert "passed" in sr


class TestFirmwareAgent:
    """Tests for FirmwareAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_hal_generation_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = FirmwareAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            FWTaskRequest(
                task_type="generate_hal",
                artifact_id=artifacts["firmware"].id,
                parameters={
                    "mcu_family": "STM32F4",
                    "peripherals": ["GPIO", "SPI", "I2C"],
                },
            )
        )
        assert result.task_type == "generate_hal"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_hal_produces_files(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = FirmwareAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            FWTaskRequest(
                task_type="generate_hal",
                artifact_id=artifacts["firmware"].id,
                parameters={
                    "mcu_family": "STM32F4",
                    "peripherals": ["GPIO", "SPI"],
                },
            )
        )
        sr = result.skill_results[0]
        assert sr["skill"] == "generate_hal"
        assert "generated_files" in sr
        assert len(sr["generated_files"]) > 0


class TestSimulationAgent:
    """Tests for SimulationAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_fea_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = SimulationAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            SimTaskRequest(
                task_type="run_fea",
                artifact_id=artifacts["cad"].id,
                parameters={
                    "mesh_file": "models/bracket.inp",
                    "analysis_type": "static",
                    "material": "aluminum_6061",
                },
            )
        )
        assert result.task_type == "run_fea"
        assert len(result.skill_results) > 0
        sr = result.skill_results[0]
        assert "max_stress_mpa" in sr
        assert "safety_factor" in sr


class TestSupplyChainAgent:
    """Tests for SupplyChainAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_bom_risk_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = SupplyChainAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            SCTaskRequest(
                task_type="score_bom_risk",
                artifact_id=artifacts["bom"].id,
                parameters={"parts": DRONE_BOM_PARTS},
            )
        )
        assert result.task_type == "score_bom_risk"
        assert result.success is True
        assert len(result.skill_results) > 0

    @pytest.mark.asyncio
    async def test_bom_risk_produces_report(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = SupplyChainAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            SCTaskRequest(
                task_type="score_bom_risk",
                artifact_id=artifacts["bom"].id,
                parameters={"parts": DRONE_BOM_PARTS, "risk_threshold": 0.6},
            )
        )
        sr = result.skill_results[0]
        assert sr["skill"] == "score_bom_risk"
        assert "overall_risk_score" in sr
        assert sr["total_parts"] == len(DRONE_BOM_PARTS)
        assert "part_risks" in sr
        assert "total_bom_cost_usd" in sr


class TestComplianceAgent:
    """Tests for ComplianceAgent in the pipeline."""

    @pytest.mark.asyncio
    async def test_checklist_executes(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = ComplianceAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            ComplianceTaskRequest(
                task_type="generate_checklist",
                artifact_id=artifacts["bom"].id,
                parameters={"markets": ["CE", "FCC", "UKCA"]},
            )
        )
        assert result.task_type == "generate_checklist"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_checklist_produces_items(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        agent = ComplianceAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            ComplianceTaskRequest(
                task_type="generate_checklist",
                artifact_id=artifacts["bom"].id,
                parameters={"markets": ["CE", "FCC", "UKCA"]},
            )
        )
        sr = result.skill_results[0]
        assert sr["skill"] == "generate_checklist"
        assert sr["total_items"] > 0
        assert set(sr["markets_covered"]) == {"CE", "FCC", "UKCA"}
        assert "checklists" in sr


# ---------------------------------------------------------------------------
# Tests: Gate engine evaluation
# ---------------------------------------------------------------------------

class TestGateEngine:
    """Tests for EVT gate readiness evaluation."""

    def test_evaluate_readiness_all_pass(self) -> None:
        gate = GateEngine()
        agent_results = {
            "mechanical_stress": {"success": True},
            "electronics_erc": {"success": True},
            "firmware_hal": {"success": True},
            "simulation_fea": {"success": True},
            "supply_chain_bom": {"success": True},
            "compliance_checklist": {"success": True},
        }
        readiness = gate.evaluate_readiness(GateStage.EVT, agent_results)
        assert isinstance(readiness, ReadinessScore)
        assert readiness.score == 1.0
        assert readiness.passed is True
        assert len(readiness.blockers) == 0

    def test_evaluate_readiness_partial_fail(self) -> None:
        gate = GateEngine()
        agent_results = {
            "mechanical_stress": {"success": True},
            "electronics_erc": {"success": False, "error": "3 ERC violations"},
            "firmware_hal": {"success": True},
            "simulation_fea": {"success": True},
            "supply_chain_bom": {"success": True},
            "compliance_checklist": {"success": True},
        }
        readiness = gate.evaluate_readiness(GateStage.EVT, agent_results)
        assert readiness.score < 1.0
        assert len(readiness.blockers) > 0
        assert any("electronics_erc" in b for b in readiness.blockers)

    def test_evaluate_readiness_missing_check(self) -> None:
        gate = GateEngine()
        # Only provide some results -- missing ones should be blockers
        agent_results = {
            "mechanical_stress": {"success": True},
            "electronics_erc": {"success": True},
        }
        readiness = gate.evaluate_readiness(GateStage.EVT, agent_results)
        assert readiness.passed is False
        assert len(readiness.blockers) >= 4  # 4 missing checks


# ---------------------------------------------------------------------------
# Tests: Pipeline resilience
# ---------------------------------------------------------------------------

class TestPipelineResilience:
    """Tests for pipeline behaviour when agents fail."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_after_agent_failure(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        """One agent failing should not prevent others from running."""
        results: dict[str, Any] = {}

        # Mechanical -- will fail due to MCP tool not responding for wrong tool
        mech_agent = MechanicalAgent(twin=twin, mcp=mcp)
        mech_result = await mech_agent.run_task(
            MechTaskRequest(
                task_type="validate_stress",
                artifact_id=artifacts["cad"].id,
                parameters={
                    "mesh_file_path": "models/bracket.inp",
                    "load_case": "hover_3g",
                    "constraints": [{"max_von_mises_mpa": 276.0, "safety_factor": 1.5}],
                },
            )
        )
        results["mechanical"] = mech_result

        # Supply chain -- should succeed regardless
        sc_agent = SupplyChainAgent(twin=twin, mcp=mcp)
        sc_result = await sc_agent.run_task(
            SCTaskRequest(
                task_type="score_bom_risk",
                artifact_id=artifacts["bom"].id,
                parameters={"parts": DRONE_BOM_PARTS},
            )
        )
        results["supply_chain"] = sc_result

        # Compliance -- should succeed regardless
        comp_agent = ComplianceAgent(twin=twin, mcp=mcp)
        comp_result = await comp_agent.run_task(
            ComplianceTaskRequest(
                task_type="generate_checklist",
                artifact_id=artifacts["bom"].id,
                parameters={"markets": ["CE"]},
            )
        )
        results["compliance"] = comp_result

        # Even if mech failed, SC and compliance should be fine
        assert sc_result.success is True
        assert comp_result.success is True

    @pytest.mark.asyncio
    async def test_unsupported_task_returns_error(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        """Agents should return a clear error for unsupported task types."""
        agent = SupplyChainAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            SCTaskRequest(
                task_type="nonexistent_task",
                artifact_id=artifacts["bom"].id,
            )
        )
        assert result.success is False
        assert len(result.errors) > 0
        assert "Unsupported" in result.errors[0]


# ---------------------------------------------------------------------------
# Tests: Twin state updates
# ---------------------------------------------------------------------------

class TestTwinState:
    """Tests for Digital Twin state after agent execution."""

    @pytest.mark.asyncio
    async def test_artifacts_exist_after_creation(
        self, twin: InMemoryTwinAPI, artifacts: dict[str, Artifact]
    ) -> None:
        """All artifacts should be retrievable from the twin."""
        for name, artifact in artifacts.items():
            retrieved = await twin.get_artifact(artifact.id)
            assert retrieved is not None, f"Artifact '{name}' not found in twin"
            assert retrieved.name == artifact.name

    @pytest.mark.asyncio
    async def test_twin_update_after_agent_run(
        self, twin: InMemoryTwinAPI, mcp: InMemoryMcpBridge, artifacts: dict[str, Artifact]
    ) -> None:
        """Agent results can be written back to the twin."""
        agent = SupplyChainAgent(twin=twin, mcp=mcp)
        result = await agent.run_task(
            SCTaskRequest(
                task_type="score_bom_risk",
                artifact_id=artifacts["bom"].id,
                parameters={"parts": DRONE_BOM_PARTS},
            )
        )
        assert result.success is True

        # Update the twin with results
        await twin.update_artifact(
            artifacts["bom"].id,
            {"metadata": {"bom_risk_score": result.skill_results[0]["overall_risk_score"]}},
        )
        updated = await twin.get_artifact(artifacts["bom"].id)
        assert updated is not None
        assert "bom_risk_score" in updated.metadata
