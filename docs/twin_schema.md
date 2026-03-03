# Digital Twin Graph Schema

> **Version**: 0.2 (Phase 1 — Implementation)
> **Status**: Approved — matches implementation
> **Last Updated**: 2026-03-03
> **Depends on**: [`architecture.md`](architecture.md)
> **Referenced by**: [`skill_spec.md`](skill_spec.md), [`mcp_spec.md`](mcp_spec.md), [`roadmap.md`](roadmap.md)
> **Implementation**: `twin_core/` (models, graph engine, versioning, constraint engine)

## 1. Overview

The Digital Twin is the **single source of design truth** in MetaForge. It is a versioned, directed property graph that captures every artifact, constraint, relationship, and version in a hardware design.

All agents read from and propose changes to the Twin. No agent maintains its own persistent state — the Twin is the canonical record of what exists, what constrains it, and how it evolved.

> **v0.1 note**: The current implementation uses an in-memory graph engine (`InMemoryGraphEngine`). Neo4j integration is planned for v0.2+.

### Design Principles

1. **Graph-native**: Hardware designs are naturally graphs (components depend on each other, constraints span domains). A property graph captures this directly.
2. **Version-everything**: Every mutation creates a version record. The graph supports branching and merging like Git.
3. **Constraint-first**: Constraints are first-class nodes, not annotations. They are evaluated automatically on every proposed change.
4. **Domain-agnostic core**: The Twin schema is generic. Domain-specific semantics live in artifact metadata and constraint expressions.

---

### 1.1 Base Types

All graph nodes inherit from `NodeBase`, which provides a UUID identifier and a `NodeType` discriminator. All edges inherit from `EdgeBase` with a typed `EdgeType` field.

#### NodeType Enum

```python
from enum import StrEnum

class NodeType(StrEnum):
    """Discriminator for graph node types."""

    ARTIFACT = "artifact"
    CONSTRAINT = "constraint"
    VERSION = "version"
    COMPONENT = "component"
    AGENT = "agent"
```

*Source: `twin_core/models/enums.py`*

#### NodeBase

```python
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from twin_core.models.enums import NodeType

class NodeBase(BaseModel):
    """Abstract base for all graph nodes."""

    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType
```

All node models (`Artifact`, `Constraint`, `Version`, `Component`, `AgentNode`) inherit from `NodeBase` and set `node_type` to a default value matching their type.

*Source: `twin_core/models/base.py`*

#### EdgeType Enum

```python
class EdgeType(StrEnum):
    """Types of directed relationships between graph nodes."""

    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    VALIDATES = "validates"
    CONTAINS = "contains"
    VERSIONED_BY = "versioned_by"
    CONSTRAINED_BY = "constrained_by"
    PRODUCED_BY = "produced_by"
    USES_COMPONENT = "uses_component"
    PARENT_OF = "parent_of"
    CONFLICTS_WITH = "conflicts_with"
```

*Source: `twin_core/models/enums.py`*

#### EdgeBase

```python
from datetime import UTC, datetime

class EdgeBase(BaseModel):
    """A directed relationship between two graph nodes."""

    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)
```

*Source: `twin_core/models/base.py`*

---

## 2. Node Types

### 2.1 Artifact

An Artifact represents any design output: a schematic, BOM, PCB layout, firmware source file, test plan, simulation result, or manufacturing file.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `UUID` | Yes | Unique identifier (inherited from `NodeBase`) |
| `node_type` | `NodeType` | Yes | Always `NodeType.ARTIFACT` |
| `name` | `str` | Yes | Human-readable name (e.g., `"main_schematic"`) |
| `type` | `ArtifactType` | Yes | Enum: see below |
| `domain` | `str` | Yes | Engineering domain (e.g., `"mechanical"`, `"electronics"`) |
| `file_path` | `str` | Yes | Relative path within the project directory |
| `content_hash` | `str` | Yes | SHA-256 hash of file contents |
| `format` | `str` | Yes | File format (e.g., `"kicad_sch"`, `"step"`, `"json"`) |
| `metadata` | `dict` | No | Domain-specific key-value pairs |
| `created_at` | `datetime` | Yes | Creation timestamp |
| `updated_at` | `datetime` | Yes | Last modification timestamp |
| `created_by` | `str` | Yes | Agent ID or `"human"` |

**ArtifactType enum**:

