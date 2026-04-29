"""Unit tests for MCP-layer OTel instrumentation (MET-386).

Verifies that ``McpToolServer.handle_request`` and the inner
``handle_tool_call`` produce a parent + child span pair with the
expected ``mcp.*`` attributes for every successful and failed call.

Uses an in-memory span exporter so the assertions stay deterministic
without booting Tempo/Jaeger.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mcp_core.context import McpCallContext, with_context
from tool_registry.mcp_server.handlers import (
    ResourceLimits,
    ToolManifest,
)
from tool_registry.mcp_server.server import McpToolServer


@pytest.fixture
def span_exporter() -> AsyncIterator[InMemorySpanExporter]:
    """Attach an in-memory span exporter to the active TracerProvider.

    OTel forbids replacing the global TracerProvider after first use,
    so we add a SimpleSpanProcessor that funnels all spans into our
    exporter. If the active provider is the NoOp default (no spans
    will land), we install a fresh SDK TracerProvider — but only if no
    one beat us to it.
    """
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    if not hasattr(provider, "add_span_processor"):
        # NoOp provider — install a real one. This only succeeds the
        # first time across the whole test session.
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    try:
        yield exporter
    finally:
        # Best-effort cleanup; SimpleSpanProcessor is fire-and-forget
        # so we just clear the exporter for the next test.
        exporter.clear()


@pytest.fixture
def server() -> McpToolServer:
    """A minimal server with one success-tool and one fail-tool."""

    srv = McpToolServer(adapter_id="test", version="0.0.1")

    async def _success(arguments: dict[str, Any]) -> dict[str, Any]:
        return {"echo": arguments.get("payload", "")}

    async def _fail(arguments: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("intentional test failure")

    srv.register_tool(
        manifest=ToolManifest(
            tool_id="test.echo",
            adapter_id="test",
            name="Echo",
            description="returns its input",
            capability="test",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            phase=1,
            resource_limits=ResourceLimits(),
        ),
        handler=_success,
    )
    srv.register_tool(
        manifest=ToolManifest(
            tool_id="test.boom",
            adapter_id="test",
            name="Boom",
            description="always raises",
            capability="test",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            phase=1,
            resource_limits=ResourceLimits(),
        ),
        handler=_fail,
    )
    return srv


def _request(method: str, params: dict[str, Any], request_id: str = "1") -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})


class TestHappyPath:
    async def test_tool_call_produces_root_and_inner_spans(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(
            _request("tool/call", {"tool_id": "test.echo", "arguments": {"payload": "hi"}})
        )

        spans = {s.name: s for s in span_exporter.get_finished_spans()}
        assert "mcp.tool.call" in spans, list(spans)
        assert "mcp.tool.test.echo" in spans, list(spans)

        root = spans["mcp.tool.call"]
        inner = spans["mcp.tool.test.echo"]
        # Child relationship — inner span's parent_span_id == root's span_id.
        assert inner.parent.span_id == root.context.span_id

    async def test_root_span_attributes(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(
            _request("tool/call", {"tool_id": "test.echo", "arguments": {"payload": "hi"}})
        )

        root = next(s for s in span_exporter.get_finished_spans() if s.name == "mcp.tool.call")
        attrs = dict(root.attributes or {})
        assert attrs["mcp.method"] == "tool/call"
        assert attrs["mcp.adapter_id"] == "test"
        assert attrs["mcp.tool_id"] == "test.echo"
        assert attrs["mcp.status"] == "success"
        # Caller identity from MET-387 default sentinel.
        assert attrs["mcp.actor_id"] == "system:unattributed"

    async def test_inner_span_carries_tool_metadata(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(
            _request(
                "tool/call",
                {"tool_id": "test.echo", "arguments": {"payload": "hi", "extra": 1}},
            )
        )

        inner = next(
            s for s in span_exporter.get_finished_spans() if s.name == "mcp.tool.test.echo"
        )
        attrs = dict(inner.attributes or {})
        assert attrs["mcp.tool_id"] == "test.echo"
        assert attrs["mcp.tool.adapter_id"] == "test"
        assert attrs["mcp.tool.capability"] == "test"
        assert attrs["mcp.tool.argument_count"] == 2
        # Duration was recorded on success.
        assert "mcp.tool.duration_ms" in attrs


class TestContextPropagation:
    async def test_actor_and_project_id_appear_on_root_span(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        ctx = McpCallContext(
            project_id=UUID("11111111-1111-1111-1111-111111111111"),
            actor_id="agent:claude_code",
        )
        with with_context(ctx):
            await server.handle_request(
                _request("tool/call", {"tool_id": "test.echo", "arguments": {}})
            )

        root = next(s for s in span_exporter.get_finished_spans() if s.name == "mcp.tool.call")
        attrs = dict(root.attributes or {})
        assert attrs["mcp.actor_id"] == "agent:claude_code"
        assert attrs["mcp.project_id"] == "11111111-1111-1111-1111-111111111111"
        assert attrs["mcp.session_id"] == str(ctx.session_id)


class TestFailurePath:
    async def test_handler_failure_marks_status_and_records_exception(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(
            _request("tool/call", {"tool_id": "test.boom", "arguments": {}})
        )

        spans = {s.name: s for s in span_exporter.get_finished_spans()}
        root = spans["mcp.tool.call"]
        inner = spans["mcp.tool.test.boom"]

        # Root marks tool_execution_error + records the exception.
        attrs = dict(root.attributes or {})
        assert attrs["mcp.status"] == "tool_execution_error"
        assert attrs["mcp.error.tool_id"] == "test.boom"
        assert root.events, "expected an exception event on the root span"

        # Inner span recorded the underlying exception too.
        inner_attrs = dict(inner.attributes or {})
        assert "mcp.tool.duration_ms" in inner_attrs
        assert inner.events, "expected an exception event on the inner span"

    async def test_unknown_tool_marks_method_not_found(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(
            _request("tool/call", {"tool_id": "test.does_not_exist", "arguments": {}})
        )

        spans = {s.name: s for s in span_exporter.get_finished_spans()}
        root = spans["mcp.tool.call"]
        attrs = dict(root.attributes or {})
        assert attrs["mcp.status"] == "tool_not_found"
        assert attrs["mcp.error.tool_id"] == "test.does_not_exist"
        # No inner mcp.tool.<id> span — dispatch raised before handler.
        assert "mcp.tool.test.does_not_exist" not in spans


class TestNonToolMethods:
    async def test_tool_list_emits_root_span_only(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(_request("tool/list", {}))

        spans = {s.name: s for s in span_exporter.get_finished_spans()}
        assert "mcp.tool.call" in spans
        # tool/list doesn't dispatch to a handler — no inner span.
        inner_names = [n for n in spans if n.startswith("mcp.tool.") and n != "mcp.tool.call"]
        assert inner_names == [], inner_names

        attrs = dict(spans["mcp.tool.call"].attributes or {})
        assert attrs["mcp.method"] == "tool/list"
        assert attrs["mcp.status"] == "success"

    async def test_health_check_emits_root_span(
        self,
        server: McpToolServer,
        span_exporter: InMemorySpanExporter,
    ) -> None:
        await server.handle_request(_request("health/check", {}))
        spans = {s.name: s for s in span_exporter.get_finished_spans()}
        assert "mcp.tool.call" in spans
        attrs = dict(spans["mcp.tool.call"].attributes or {})
        assert attrs["mcp.method"] == "health/check"
        assert attrs["mcp.status"] == "success"
