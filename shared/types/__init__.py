"""Shared domain types facade — re-exports foundational types from their source modules.

This package provides a single import point for all core domain models used
across the MetaForge platform. Types are defined in their owning modules
(twin_core, orchestrator, etc.) and re-exported here for convenience.

Usage::

    from shared.types import Artifact, Constraint, Event, GateStage

All re-exported types are identical objects to their source definitions
(i.e., ``shared.types.Artifact is twin_core.models.Artifact``).
"""

import structlog

from digital_twin.thread.gate_engine.models import (
    CriterionResult,
    GateApprovalResult,
    GateCriterion,
    GateCriterionType,
    GateDefinition,
    GateStage,
    GateTransition,
    GateTransitionRequest,
    GateTransitionStatus,
    ReadinessScore,
)
from mcp_core.schemas import (
    HealthStatus,
    McpErrorData,
    ResourceLimits,
    ToolCallRequest,
    ToolCallResult,
    ToolListRequest,
    ToolListResult,
    ToolManifest,
    ToolProgress,
)
from observability.tracing import get_tracer
from orchestrator.event_bus.events import (
    ChatMessageEvent,
    ChatThreadEvent,
    ChatTypingEvent,
    Event,
    EventType,
)
from shared.types.common import (
    ArtifactId,
    ComponentId,
    ConstraintId,
    NodeId,
    SessionId,
    Timestamp,
    VersionId,
)
from skill_registry.schema_validator import (
    SkillDefinition,
    ToolRef,
)
from twin_core.models import (
    AgentNode,
    Artifact,
    ArtifactChange,
    BOMItem,
    Component,
    ConstrainedByEdge,
    Constraint,
    DependsOnEdge,
    DesignElement,
    DeviceInstance,
    EdgeBase,
    NodeBase,
    SubGraph,
    TwinModel,
    UsesComponentEdge,
    Version,
    VersionDiff,
)
from twin_core.models.enums import (
    ArtifactType,
    ComponentLifecycle,
    ConstraintSeverity,
    ConstraintStatus,
    EdgeType,
    NodeType,
)

# --- Structured logging and tracing ---
logger = structlog.get_logger(__name__)
tracer = get_tracer("shared.types")

logger.debug("shared.types facade loaded")

__all__ = [
    # Twin Core — enums
    "ArtifactType",
    "ComponentLifecycle",
    "ConstraintSeverity",
    "ConstraintStatus",
    "EdgeType",
    "NodeType",
    # Twin Core — base
    "EdgeBase",
    "NodeBase",
    # Twin Core — nodes
    "AgentNode",
    "Artifact",
    "BOMItem",
    "Component",
    "Constraint",
    "DesignElement",
    "DeviceInstance",
    "TwinModel",
    "Version",
    # Twin Core — edges
    "ConstrainedByEdge",
    "DependsOnEdge",
    "UsesComponentEdge",
    # Twin Core — responses
    "ArtifactChange",
    "SubGraph",
    "VersionDiff",
    # Event bus
    "ChatMessageEvent",
    "ChatThreadEvent",
    "ChatTypingEvent",
    "Event",
    "EventType",
    # Gate engine
    "CriterionResult",
    "GateApprovalResult",
    "GateCriterion",
    "GateCriterionType",
    "GateDefinition",
    "GateStage",
    "GateTransition",
    "GateTransitionRequest",
    "GateTransitionStatus",
    "ReadinessScore",
    # MCP schemas
    "HealthStatus",
    "McpErrorData",
    "ResourceLimits",
    "ToolCallRequest",
    "ToolCallResult",
    "ToolListRequest",
    "ToolListResult",
    "ToolManifest",
    "ToolProgress",
    # Skill registry
    "SkillDefinition",
    "ToolRef",
    # Common aliases
    "ArtifactId",
    "ComponentId",
    "ConstraintId",
    "NodeId",
    "SessionId",
    "Timestamp",
    "VersionId",
]