```python
from enum import StrEnum

class ArtifactType(StrEnum):
    SCHEMATIC = "schematic"
    PCB_LAYOUT = "pcb_layout"
    BOM = "bom"
    CAD_MODEL = "cad_model"
    FIRMWARE_SOURCE = "firmware_source"
    SIMULATION_RESULT = "simulation_result"
    TEST_PLAN = "test_plan"
    TEST_RESULT = "test_result"
    MANUFACTURING_FILE = "manufacturing_file"
    CONSTRAINT_SET = "constraint_set"
    PRD = "prd"
    PINMAP = "pinmap"
    GERBER = "gerber"
    PICK_AND_PLACE = "pick_and_place"
    DOCUMENTATION = "documentation"
```

**Pydantic Model**:

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4
from pydantic import Field
from twin_core.models.base import NodeBase
from twin_core.models.enums import ArtifactType, NodeType

class Artifact(NodeBase):
    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.ARTIFACT
    name: str
    type: ArtifactType
    domain: str
    file_path: str
    content_hash: str
    format: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str
```

*Source: `twin_core/models/artifact.py`*

### 2.2 Constraint

A Constraint is a rule that must be satisfied across one or more artifacts. Constraints are first-class graph nodes evaluated by the Constraint Engine.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `UUID` | Yes | Unique identifier (inherited from `NodeBase`) |
| `node_type` | `NodeType` | Yes | Always `NodeType.CONSTRAINT` |
| `name` | `str` | Yes | Human-readable name (e.g., `"max_voltage_3v3"`) |
| `expression` | `str` | Yes | Constraint expression (see Constraint Language below) |
| `severity` | `ConstraintSeverity` | Yes | `ERROR`, `WARNING`, or `INFO` |
| `status` | `ConstraintStatus` | Yes | Current evaluation status |
| `domain` | `str` | Yes | Primary domain (e.g., `"electronics"`) |
| `cross_domain` | `bool` | No | Whether constraint spans multiple domains |
| `source` | `str` | Yes | Free-form string describing origin (e.g., `"user"`, `"agent"`, `"system"`) |
| `message` | `str` | No | Human-readable description of the constraint |
| `last_evaluated` | `datetime` | No | When the constraint was last checked |
| `metadata` | `dict` | No | Additional context |

```python
class ConstraintSeverity(StrEnum):
    ERROR = "error"       # Must be resolved — blocks commit
    WARNING = "warning"   # Should be resolved — does not block
    INFO = "info"         # Informational only

class ConstraintStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNEVALUATED = "unevaluated"
    SKIPPED = "skipped"   # Constraint not applicable to current state

class Constraint(NodeBase):
    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.CONSTRAINT
    name: str
    expression: str
    severity: ConstraintSeverity
    status: ConstraintStatus = ConstraintStatus.UNEVALUATED
    domain: str
    cross_domain: bool = False
    source: str
    message: str = ""
    last_evaluated: datetime | None = None
    metadata: dict = Field(default_factory=dict)
```

*Source: `twin_core/models/constraint.py`*

### 2.3 Version

A Version represents a point-in-time snapshot of the artifact graph. Versions form a DAG (directed acyclic graph) that supports branching and merging.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `UUID` | Yes | Unique identifier (inherited from `NodeBase`) |
| `node_type` | `NodeType` | Yes | Always `NodeType.VERSION` |
| `branch_name` | `str` | Yes | Branch this version belongs to (e.g., `"main"`, `"agent/mechanical/stress-fix"`) |
| `parent_id` | `UUID` | No | Parent version (null for initial version) |
| `merge_parent_id` | `UUID` | No | Second parent (for merge commits) |
| `commit_message` | `str` | Yes | Description of changes |
| `snapshot_hash` | `str` | Yes | SHA-256 hash of the complete graph state at this version |
| `author` | `str` | Yes | Agent ID, `"human"`, or `"system"` |
| `created_at` | `datetime` | Yes | Version creation timestamp |
| `artifact_ids` | `list[UUID]` | Yes | Artifacts modified in this version |

```python
class Version(NodeBase):
    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.VERSION
    branch_name: str
    parent_id: UUID | None = None
    merge_parent_id: UUID | None = None
    commit_message: str
    snapshot_hash: str
    author: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    artifact_ids: list[UUID] = Field(default_factory=list)
