"""Metadata models for tool adapters and their capabilities."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from tool_registry.mcp_server.handlers import ToolManifest


class AdapterStatus(StrEnum):
    """Status of a tool adapter."""

    REGISTERED = "registered"  # Known but not connected
    CONNECTED = "connected"  # Connected and responsive
    DEGRADED = "degraded"  # Some tools failing
    DISCONNECTED = "disconnected"  # Not reachable
    ERROR = "error"  # Fatal error


class AdapterInfo(BaseModel):
    """Metadata about a registered tool adapter."""

    adapter_id: str
    version: str
    status: AdapterStatus = AdapterStatus.REGISTERED
    tools: list[ToolManifest] = Field(default_factory=list)
    last_health_check: datetime | None = None
    health_check_interval_seconds: int = 60
    error_message: str | None = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolCapability(BaseModel):
    """Describes a capability that one or more tools provide."""

    capability: str
    tool_ids: list[str] = Field(default_factory=list)
    description: str = ""
