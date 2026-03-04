"""Execution engine for tool calls with timeout, retry, and error handling."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from mcp_core.protocol import ToolExecutionError, ToolTimeoutError, ToolUnavailableError
from mcp_core.schemas import ToolCallRequest, ToolCallResult
from tool_registry.registry import ToolRegistry

logger = structlog.get_logger()


class ExecutionEngine:
    """Executes tool calls with timeout, retry, and error handling.

    Works with the ToolRegistry to find and invoke the right adapter.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        default_timeout: float = 120.0,
        max_retries: int = 1,
    ) -> None:
        self._registry = registry
        self._default_timeout = default_timeout
        self._max_retries = max_retries

    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> ToolCallResult:
        """Execute a tool call with timeout and retry logic.

        Looks up the adapter from the registry, sends the call via MCP client,
        and handles timeout and retry on failure.

        Args:
            tool_id: The tool identifier (e.g., 'calculix.run_fea').
            arguments: The tool call arguments.
            timeout: Optional timeout override in seconds.

        Returns:
            ToolCallResult on success.

        Raises:
            ToolUnavailableError: If the tool or its adapter is not found.
            ToolTimeoutError: If the call exceeds the timeout.
            ToolExecutionError: If the tool execution fails after all retries.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout

        # Look up the adapter for this tool
        adapter_id = self._registry.get_adapter_for_tool(tool_id)
        if adapter_id is None:
            raise ToolUnavailableError(tool_id)

        client = self._registry.get_client(adapter_id)
        if client is None:
            raise ToolUnavailableError(tool_id)

        request = ToolCallRequest(
            tool_id=tool_id,
            arguments=arguments,
            timeout_seconds=max(1, int(effective_timeout)),
        )

        last_error: Exception | None = None
        attempts = 1 + self._max_retries

        for attempt in range(attempts):
            try:
                result = await asyncio.wait_for(
                    client.call_tool(request),
                    timeout=effective_timeout,
                )
                logger.info(
                    "Tool call succeeded",
                    tool_id=tool_id,
                    attempt=attempt + 1,
                    duration_ms=result.duration_ms,
                )
                return result

            except TimeoutError:
                logger.warning(
                    "Tool call timed out",
                    tool_id=tool_id,
                    timeout=effective_timeout,
                    attempt=attempt + 1,
                )
                raise ToolTimeoutError(tool_id, int(effective_timeout))

            except ToolExecutionError as exc:
                last_error = exc
                if attempt < attempts - 1:
                    logger.warning(
                        "Tool call failed, retrying",
                        tool_id=tool_id,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                else:
                    logger.error(
                        "Tool call failed after all retries",
                        tool_id=tool_id,
                        attempts=attempts,
                        error=str(exc),
                    )

        # Should not reach here, but satisfy type checker
        assert last_error is not None  # noqa: S101
        raise last_error

    async def execute_batch(
        self,
        calls: list[ToolCallRequest],
    ) -> list[ToolCallResult]:
        """Execute multiple tool calls concurrently.

        Args:
            calls: List of tool call requests to execute in parallel.

        Returns:
            List of ToolCallResult in the same order as the input calls.
            Failed calls will raise their exceptions (not wrapped).
        """
        tasks = [
            self.execute(
                tool_id=call.tool_id,
                arguments=call.arguments,
                timeout=float(call.timeout_seconds),
            )
            for call in calls
        ]
        return list(await asyncio.gather(*tasks))