```

*Source: `twin_core/models/version.py`*

### 2.4 Component

A Component represents a physical part used in the design (IC, resistor, connector, etc.) with supply chain metadata.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `UUID` | Yes | Unique identifier (inherited from `NodeBase`) |
| `node_type` | `NodeType` | Yes | Always `NodeType.COMPONENT` |
| `part_number` | `str` | Yes | Manufacturer part number |
| `manufacturer` | `str` | Yes | Manufacturer name |
| `description` | `str` | No | Part description |
| `package` | `str` | No | Physical package (e.g., `"QFP-48"`, `"0402"`) |
| `lifecycle` | `ComponentLifecycle` | Yes | Production status |
| `datasheet_url` | `str` | No | Link to datasheet |
| `specs` | `dict` | No | Key electrical/mechanical specifications |
| `alternates` | `list[str]` | No | Alternative part numbers |
| `unit_cost` | `float` | No | Per-unit cost in USD |
| `lead_time_days` | `int` | No | Estimated lead time |
| `quantity` | `int` | No | Quantity used in design |

```python
class ComponentLifecycle(StrEnum):
    ACTIVE = "active"
    NRND = "nrnd"               # Not recommended for new designs
    EOL = "eol"                 # End of life
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"

class Component(NodeBase):
    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.COMPONENT
    part_number: str
    manufacturer: str
    description: str = ""
    package: str = ""
    lifecycle: ComponentLifecycle = ComponentLifecycle.ACTIVE
    datasheet_url: str = ""
    specs: dict = Field(default_factory=dict)
    alternates: list[str] = Field(default_factory=list)
    unit_cost: float | None = None
    lead_time_days: int | None = None
    quantity: int = 1
```

*Source: `twin_core/models/component.py`*

### 2.5 Agent

An Agent node records which agent produced or modified artifacts. It connects the provenance chain from human intent through agent execution to artifact output.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `UUID` | Yes | Unique identifier (inherited from `NodeBase`) |
| `node_type` | `NodeType` | Yes | Always `NodeType.AGENT` |
| `agent_type` | `str` | Yes | Agent discipline (e.g., `"mechanical"`, `"electronics"`) |
| `domain` | `str` | Yes | Engineering domain this agent covers |
| `session_id` | `UUID` | Yes | Current execution session |
| `skills_used` | `list[str]` | No | Skill IDs invoked during this session |
| `started_at` | `datetime` | Yes | Session start time |
| `completed_at` | `datetime` | No | Session completion time |
| `status` | `str` | Yes | `"running"`, `"completed"`, `"failed"` |

```python
class AgentNode(NodeBase):
    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.AGENT
    agent_type: str
    domain: str
    session_id: UUID
    skills_used: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"
```

*Source: `twin_core/models/agent.py`*

---

## 3. Edge Types

Edges are directed relationships between nodes. Each edge type has defined source and target node types.

| Edge Type | Source -> Target | Description |
|-----------|-----------------|-------------|
| `DEPENDS_ON` | Artifact -> Artifact | Artifact A requires Artifact B (e.g., PCB depends on schematic) |
| `IMPLEMENTS` | Artifact -> Artifact | Artifact A implements the spec defined in Artifact B |
| `VALIDATES` | Artifact -> Artifact | Artifact A (test result) validates Artifact B (design) |
| `CONTAINS` | Artifact -> Artifact | Artifact A contains Artifact B (hierarchical composition) |
| `VERSIONED_BY` | Artifact -> Version | Links an artifact to the version that last modified it |
| `CONSTRAINED_BY` | Artifact -> Constraint | Constraint applies to this artifact |
| `PRODUCED_BY` | Artifact -> Agent | Artifact was produced or modified by this agent |
| `USES_COMPONENT` | Artifact -> Component | Artifact references this component (e.g., BOM uses resistor) |
| `PARENT_OF` | Version -> Version | Version lineage (parent -> child) |
| `CONFLICTS_WITH` | Constraint -> Constraint | Two constraints that cannot both be satisfied |

### Typed Edge Models

Edges with domain-specific properties are modeled as typed subclasses of `EdgeBase`:

```python
class DependsOnEdge(EdgeBase):
    """Artifact A requires Artifact B."""

    edge_type: EdgeType = EdgeType.DEPENDS_ON
    dependency_type: str = "hard"  # "hard" or "soft"
    description: str = ""


class UsesComponentEdge(EdgeBase):
    """Artifact references a physical component."""

    edge_type: EdgeType = EdgeType.USES_COMPONENT
    reference_designator: str = ""  # e.g. "R1", "U3"
    quantity: int = 1


class ConstrainedByEdge(EdgeBase):
    """Constraint applies to an artifact."""

    edge_type: EdgeType = EdgeType.CONSTRAINED_BY
    scope: str = "local"  # "local" or "global"
    priority: int = 0
