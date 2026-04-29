"""MCP core -- Model Context Protocol client layer for MetaForge."""

from mcp_core.client import InMemoryTransport, McpClient, Transport
from mcp_core.context import (
    McpCallContext,
    context_from_env,
    context_from_headers,
    current_context,
    reset_context,
    set_context,
    with_context,
)
from mcp_core.protocol import (
    McpError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolUnavailableError,
)
from mcp_core.schemas import (
    HealthStatus,
    JsonRpcErrorResponse,
    JsonRpcRequest,
    JsonRpcSuccessResponse,
    ToolCallRequest,
    ToolCallResult,
    ToolManifest,
)
from mcp_core.transports import LoopbackTransport

__all__ = [
    "HealthStatus",
    "InMemoryTransport",
    "LoopbackTransport",
    "JsonRpcErrorResponse",
    "JsonRpcRequest",
    "JsonRpcSuccessResponse",
    "McpCallContext",
    "McpClient",
    "McpError",
    "ToolCallRequest",
    "ToolCallResult",
    "ToolExecutionError",
    "ToolManifest",
    "ToolTimeoutError",
    "ToolUnavailableError",
    "Transport",
    "context_from_env",
    "context_from_headers",
    "current_context",
    "reset_context",
    "set_context",
    "with_context",
]
