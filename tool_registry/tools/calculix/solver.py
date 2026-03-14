"""CalculiX solver wrapper -- subprocess invocation with timeout handling."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any

import structlog

from observability.tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer("tool_registry.tools.calculix.solver")

# Maximum solver timeout in seconds
MAX_SOLVER_TIMEOUT = 300


class SolverError(Exception):
    """Raised when the CalculiX solver fails."""

    def __init__(self, message: str, returncode: int | None = None, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class SolverTimeoutError(SolverError):
    """Raised when the solver exceeds the timeout."""


async def run_fea(
    mesh_file: str,
    load_case: str,
    analysis_type: str = "static_stress",
    timeout: int = MAX_SOLVER_TIMEOUT,
    ccx_binary: str = "ccx",
    work_dir: str | None = None,
) -> dict[str, Any]:
    """Run CalculiX FEA analysis via subprocess.

    Args:
        mesh_file: Path to the .inp mesh file.
        load_case: Load case identifier (used for logging/tracing).
        analysis_type: Type of analysis (static_stress, modal).
        timeout: Maximum solver time in seconds (capped at MAX_SOLVER_TIMEOUT).
        ccx_binary: Path to the ccx binary.
        work_dir: Working directory for solver execution. Defaults to mesh file directory.

    Returns:
        Dict with keys: result_files, stdout, stderr, returncode, solver_time_s.

    Raises:
        SolverError: If the solver returns a non-zero exit code.
        SolverTimeoutError: If the solver exceeds the timeout.
        FileNotFoundError: If the mesh file does not exist.
        ValueError: If arguments are invalid.
    """
    effective_timeout = min(timeout, MAX_SOLVER_TIMEOUT)

    mesh_path = Path(mesh_file)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_file}")

    if not mesh_path.suffix == ".inp":
        raise ValueError(f"Mesh file must be a .inp file, got: {mesh_path.suffix}")

    if analysis_type not in ("static_stress", "modal"):
        raise ValueError(f"Unsupported analysis type: {analysis_type}")

    # CalculiX expects the job name without the .inp extension
    job_name = mesh_path.stem
    effective_work_dir = work_dir or str(mesh_path.parent)

    # Verify ccx binary is available
    if not shutil.which(ccx_binary):
        raise SolverError(f"CalculiX binary not found: {ccx_binary}")

    with tracer.start_as_current_span("calculix.run_fea") as span:
        span.set_attribute("calculix.mesh_file", mesh_file)
        span.set_attribute("calculix.load_case", load_case)
        span.set_attribute("calculix.analysis_type", analysis_type)
        span.set_attribute("calculix.timeout_s", effective_timeout)

        logger.info(
            "Starting CalculiX solver",
            mesh_file=mesh_file,
            load_case=load_case,
            analysis_type=analysis_type,
            timeout=effective_timeout,
        )

        start_time = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                ccx_binary,
                "-i",
                job_name,
                cwd=effective_work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "OMP_NUM_THREADS": "1"},
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=effective_timeout,
            )

        except TimeoutError:
            # Kill the process on timeout
            try:
                process.kill()  # type: ignore[possibly-undefined]
                await process.wait()  # type: ignore[possibly-undefined]
            except ProcessLookupError:
                pass

            elapsed = time.monotonic() - start_time
            span.set_attribute("calculix.timed_out", True)
            span.set_attribute("calculix.elapsed_s", elapsed)

            logger.error(
                "CalculiX solver timed out",
                mesh_file=mesh_file,
                timeout=effective_timeout,
                elapsed_s=elapsed,
            )
            raise SolverTimeoutError(
                f"CalculiX solver timed out after {effective_timeout}s",
                returncode=None,
                stderr="",
            )

        except Exception as exc:
            span.record_exception(exc)
            raise

        elapsed = time.monotonic() - start_time
        stdout_str = stdout_bytes.decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        span.set_attribute("calculix.elapsed_s", elapsed)
        span.set_attribute("calculix.returncode", process.returncode or 0)

        if process.returncode != 0:
            logger.error(
                "CalculiX solver failed",
                returncode=process.returncode,
                stderr=stderr_str[:500],
            )
            raise SolverError(
                f"CalculiX solver exited with code {process.returncode}",
                returncode=process.returncode,
                stderr=stderr_str,
            )

        # Collect result files
        work_path = Path(effective_work_dir)
        result_files: list[str] = []
        for ext in (".frd", ".dat", ".sta", ".cvg"):
            result_path = work_path / f"{job_name}{ext}"
            if result_path.exists():
                result_files.append(str(result_path))

        logger.info(
            "CalculiX solver completed",
            mesh_file=mesh_file,
            elapsed_s=round(elapsed, 2),
            result_files=result_files,
        )

        return {
            "result_files": result_files,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": process.returncode,
            "solver_time_s": round(elapsed, 2),
            "job_name": job_name,
            "work_dir": effective_work_dir,
        }