```

*Source: `twin_core/models/relationship.py`*

### SubGraph Response

```python
class SubGraph(BaseModel):
    """A traversal result containing a subset of the graph."""

    nodes: list[NodeBase] = Field(default_factory=list)
    edges: list[EdgeBase] = Field(default_factory=list)
    root_id: UUID
    depth: int
```

*Source: `twin_core/models/relationship.py`*

---

### 3.1 Graph Engine Interface

The `GraphEngine` ABC defines the core contract for all graph storage backends. It provides node CRUD, edge management, and traversal queries.

> **v0.1**: `InMemoryGraphEngine` (dict-based, for development and testing).
> **Planned**: `Neo4jGraphEngine` for production persistence.

```python
from abc import ABC, abstractmethod
from uuid import UUID
from twin_core.models.base import EdgeBase, NodeBase
from twin_core.models.enums import EdgeType, NodeType
from twin_core.models.relationship import SubGraph


class GraphEngine(ABC):
    """Abstract interface for Digital Twin graph storage and retrieval.

    All backends (in-memory, Neo4j) implement this contract.
    """

    # --- Node operations ---

    @abstractmethod
    async def add_node(self, node: NodeBase) -> NodeBase:
        """Add a node to the graph. Raises ValueError if ID already exists."""
        ...

    @abstractmethod
    async def get_node(self, node_id: UUID) -> NodeBase | None:
        """Retrieve a node by ID, or None if not found."""
        ...

    @abstractmethod
    async def update_node(self, node_id: UUID, updates: dict) -> NodeBase:
        """Update a node's fields. Raises KeyError if node not found."""
        ...

    @abstractmethod
    async def delete_node(self, node_id: UUID) -> bool:
        """Delete a node and all its connected edges. Returns False if not found."""
        ...

    @abstractmethod
    async def list_nodes(
        self,
        node_type: NodeType | None = None,
        filters: dict | None = None,
    ) -> list[NodeBase]:
        """List nodes, optionally filtered by type and field values."""
        ...

    # --- Edge operations ---

    @abstractmethod
    async def add_edge(self, edge: EdgeBase) -> EdgeBase:
        """Add an edge. Raises ValueError if source or target node doesn't exist."""
        ...

    @abstractmethod
    async def get_edges(
        self,
        node_id: UUID,
        direction: str = "outgoing",
        edge_type: EdgeType | None = None,
    ) -> list[EdgeBase]:
        """Get edges connected to a node. Direction: 'outgoing', 'incoming', or 'both'."""
        ...

    @abstractmethod
    async def remove_edge(
        self, source_id: UUID, target_id: UUID, edge_type: EdgeType
    ) -> bool:
        """Remove a specific edge. Returns False if not found."""
        ...

    # --- Traversal queries ---

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: UUID,
        edge_type: EdgeType | None = None,
        direction: str = "outgoing",
    ) -> list[NodeBase]:
        """Get nodes directly connected to the given node."""
        ...

    @abstractmethod
    async def get_subgraph(
        self,
        root_id: UUID,
        depth: int = 2,
        edge_types: list[EdgeType] | None = None,
    ) -> SubGraph:
        """BFS traversal from root, returning all nodes/edges within depth hops."""
        ...

    @abstractmethod
    async def traverse(
        self,
        root_id: UUID,
        edge_types: list[EdgeType],
        max_depth: int = 5,
    ) -> list[list[UUID]]:
        """Find all paths from root following the given edge types, up to max_depth."""
        ...
```

*Source: `twin_core/graph_engine.py`*

---

## 4. Versioning Model

The Twin uses a Git-like branching model for the artifact graph. Every mutation goes through a version, and changes can be isolated in branches before merging.

### Branch Types

| Branch | Purpose | Lifecycle |
|--------|---------|-----------|
| `main` | Canonical design state — approved artifacts only | Persistent |
| `agent/<domain>/<task>` | Agent working branch for a specific task | Temporary — merged or discarded |
| `review/<id>` | Human review branch for approval workflow | Temporary — merged or discarded |

### Version Operations

```python
from abc import ABC, abstractmethod

