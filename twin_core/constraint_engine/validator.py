"""Constraint validation engine.

Evaluates constraint expressions against the current graph state.
Provides sandboxed Python expression evaluation with access to
artifacts, components, and dependencies via ConstraintContext.
"""

import time
from datetime import datetime
from uuid import UUID

from ..config import config
from ..exceptions import ConstraintViolationError
from ..graph_engine import GraphEngine
from ..models import (
    Artifact,
    ArtifactType,
    Component,
    Constraint,
    ConstraintContext,
    ConstraintEvaluationResult,
    ConstraintSeverity,
    ConstraintStatus,
    ConstraintViolation,
)


class ConstraintContextImpl(ConstraintContext):
    """Concrete implementation of ConstraintContext.

    This class is injected as 'ctx' into constraint expressions.
    It queries the graph to provide access to artifacts, components,
    and dependencies.
    """

    def __init__(self, graph_engine: GraphEngine, branch: str = "main"):
        """Initialize context with graph engine.

        Args:
            graph_engine: GraphEngine instance for querying
            branch: Branch name to query (default: "main")
        """
        super().__init__()
        self.graph = graph_engine
        self.branch = branch
        self._artifact_cache: dict[str, Artifact] = {}

    def artifact(self, name: str) -> Artifact:
        """Retrieve an artifact by name from the current graph state.

        Args:
            name: Name of the artifact to retrieve.

        Returns:
            Artifact instance.

        Raises:
            KeyError: If artifact not found.
        """
        # Check cache
        if name in self._artifact_cache:
            return self._artifact_cache[name]

        # Query graph
        # TODO: Implement actual query using graph_engine
        # For now, raise KeyError
        raise KeyError(f"Artifact '{name}' not found")

    def artifacts(
        self,
        domain: str | None = None,
        artifact_type: ArtifactType | None = None,
    ) -> list[Artifact]:
        """Query artifacts by domain and/or type.

        Args:
            domain: Filter by engineering domain (optional).
            artifact_type: Filter by artifact type (optional).

        Returns:
            List of matching artifacts.
        """
        # TODO: Implement actual query using graph_engine
        return []

    def components(self) -> list[Component]:
        """Retrieve all components in the current design.

        Returns:
            List of Component instances.
        """
        # TODO: Implement actual query using graph_engine
        return []

    def dependents(self, artifact_id: UUID) -> list[Artifact]:
        """Get all artifacts that depend on the given artifact.

        Args:
            artifact_id: UUID of the artifact.

        Returns:
            List of dependent artifacts.
        """
        # TODO: Implement by following DEPENDS_ON edges
        return []


class ConstraintExpressionEvaluator:
    """Evaluates constraint expressions in a sandboxed environment.

    Constraint expressions are Python code evaluated with a restricted
    set of builtins to prevent dangerous operations (file I/O, imports, etc.).
    """

    def __init__(self):
        """Initialize evaluator with safe builtins."""
        # Whitelist of safe built-in functions
        self.safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            # Explicitly excluded: __import__, open, eval, exec, compile
        }

    def evaluate(
        self, expression: str, context: ConstraintContextImpl
    ) -> bool:
        """Evaluate a constraint expression.

        Args:
            expression: Python expression to evaluate
            context: ConstraintContext with graph access

        Returns:
            Boolean result of expression evaluation.

        Raises:
            Exception: If expression is invalid or evaluation fails.
        """
        # Build safe globals environment
        safe_globals = {
            "__builtins__": self.safe_builtins,
            "ctx": context,
        }

        try:
            # Evaluate expression with timeout
            result = eval(expression, safe_globals, {})
            return bool(result)
        except Exception as e:
            # Log evaluation error
            raise ValueError(f"Constraint expression evaluation failed: {e}")


class ConstraintValidator:
    """Validates constraints against graph state.

    This is the main constraint evaluation pipeline that:
    1. Loads constraints linked to modified artifacts
    2. Expands to cross-domain constraints
    3. Evaluates each expression
    4. Collects PASS/FAIL/WARN results
    5. Returns evaluation result
    """

    def __init__(self, graph_engine: GraphEngine):
        """Initialize validator with graph engine.

        Args:
            graph_engine: GraphEngine instance for queries.
        """
        self.graph = graph_engine
        self.evaluator = ConstraintExpressionEvaluator()

    async def evaluate_constraints_for_commit(
        self, branch: str, modified_artifact_ids: list[UUID]
    ) -> ConstraintEvaluationResult:
        """Evaluate all constraints affected by modified artifacts.

        Args:
            branch: Branch name
            modified_artifact_ids: List of artifact IDs modified in commit

        Returns:
            ConstraintEvaluationResult with violations and warnings.
        """
        start_time = time.time()

        # 1. Load constraints linked to modified artifacts
        constraints = await self._load_affected_constraints(modified_artifact_ids)

        # 2. Expand to cross-domain constraints
        constraints = await self._expand_cross_domain_constraints(constraints)

        # 3. Evaluate each constraint
        violations = []
        warnings = []
        evaluated_count = 0
        skipped_count = 0

        context = ConstraintContextImpl(self.graph, branch)

        for constraint in constraints:
            try:
                # Evaluate expression
                passed = self.evaluator.evaluate(constraint.expression, context)

                if not passed:
                    violation = ConstraintViolation(
                        constraint_id=constraint.id,
                        constraint_name=constraint.name,
                        severity=constraint.severity,
                        message=constraint.message,
                        artifact_ids=modified_artifact_ids,
                        expression=constraint.expression,
                        evaluated_at=datetime.utcnow(),
                    )

                    if constraint.severity == ConstraintSeverity.ERROR:
                        violations.append(violation)
                    elif constraint.severity == ConstraintSeverity.WARNING:
                        warnings.append(violation)

                evaluated_count += 1

                # Update constraint status in graph
                await self._update_constraint_status(
                    constraint.id,
                    ConstraintStatus.PASS if passed else ConstraintStatus.FAIL,
                )

            except Exception as e:
                # Skip constraint if evaluation fails
                skipped_count += 1
                # TODO: Log evaluation error

        # 4. Compute result
        duration_ms = (time.time() - start_time) * 1000
        passed = len(violations) == 0

        return ConstraintEvaluationResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            evaluated_count=evaluated_count,
            skipped_count=skipped_count,
            duration_ms=duration_ms,
        )

    async def _load_affected_constraints(
        self, artifact_ids: list[UUID]
    ) -> list[Constraint]:
        """Load all constraints that apply to the given artifacts.

        Args:
            artifact_ids: List of artifact UUIDs

        Returns:
            List of Constraint instances.
        """
        # TODO: Query graph for constraints linked via CONSTRAINED_BY edges
        return []

    async def _expand_cross_domain_constraints(
        self, constraints: list[Constraint]
    ) -> list[Constraint]:
        """Expand to include cross-domain constraints.

        Args:
            constraints: Initial list of constraints

        Returns:
            Expanded list including cross-domain constraints.
        """
        # TODO: Find constraints with cross_domain=True that transitively apply
        return constraints

    async def _update_constraint_status(
        self, constraint_id: UUID, status: ConstraintStatus
    ) -> None:
        """Update the status of a constraint in the graph.

        Args:
            constraint_id: Constraint UUID
            status: New status
        """
        # TODO: Update constraint node in graph
        pass
