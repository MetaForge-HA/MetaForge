"""Pydantic schemas for MCP protocol messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Tool-level schemas ---


class ResourceLimits(BaseModel):
    """Resource limits for a tool adapter container."""

    max_memory_mb: int = 1024
    max_cpu_seconds: int = 300
    max_disk_mb: int = 256


class ToolManifest(BaseModel):
    """Manifest describing a single tool's capabilities."""

    tool_id: str
    adapter_id: str
    name: str
    description: str
    capability: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    phase: int = 1
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)


# --- Requests ---


class ToolListRequest(BaseModel):
    """Parameters for tool/list method."""

    capability: str | None = None


class ToolCallRequest(BaseModel):
    """Parameters for tool/call method."""

    tool_id: str = Field(..., description="Tool identifier (e.g., 'calculix.run_fea')")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID")


class HealthCheckRequest(BaseModel):
    """Parameters for health/check method."""


# --- Responses ---


class ToolListResult(BaseModel):
    """Result of tool/list method."""

    tools: list[ToolManifest]


class ToolCallResult(BaseModel):
    """Result of a successful tool/call."""

    tool_id: str
    status: str  # "success" or "error"
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0
    output_files: list[str] = Field(default_factory=list)


class ToolProgress(BaseModel):
    """Progress notification for long-running tool calls."""

    request_id: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str = ""


class HealthStatus(BaseModel):
    """Health status of a tool adapter."""

    adapter_id: str
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    tools_available: int
    uptime_seconds: float
    last_invocation: datetime | None = None


# --- Errors ---


class McpErrorData(BaseModel):
    """Structured error data for MCP errors."""

    error_type: str
    tool_id: str
    details: str
    duration_ms: float = 0


# --- JSON-RPC 2.0 envelope ---


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""

    jsonrpc: str = "2.0"
    id: str
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcSuccessResponse(BaseModel):
    """JSON-RPC 2.0 success response."""

    jsonrpc: str = "2.0"
    id: str
    result: dict[str, Any]


class JsonRpcErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response."""

    jsonrpc: str = "2.0"
    id: str
    error: dict[str, Any]


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id)."""

    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
