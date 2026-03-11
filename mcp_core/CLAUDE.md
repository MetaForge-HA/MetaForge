# mcp_core

Model Context Protocol (MCP) client layer. Provides the wire protocol, JSON-RPC transport, and typed schemas that all tool communication flows through. Agents never call tools directly -- every invocation goes through MCP.

## Layer & Dependencies

- **Layer**: 1 (no upstream deps)
- **May import from**: standard library, `pydantic`
- **Do NOT import from**: `skill_registry`, `tool_registry`, `twin_core`, `orchestrator`, `domain_agents`, `api_gateway`, `digital_twin`, `observability`

## Key Files

- `client.py` -- `McpClient` and `Transport` abstraction (InMemoryTransport for testing)
- `protocol.py` -- Wire protocol implementation, error hierarchy (`McpError`, `ToolExecutionError`, `ToolTimeoutError`, `ToolUnavailableError`)
- `schemas.py` -- Pydantic models: `ToolCallRequest`, `ToolCallResult`, `ToolManifest`, JSON-RPC envelope types
- `transports.py` -- `LoopbackTransport` for in-process testing

## Testing

```bash
ruff check mcp_core/
mypy --strict mcp_core/
pytest tests/unit/test_mcp_core*.py -v
```

## Conventions

- All public types are re-exported from `__init__.py`
- Transport is an abstract base -- implement it for new backends (HTTP, stdio, etc.)
- Error types inherit from `McpError` -- never raise raw exceptions for tool failures
- Schemas use Pydantic v2 models exclusively
- This module has zero side effects on import -- no logging, no tracing, no network calls