class VersionEngine(ABC):
    """Abstract interface for Git-like versioning of the artifact graph."""

    @abstractmethod
    async def create_branch(self, name: str, from_version: UUID | None = None) -> str:
        """Create a new branch, optionally forking from a specific version.

        If from_version is None, forks from the HEAD of "main".

        Raises:
            ValueError: If branch name already exists.
            KeyError: If from_version doesn't exist.
        """
        ...

    @abstractmethod
    async def commit(
        self,
        branch: str,
        message: str,
        artifact_ids: list[UUID],
        author: str,
    ) -> Version:
        """Create a new version on the given branch.

        Captures a snapshot of all tracked artifacts, overlaying changes
        from the provided artifact_ids.

        Raises:
            KeyError: If branch doesn't exist or an artifact_id is not in the graph.
        """
        ...

    @abstractmethod
    async def merge(
        self,
        source_branch: str,
        target_branch: str,
        message: str,
        author: str,
    ) -> Version:
        """Merge source_branch into target_branch.

        Uses three-way merge with common ancestor detection.

        Raises:
            KeyError: If either branch doesn't exist.
            MergeConflict: If conflicting changes are detected.
        """
        ...

    @abstractmethod
    async def diff(self, version_a: UUID, version_b: UUID) -> VersionDiff:
        """Compute the diff between two versions.

        Raises:
            KeyError: If either version doesn't exist.
        """
        ...

    @abstractmethod
    async def log(self, branch: str, limit: int = 50) -> list[Version]:
        """Return commit history for a branch, newest first.

        Raises:
            KeyError: If branch doesn't exist.
        """
        ...

    @abstractmethod
    async def get_head(self, branch: str) -> Version:
        """Get the HEAD version of a branch.

        Raises:
            KeyError: If branch doesn't exist or has no commits.
        """
        ...
```

*Source: `twin_core/versioning/branch.py`*

### Version Diff

```python
class ArtifactChange(BaseModel):
    """A single artifact change between two versions."""

    artifact_id: UUID
    change_type: str  # "added", "modified", "deleted"
    old_content_hash: str | None = None
    new_content_hash: str | None = None

class VersionDiff(BaseModel):
    """The diff between two versions."""

    version_a: UUID
    version_b: UUID
    changes: list[ArtifactChange]
    constraints_added: list[UUID] = Field(default_factory=list)
    constraints_removed: list[UUID] = Field(default_factory=list)
```

*Source: `twin_core/models/version.py`*

### Three-Way Merge Algorithm

The merge implementation follows Git's three-way merge strategy:

1. **Common ancestor detection**: `_find_common_ancestor()` uses interleaved BFS from both branch HEADs, walking `parent_id` and `merge_parent_id` links, to find the nearest shared commit.

2. **Conflict detection**: `detect_conflicts()` compares source and target snapshots against the ancestor:
   - **Content conflict**: Both branches modified the same artifact with different content hashes.
   - **Structural conflict**: One branch deleted an artifact that the other branch modified (or added differently).
   - **No conflict**: If only one side changed, or both sides made identical changes.

3. **Merge execution**: `perform_merge()` starts from the target snapshot and applies non-conflicting source changes. If any conflicts exist, it raises `MergeConflict`.

```python
class ConflictDetail(BaseModel):
    """Description of a single merge conflict."""

    artifact_id: UUID
    conflict_type: str  # "content" or "structural"
    source_hash: str | None = None
    target_hash: str | None = None


class MergeConflict(Exception):
    """Raised when a three-way merge encounters unresolvable conflicts."""

    def __init__(self, conflicts: list[ConflictDetail]) -> None:
        self.conflicts = conflicts
        ids = ", ".join(str(c.artifact_id)[:8] for c in conflicts)
        super().__init__(f"Merge conflicts on artifacts: {ids}")
```

*Source: `twin_core/versioning/merge.py`*

Conflicts must be resolved manually (by a human or an agent with explicit instructions). Auto-merge is only performed for non-conflicting changes.

---

## 5. Constraint Engine

The Constraint Engine evaluates rules against the current graph state. It runs automatically on every proposed commit.

### Constraint Engine Interface

```python
from abc import ABC, abstractmethod
from uuid import UUID
from twin_core.constraint_engine.models import ConstraintEvaluationResult
from twin_core.models.constraint import Constraint


