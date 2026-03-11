# skill_registry

Skill management layer. Skills are the atomic unit of domain expertise -- deterministic, schema-validated, independently testable. This module handles discovery, loading, validation, and MCP bridging for all skills.

## Layer & Dependencies

- **Layer**: 2
- **May import from**: `mcp_core`, `pydantic`, standard library
- **Do NOT import from**: `twin_core`, `orchestrator`, `domain_agents`, `api_gateway`, `digital_twin`, `tool_registry`

## Key Files

- `skill_base.py` -- `SkillBase` abstract class, `SkillContext`, `SkillResult`
- `registry.py` -- `SkillRegistry` catalog with auto-discovery and `SkillRegistration`
- `loader.py` -- `SkillLoader` for dynamic loading from `definition.json` files; `SkillLoadError`
- `schema_validator.py` -- `SchemaValidator`, `SkillDefinition`, `ToolRef` for input/output schema validation
- `mcp_bridge.py` -- `McpBridge` / `InMemoryMcpBridge` translating skill tool calls to MCP protocol
- `mcp_client_bridge.py` -- `McpClientBridge` using a real `McpClient` instance

## Testing

```bash
ruff check skill_registry/
mypy --strict skill_registry/
pytest tests/unit/test_skill*.py -v
```

## Conventions

- Every skill lives in its own directory with: `definition.json`, `SKILL.md`, `schema.py`, `handler.py`, `tests.py`
- Skills must be deterministic -- no randomness, no network calls in handlers
- All skill I/O is validated through Pydantic v2 schemas before and after execution
- Use `InMemoryMcpBridge` in tests -- never hit a real MCP server
- Public types are re-exported from `__init__.py`
