"""Unit tests for the constraint MCP tool adapter (MET-383)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tool_registry.tools.constraint.adapter import ConstraintServer
from twin_core.constraint_engine.models import (
    ConstraintEvaluationResult,
    ConstraintViolation,
)
from twin_core.models.enums import ConstraintSeverity


class _FakeEngine:
    """Records evaluate() calls so the test can assert exact delegation."""

    def __init__(self, result: ConstraintEvaluationResult) -> None:
        self._result = result
        self.calls: list[list[UUID]] = []

    async def evaluate(self, work_product_ids: list[UUID]) -> ConstraintEvaluationResult:
        self.calls.append(list(work_product_ids))
        return self._result

    # Unused by the adapter but required by the ConstraintEngine ABC.
    async def evaluate_all(self) -> ConstraintEvaluationResult:  # pragma: no cover
        return self._result

    async def add_constraint(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def get_constraint(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def remove_constraint(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError


def _request(payload: dict[str, object]) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tool/call",
            "params": {"tool_id": "constraint.validate", "arguments": payload},
        }
    )


class TestConstraintServer:
    def test_registers_single_tool(self) -> None:
        result = ConstraintEvaluationResult(passed=True, evaluated_count=0)
        srv = ConstraintServer(engine=_FakeEngine(result))
        assert srv.adapter_id == "constraint"
        assert srv.tool_ids == ["constraint.validate"]

    async def test_validate_delegates_to_engine(self) -> None:
        constraint_id = uuid4()
        wp_a = uuid4()
        wp_b = uuid4()
        violation = ConstraintViolation(
            constraint_id=constraint_id,
            constraint_name="material_must_match",
            severity=ConstraintSeverity.ERROR,
            message="Bracket and bolt must share a material family",
            work_product_ids=[wp_a, wp_b],
            expression="bracket.material == bolt.material",
            evaluated_at=datetime.now(UTC),
        )
        engine = _FakeEngine(
            ConstraintEvaluationResult(
                passed=False,
                violations=[violation],
                warnings=[],
                evaluated_count=1,
                duration_ms=12.5,
            )
        )
        srv = ConstraintServer(engine=engine)

        wp_ids = [wp_a, wp_b]
        raw = await srv.handle_request(_request({"work_product_ids": [str(wp) for wp in wp_ids]}))
        body = json.loads(raw)

        # Engine got the right input.
        assert engine.calls == [wp_ids]

        # Wire format is the standard tool envelope.
        assert body["id"] == "1"
        assert "result" in body, body
        result = body["result"]
        assert result["tool_id"] == "constraint.validate"
        assert result["status"] == "success"

        data = result["data"]
        assert data["passed"] is False
        assert data["evaluated_count"] == 1
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["constraint_name"] == "material_must_match"
        assert v["severity"] == "error"
        # UUIDs serialise as strings via mode="json".
        assert v["constraint_id"] == str(constraint_id)
        assert sorted(v["work_product_ids"]) == sorted([str(wp_a), str(wp_b)])

    async def test_passing_result(self) -> None:
        engine = _FakeEngine(
            ConstraintEvaluationResult(
                passed=True,
                violations=[],
                warnings=[],
                evaluated_count=3,
                duration_ms=4.2,
            )
        )
        srv = ConstraintServer(engine=engine)

        raw = await srv.handle_request(_request({"work_product_ids": [str(uuid4())]}))
        body = json.loads(raw)
        data = body["result"]["data"]
        assert data["passed"] is True
        assert data["violations"] == []
        assert data["evaluated_count"] == 3

    async def test_warnings_surface_separately(self) -> None:
        warn_id = uuid4()
        engine = _FakeEngine(
            ConstraintEvaluationResult(
                passed=True,  # warnings don't fail the gate
                violations=[],
                warnings=[
                    ConstraintViolation(
                        constraint_id=warn_id,
                        constraint_name="prefer_imperial_units",
                        severity=ConstraintSeverity.WARNING,
                        message="Project uses metric — bracket spec is imperial",
                        work_product_ids=[],
                        expression="True",
                        evaluated_at=datetime.now(UTC),
                    )
                ],
                evaluated_count=1,
            )
        )
        srv = ConstraintServer(engine=engine)

        raw = await srv.handle_request(_request({"work_product_ids": [str(uuid4())]}))
        data = json.loads(raw)["result"]["data"]
        assert data["passed"] is True
        assert data["violations"] == []
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["severity"] == "warning"

    @pytest.mark.parametrize(
        "bad_payload",
        [
            {},  # missing field
            {"work_product_ids": "not-a-list"},
            {"work_product_ids": ["not-a-uuid"]},
        ],
    )
    async def test_invalid_input_surfaces_as_tool_error(self, bad_payload: dict) -> None:
        result = ConstraintEvaluationResult(passed=True, evaluated_count=0)
        srv = ConstraintServer(engine=_FakeEngine(result))

        raw = await srv.handle_request(_request(bad_payload))
        body = json.loads(raw)
        # The MCP server wraps any handler ``raise`` in a JSON-RPC
        # error with code -32001.
        assert "error" in body, body
        assert body["error"]["code"] == -32001