class ConstraintEngine(ABC):
    """Abstract interface for constraint evaluation against the Digital Twin graph."""

    @abstractmethod
    async def evaluate(
        self, artifact_ids: list[UUID]
    ) -> ConstraintEvaluationResult:
        """Evaluate constraints relevant to the given artifacts.

        Returns a result indicating whether all ERROR-severity constraints pass.
        """
        ...

    @abstractmethod
    async def evaluate_all(self) -> ConstraintEvaluationResult:
        """Evaluate every constraint in the graph."""
        ...

    @abstractmethod
    async def add_constraint(
        self, constraint: Constraint, artifact_ids: list[UUID]
    ) -> Constraint:
        """Register a constraint and create CONSTRAINED_BY edges to the given artifacts."""
        ...

    @abstractmethod
    async def get_constraint(self, constraint_id: UUID) -> Constraint | None:
        """Retrieve a constraint by ID, or None if not found."""
        ...

    @abstractmethod
    async def remove_constraint(self, constraint_id: UUID) -> bool:
        """Delete a constraint node and all its edges. Returns False if not found."""
        ...
```

> **v0.1**: `InMemoryConstraintEngine` backed by a `GraphEngine` instance.

*Source: `twin_core/constraint_engine/validator.py`*

### Constraint Language

Constraints are expressed as Python expressions evaluated against a context object. The expression must return a boolean (`True` = pass, `False` = fail).

```python
# Example constraint expressions:

# Voltage rail must not exceed 3.3V
"ctx.artifact('power_budget').metadata.get('max_voltage', 0) <= 3.3"

# BOM cost must stay under $50
"ctx.artifact('bom').metadata.get('total_cost', 0) < 50.0"

# All components must be ACTIVE lifecycle
"all(c.lifecycle == 'active' for c in ctx.components())"

# PCB must have DRC passing
"ctx.artifact('pcb_layout').metadata.get('drc_status') == 'pass'"
```

### Safe Builtins Whitelist

Constraint expressions run in a restricted `eval()` environment. Only the following 25 builtins are available — no `__import__`, `open`, `exec`, `eval`, or `compile`:

| Category | Functions |
|----------|-----------|
| Aggregation | `all`, `any`, `len`, `min`, `max`, `sum`, `abs`, `round` |
| Iteration | `sorted`, `enumerate`, `zip`, `map`, `filter` |
| Type checking | `isinstance` |
| Type constructors | `str`, `int`, `float`, `bool`, `list`, `dict`, `set`, `tuple` |
| Constants | `True`, `False`, `None` |

*Source: `twin_core/constraint_engine/validator.py` (`_SAFE_BUILTINS` dict)*

### Constraint Evaluation Context

The `ConstraintContext` is a **plain class** (not a Pydantic `BaseModel`) that provides a synchronous, read-only view of the graph state. It is pre-loaded asynchronously by `build_context()` so that `eval()` never needs to `await`.

```python
class ConstraintContext:
    """Synchronous read-only snapshot of graph state, exposed as ``ctx`` in expressions."""

    def __init__(
        self,
        artifacts_by_name: dict[str, Artifact],
        artifacts_by_id: dict[UUID, Artifact],
        all_components: list[Component],
        dependency_map: dict[UUID, list[UUID]],
    ) -> None: ...

    def artifact(self, name: str) -> Artifact:
        """Lookup an artifact by name. Raises KeyError if not found."""
        ...

    def artifacts(
        self,
        domain: str | None = None,
        type: str | None = None,
    ) -> list[Artifact]:
        """Return artifacts, optionally filtered by domain and/or type."""
        ...

    def components(self) -> list[Component]:
        """Return all components in the graph."""
        ...

    def dependents(self, artifact_id: UUID) -> list[Artifact]:
        """Return artifacts that have incoming DEPENDS_ON edges to artifact_id."""
        ...


async def build_context(graph: GraphEngine) -> ConstraintContext:
    """Async factory that pre-loads graph state into a synchronous ConstraintContext.

    Loads all artifacts (indexed by name and ID), all components, and builds
    a dependency map by following incoming DEPENDS_ON edges.
    """
    ...
```

*Source: `twin_core/constraint_engine/context.py`*

### Constraint Resolver

The resolver module handles two-phase constraint discovery:

```python
async def resolve_constraints(
    graph: GraphEngine,
    artifact_ids: list[UUID],
) -> list[Constraint]:
    """Two-phase constraint resolution.

    1. Follow outgoing CONSTRAINED_BY edges from each artifact to find direct constraints.
    2. Include all cross_domain=True constraints from the graph.
    3. Deduplicate by constraint ID.
    """
    ...


async def find_constrained_artifacts(
    graph: GraphEngine,
    constraint_id: UUID,
) -> list[UUID]:
    """Reverse lookup: find which artifacts a constraint applies to.

    Follows incoming CONSTRAINED_BY edges to the constraint node.
    """
    ...
