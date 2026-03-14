"""Unit tests for CalculiX solver and result parser (MET-222).

No real CalculiX binary required -- subprocess calls are mocked.
"""

from __future__ import annotations

import pytest

from tool_registry.tools.calculix.result_parser import (
    FrdParseError,
    _build_stats,
    _compute_von_mises,
    _parse_node_data_line,
)
from tool_registry.tools.calculix.solver import (
    MAX_SOLVER_TIMEOUT,
    SolverError,
    SolverTimeoutError,
)

# ---------------------------------------------------------------------------
# 1. Von Mises computation
# ---------------------------------------------------------------------------


class TestVonMises:
    """Von Mises equivalent stress computation."""

    def test_uniaxial_tension(self) -> None:
        # Pure uniaxial stress: vm = |sxx|
        vm = _compute_von_mises(100.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(vm - 100.0) < 0.01

    def test_pure_shear(self) -> None:
        # Pure shear: vm = sqrt(3) * |sxy|
        import math

        vm = _compute_von_mises(0.0, 0.0, 0.0, 100.0, 0.0, 0.0)
        assert abs(vm - math.sqrt(3) * 100.0) < 0.01

    def test_hydrostatic_zero(self) -> None:
        # Hydrostatic (equal all normals): vm = 0
        vm = _compute_von_mises(100.0, 100.0, 100.0, 0.0, 0.0, 0.0)
        assert abs(vm) < 0.001

    def test_biaxial(self) -> None:
        vm = _compute_von_mises(100.0, 50.0, 0.0, 0.0, 0.0, 0.0)
        assert vm > 0

    def test_all_components(self) -> None:
        vm = _compute_von_mises(10.0, 20.0, 30.0, 5.0, 3.0, 2.0)
        assert vm > 0


# ---------------------------------------------------------------------------
# 2. FRD line parsing
# ---------------------------------------------------------------------------


class TestParseNodeDataLine:
    """Parse fixed-width -1 data lines from .frd format."""

    def test_valid_line(self) -> None:
        # Simulate a -1 line: " -1" + 10-char node ID + 12-char values
        line = " -1" + "         1" + "  100.000000" + "   50.000000" + "   25.000000"
        result = _parse_node_data_line(line)
        assert result is not None
        assert result[0] == 1.0  # node_id
        assert abs(result[1] - 100.0) < 0.01
        assert abs(result[2] - 50.0) < 0.01

    def test_invalid_line_returns_none(self) -> None:
        result = _parse_node_data_line(" -1  not_a_number  blah")
        assert result is None

    def test_empty_data_returns_none(self) -> None:
        result = _parse_node_data_line(" -1          ")
        # Whitespace-only data after prefix fails to parse
        assert result is None


# ---------------------------------------------------------------------------
# 3. Build stats helper
# ---------------------------------------------------------------------------


class TestBuildStats:
    """Statistics computation from node data."""

    def test_empty_nodes(self) -> None:
        result = _build_stats({}, "mpa")
        assert result["max"] == 0.0
        assert result["min"] == 0.0
        assert result["avg"] == 0.0
        assert result["nodes"] == {}

    def test_single_node(self) -> None:
        result = _build_stats({1: 42.0}, "mpa")
        assert result["max"] == 42.0
        assert result["min"] == 42.0
        assert result["avg"] == 42.0

    def test_multiple_nodes(self) -> None:
        result = _build_stats({1: 10.0, 2: 20.0, 3: 30.0}, "mpa")
        assert result["max"] == 30.0
        assert result["min"] == 10.0
        assert abs(result["avg"] - 20.0) < 0.01


# ---------------------------------------------------------------------------
# 4. Solver error classes
# ---------------------------------------------------------------------------


class TestSolverErrors:
    """Solver error hierarchy."""

    def test_solver_error_fields(self) -> None:
        err = SolverError("failed", returncode=1, stderr="bad input")
        assert err.returncode == 1
        assert err.stderr == "bad input"
        assert "failed" in str(err)

    def test_timeout_is_solver_error(self) -> None:
        err = SolverTimeoutError("timed out")
        assert isinstance(err, SolverError)

    def test_max_timeout_constant(self) -> None:
        assert MAX_SOLVER_TIMEOUT == 300


# ---------------------------------------------------------------------------
# 5. FRD parse error
# ---------------------------------------------------------------------------


class TestFrdParseError:
    """FRD parse error class."""

    def test_is_exception(self) -> None:
        err = FrdParseError("bad file")
        assert isinstance(err, Exception)
        assert "bad file" in str(err)


# ---------------------------------------------------------------------------
# 6. run_fea validation
# ---------------------------------------------------------------------------


class TestRunFeaValidation:
    """Input validation for run_fea (without running subprocess)."""

    @pytest.mark.asyncio
    async def test_missing_mesh_file(self) -> None:
        from tool_registry.tools.calculix.solver import run_fea

        with pytest.raises(FileNotFoundError, match="Mesh file not found"):
            await run_fea("/nonexistent/mesh.inp", "load1")

    @pytest.mark.asyncio
    async def test_wrong_extension(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from tool_registry.tools.calculix.solver import run_fea

        bad_file = tmp_path / "mesh.stl"
        bad_file.write_text("dummy")
        with pytest.raises(ValueError, match="must be a .inp file"):
            await run_fea(str(bad_file), "load1")

    @pytest.mark.asyncio
    async def test_unsupported_analysis_type(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from tool_registry.tools.calculix.solver import run_fea

        inp_file = tmp_path / "mesh.inp"
        inp_file.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported analysis type"):
            await run_fea(str(inp_file), "load1", analysis_type="thermal")