```

*Source: `twin_core/constraint_engine/resolver.py`*

### Evaluation Lifecycle

```
Proposed commit arrives
        |
        v
  Load all constraints linked to modified artifacts
  (resolve_constraints: direct CONSTRAINED_BY edges + cross_domain constraints)
        |
        v
  Build ConstraintContext (async pre-load of graph state)
        |
        v
  Evaluate each constraint expression against ctx (restricted eval)
        |
        v
  Collect results: PASS / FAIL / WARN / SKIPPED
        |
        v
  Any ERROR-severity FAIL?
   |-- Yes -> Block commit, return violations
   +-- No  -> Allow commit (warnings logged)
```

### Constraint Evaluation Result

```python
class ConstraintViolation(BaseModel):
    constraint_id: UUID
    constraint_name: str
    severity: ConstraintSeverity
    message: str
    artifact_ids: list[UUID] = Field(default_factory=list)
    expression: str
    evaluated_at: datetime

class ConstraintEvaluationResult(BaseModel):
    passed: bool  # False if any ERROR-severity constraint fails
    violations: list[ConstraintViolation] = Field(default_factory=list)
    warnings: list[ConstraintViolation] = Field(default_factory=list)
    evaluated_count: int = 0
    skipped_count: int = 0
    duration_ms: float = 0.0
```

*Source: `twin_core/constraint_engine/models.py`*

---

## 6. Twin API

The Twin API is the public interface for all graph operations. Agents, the orchestrator, and the gateway interact with the Twin exclusively through this API.

> **Note**: The Twin API composes the lower-level `GraphEngine`, `VersionEngine`, and `ConstraintEngine` interfaces into a single facade. See Section 3.1, Section 4, and Section 5 for the underlying ABCs.

### CRUD Operations

```python
class TwinAPI(ABC):
    # --- Artifacts ---
    @abstractmethod
    async def create_artifact(self, artifact: Artifact, branch: str = "main") -> Artifact:
        ...

    @abstractmethod
    async def get_artifact(self, artifact_id: UUID, branch: str = "main") -> Artifact | None:
        ...

    @abstractmethod
    async def update_artifact(self, artifact_id: UUID, updates: dict, branch: str = "main") -> Artifact:
        ...

    @abstractmethod
    async def delete_artifact(self, artifact_id: UUID, branch: str = "main") -> bool:
        ...

    @abstractmethod
    async def list_artifacts(
        self,
        branch: str = "main",
        domain: str | None = None,
        artifact_type: ArtifactType | None = None,
    ) -> list[Artifact]:
        ...

    # --- Constraints ---
    @abstractmethod
    async def create_constraint(self, constraint: Constraint) -> Constraint:
        ...

    @abstractmethod
    async def get_constraint(self, constraint_id: UUID) -> Constraint | None:
        ...

    @abstractmethod
    async def evaluate_constraints(self, branch: str = "main") -> ConstraintEvaluationResult:
        ...

    # --- Components ---
    @abstractmethod
    async def add_component(self, component: Component) -> Component:
        ...

    @abstractmethod
    async def get_component(self, component_id: UUID) -> Component | None:
        ...

    @abstractmethod
    async def find_components(self, query: dict) -> list[Component]:
        ...

    # --- Relationships ---
    @abstractmethod
    async def add_edge(self, source_id: UUID, target_id: UUID, edge_type: EdgeType, metadata: dict | None = None) -> EdgeBase:
        ...

    @abstractmethod
    async def get_edges(self, node_id: UUID, direction: str = "outgoing", edge_type: EdgeType | None = None) -> list[EdgeBase]:
        ...

    @abstractmethod
    async def remove_edge(self, source_id: UUID, target_id: UUID, edge_type: EdgeType) -> bool:
        ...

    # --- Queries ---
    @abstractmethod
    async def get_subgraph(self, root_id: UUID, depth: int = 2, edge_types: list[EdgeType] | None = None) -> SubGraph:
        ...

    @abstractmethod
    async def query_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute a raw Cypher query (read-only). For advanced queries not covered by the API."""
        ...

    # --- Versioning ---
    @abstractmethod
    async def create_branch(self, name: str, from_branch: str = "main") -> str:
        ...

    @abstractmethod
    async def commit(self, branch: str, message: str, author: str) -> Version:
        ...

    @abstractmethod
    async def merge(self, source: str, target: str, message: str, author: str) -> Version:
        ...

    @abstractmethod
    async def diff(self, branch_a: str, branch_b: str) -> VersionDiff:
        ...

    @abstractmethod
    async def log(self, branch: str = "main", limit: int = 50) -> list[Version]:
        ...
```

---

## 7. Neo4j Implementation

> **Status**: Planned for v0.2+. The current implementation uses `InMemoryGraphEngine`.

### Index Strategy

```cypher
-- Primary key indexes
CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT constraint_id IF NOT EXISTS FOR (c:Constraint) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT version_id IF NOT EXISTS FOR (v:Version) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT component_id IF NOT EXISTS FOR (p:Component) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (ag:Agent) REQUIRE ag.id IS UNIQUE;

-- Lookup indexes
CREATE INDEX artifact_domain IF NOT EXISTS FOR (a:Artifact) ON (a.domain);
CREATE INDEX artifact_type IF NOT EXISTS FOR (a:Artifact) ON (a.type);
CREATE INDEX artifact_path IF NOT EXISTS FOR (a:Artifact) ON (a.file_path);
CREATE INDEX constraint_domain IF NOT EXISTS FOR (c:Constraint) ON (c.domain);
CREATE INDEX constraint_status IF NOT EXISTS FOR (c:Constraint) ON (c.status);
CREATE INDEX version_branch IF NOT EXISTS FOR (v:Version) ON (v.branch_name);
CREATE INDEX component_part IF NOT EXISTS FOR (p:Component) ON (p.part_number);
CREATE INDEX component_mfr IF NOT EXISTS FOR (p:Component) ON (p.manufacturer);
```

### Common Cypher Patterns

**Get all artifacts in a domain with their constraints**:

```cypher
MATCH (a:Artifact {domain: $domain})
OPTIONAL MATCH (a)-[:CONSTRAINED_BY]->(c:Constraint)
RETURN a, collect(c) AS constraints
```

**Get the dependency tree for an artifact**:

```cypher
MATCH path = (root:Artifact {id: $artifact_id})-[:DEPENDS_ON*1..5]->(dep:Artifact)
RETURN root, nodes(path) AS chain, relationships(path) AS edges
```

**Find all artifacts produced by an agent session**:

```cypher
MATCH (ag:Agent {session_id: $session_id})<-[:PRODUCED_BY]-(a:Artifact)
RETURN a ORDER BY a.created_at
```

**Get version history for a branch**:

```cypher
MATCH (v:Version {branch_name: $branch})
OPTIONAL MATCH (v)-[:PARENT_OF]->(parent:Version)
RETURN v, parent.id AS parent_id
ORDER BY v.created_at DESC
LIMIT $limit
```

**Evaluate which constraints apply to modified artifacts**:

```cypher
MATCH (a:Artifact)
WHERE a.id IN $modified_artifact_ids
MATCH (a)-[:CONSTRAINED_BY]->(c:Constraint)
RETURN DISTINCT c
```

**Get BOM with components and reference designators**:

```cypher
MATCH (bom:Artifact {type: 'bom'})-[r:USES_COMPONENT]->(comp:Component)
RETURN comp.part_number, comp.manufacturer, comp.description,
       r.reference_designator, r.quantity, comp.unit_cost
ORDER BY r.reference_designator
```

---

## 8. Schema Evolution

The Twin schema will evolve across phases. Schema changes follow these rules:

1. **Additive only** within a major version: new node types, new properties (with defaults), new edge types.
2. **No breaking changes** to existing node/edge properties within a major version.
3. **Migration scripts** are provided for any structural changes across major versions.
4. **Node labels** are never renamed — deprecated labels are kept as aliases.

### Phase 1 Schema

Phase 1 implements the full schema defined in this document. The following node types and edge types are required for the mechanical vertical (MET-8):

- **Nodes**: Artifact (CAD_MODEL, SIMULATION_RESULT), Constraint, Version, Component, Agent
- **Edges**: DEPENDS_ON, CONSTRAINED_BY, PRODUCED_BY, VERSIONED_BY, USES_COMPONENT

### Phase 2 Additions

- Additional ArtifactType values for electronics (SCHEMATIC write support)
- Extended Component specs for electronics parts (voltage rating, current rating, ESR)
- New edge type: `ROUTED_TO` (net-to-pad routing in PCB)

### Phase 3 Additions

- Supply chain tracking nodes (Supplier, Order)
- Telemetry nodes (FieldData, DeviceInstance)
- Additional edge types for after-sales and sustainability tracking
