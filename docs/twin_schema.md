# Digital Twin Graph Schema

> **Version**: 0.1 (Phase 0 — Spec & Design)
> **Status**: Draft
> **Last Updated**: 2026-03-02
> **Depends on**: [`architecture.md`](architecture.md)
> **Referenced by**: [`skill_spec.md`](skill_spec.md), [`mcp_spec.md`](mcp_spec.md), [`roadmap.md`](roadmap.md)

## 1. Overview

The Digital Twin is the **single source of design truth** in MetaForge. It is a versioned, directed property graph stored in Neo4j that captures every artifact, constraint, relationship, and version in a hardware design.

All agents read from and propose changes to the Twin. No agent maintains its own persistent state — the Twin is the canonical record of what exists, what constrains it, and how it evolved.

### Design Principles

1. **Graph-native**: Hardware designs are naturally graphs (components depend on each other, constraints span domains). A property graph captures this directly.
2. **Version-everything**: Every mutation creates a version record. The graph supports branching and merging like Git.
3. **Constraint-first**: Constraints are first-class nodes, not annotations. They are evaluated automatically on every proposed change.
4. **Domain-agnostic core**: The Twin schema is generic. Domain-specific semantics live in artifact metadata and constraint expressions.

---

## 2. Node Types

### 2.1 Artifact

An Artifact represents any design output: a schematic, BOM, PCB layout, firmware source file, test plan, simulation result, or manufacturing file.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `str (UUID)` | Yes | Unique identifier |
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
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: ArtifactType
    domain: str
    file_path: str
    content_hash: str
    format: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
```

### 2.2 Constraint

A Constraint is a rule that must be satisfied across one or more artifacts. Constraints are first-class graph nodes evaluated by the Constraint Engine.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `str (UUID)` | Yes | Unique identifier |
| `name` | `str` | Yes | Human-readable name (e.g., `"max_voltage_3v3"`) |
| `expression` | `str` | Yes | Constraint expression (see Constraint Language below) |
| `severity` | `ConstraintSeverity` | Yes | `ERROR`, `WARNING`, or `INFO` |
| `status` | `ConstraintStatus` | Yes | Current evaluation status |
| `domain` | `str` | Yes | Primary domain (e.g., `"electronics"`) |
| `cross_domain` | `bool` | No | Whether constraint spans multiple domains |
| `source` | `str` | Yes | Origin: `"user"`, `"agent"`, or `"system"` |
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

class Constraint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
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

### 2.3 Version

A Version represents a point-in-time snapshot of the artifact graph. Versions form a DAG (directed acyclic graph) that supports branching and merging.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `str (UUID)` | Yes | Unique identifier |
| `branch_name` | `str` | Yes | Branch this version belongs to (e.g., `"main"`, `"agent/mechanical/stress-fix"`) |
| `parent_id` | `str (UUID)` | No | Parent version (null for initial version) |
| `merge_parent_id` | `str (UUID)` | No | Second parent (for merge commits) |
| `commit_message` | `str` | Yes | Description of changes |
| `snapshot_hash` | `str` | Yes | Hash of the complete graph state at this version |
| `author` | `str` | Yes | Agent ID, `"human"`, or `"system"` |
| `created_at` | `datetime` | Yes | Version creation timestamp |
| `artifact_ids` | `list[UUID]` | Yes | Artifacts modified in this version |

```python
class Version(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    branch_name: str
    parent_id: UUID | None = None
    merge_parent_id: UUID | None = None
    commit_message: str
    snapshot_hash: str
    author: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    artifact_ids: list[UUID] = Field(default_factory=list)
```

### 2.4 Component

A Component represents a physical part used in the design (IC, resistor, connector, etc.) with supply chain metadata.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `str (UUID)` | Yes | Unique identifier |
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

class Component(BaseModel):
    id: UUID = Field(default_factory=uuid4)
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

### 2.5 Agent

An Agent node records which agent produced or modified artifacts. It connects the provenance chain from human intent through agent execution to artifact output.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `str (UUID)` | Yes | Unique identifier |
| `agent_type` | `str` | Yes | Agent discipline (e.g., `"mechanical"`, `"electronics"`) |
| `domain` | `str` | Yes | Engineering domain this agent covers |
| `session_id` | `str (UUID)` | Yes | Current execution session |
| `skills_used` | `list[str]` | No | Skill IDs invoked during this session |
| `started_at` | `datetime` | Yes | Session start time |
| `completed_at` | `datetime` | No | Session completion time |
| `status` | `str` | Yes | `"running"`, `"completed"`, `"failed"` |

```python
class AgentNode(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_type: str
    domain: str
    session_id: UUID
    skills_used: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str = "running"
```

---

## 3. Edge Types

Edges are directed relationships between nodes. Each edge type has defined source and target node types.

| Edge Type | Source → Target | Description |
|-----------|----------------|-------------|
| `DEPENDS_ON` | Artifact → Artifact | Artifact A requires Artifact B (e.g., PCB depends on schematic) |
| `IMPLEMENTS` | Artifact → Artifact | Artifact A implements the spec defined in Artifact B |
| `VALIDATES` | Artifact → Artifact | Artifact A (test result) validates Artifact B (design) |
| `CONTAINS` | Artifact → Artifact | Artifact A contains Artifact B (hierarchical composition) |
| `VERSIONED_BY` | Artifact → Version | Links an artifact to the version that last modified it |
| `CONSTRAINED_BY` | Artifact → Constraint | Constraint applies to this artifact |
| `PRODUCED_BY` | Artifact → Agent | Artifact was produced or modified by this agent |
| `USES_COMPONENT` | Artifact → Component | Artifact references this component (e.g., BOM uses resistor) |
| `PARENT_OF` | Version → Version | Version lineage (parent → child) |
| `CONFLICTS_WITH` | Constraint → Constraint | Two constraints that cannot both be satisfied |

### Edge Properties

All edges carry a minimal set of properties:

```python
class EdgeBase(BaseModel):
    source_id: UUID
    target_id: UUID
    edge_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
```

Some edge types have additional properties:

| Edge Type | Additional Properties |
|-----------|----------------------|
| `DEPENDS_ON` | `dependency_type: str` (`"hard"` or `"soft"`), `description: str` |
| `USES_COMPONENT` | `reference_designator: str` (e.g., `"R1"`, `"U3"`), `quantity: int` |
| `CONSTRAINED_BY` | `scope: str` (`"local"` or `"global"`), `priority: int` |

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
    @abstractmethod
    async def create_branch(self, name: str, from_version: UUID | None = None) -> str:
        """Create a new branch from the given version (or HEAD of main)."""
        ...

    @abstractmethod
    async def commit(
        self, branch: str, message: str, artifact_ids: list[UUID], author: str
    ) -> Version:
        """Create a new version on the given branch."""
        ...

    @abstractmethod
    async def merge(
        self, source_branch: str, target_branch: str, message: str, author: str
    ) -> Version:
        """Merge source branch into target branch. Raises on conflict."""
        ...

    @abstractmethod
    async def diff(self, version_a: UUID, version_b: UUID) -> "VersionDiff":
        """Compute the diff between two versions."""
        ...

    @abstractmethod
    async def log(self, branch: str, limit: int = 50) -> list[Version]:
        """Return version history for a branch."""
        ...

    @abstractmethod
    async def get_head(self, branch: str) -> Version:
        """Get the latest version on a branch."""
        ...
```

### Version Diff

```python
class ArtifactChange(BaseModel):
    artifact_id: UUID
    change_type: str  # "added", "modified", "deleted"
    old_content_hash: str | None = None
    new_content_hash: str | None = None

class VersionDiff(BaseModel):
    version_a: UUID
    version_b: UUID
    changes: list[ArtifactChange]
    constraints_added: list[UUID] = Field(default_factory=list)
    constraints_removed: list[UUID] = Field(default_factory=list)
```

### Conflict Detection

When merging branches, the Twin detects conflicts by comparing artifact content hashes:

1. **No conflict**: Only one branch modified the artifact.
2. **Content conflict**: Both branches modified the same artifact with different content hashes.
3. **Structural conflict**: One branch deleted an artifact that the other branch depends on.

Conflicts must be resolved manually (by a human or an agent with explicit instructions). Auto-merge is only performed for non-conflicting changes.

---

## 5. Constraint Engine

The Constraint Engine evaluates rules against the current graph state. It runs automatically on every proposed commit.

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

### Constraint Evaluation Context

```python
class ConstraintContext(BaseModel):
    """Provided to constraint expressions during evaluation."""

    class Config:
        arbitrary_types_allowed = True

    def artifact(self, name: str) -> Artifact:
        """Retrieve an artifact by name from the current graph state."""
        ...

    def artifacts(self, domain: str | None = None, type: ArtifactType | None = None) -> list[Artifact]:
        """Query artifacts by domain and/or type."""
        ...

    def components(self) -> list[Component]:
        """Retrieve all components in the current design."""
        ...

    def dependents(self, artifact_id: UUID) -> list[Artifact]:
        """Get all artifacts that depend on the given artifact."""
        ...
```

### Evaluation Lifecycle

```
Proposed commit arrives
        │
        ▼
  Load all constraints linked to modified artifacts
        │
        ▼
  Expand to cross-domain constraints (via CONSTRAINED_BY edges)
        │
        ▼
  Evaluate each constraint expression against graph state
        │
        ▼
  Collect results: PASS / FAIL / WARN
        │
        ▼
  Any ERROR-severity FAIL?
   ├── Yes → Block commit, return violations
   └── No → Allow commit (warnings logged)
```

### Constraint Evaluation Result

```python
class ConstraintViolation(BaseModel):
    constraint_id: UUID
    constraint_name: str
    severity: ConstraintSeverity
    message: str
    artifact_ids: list[UUID]  # Artifacts involved in the violation
    expression: str
    evaluated_at: datetime

class ConstraintEvaluationResult(BaseModel):
    passed: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)
    warnings: list[ConstraintViolation] = Field(default_factory=list)
    evaluated_count: int
    skipped_count: int
    duration_ms: float
```

---

## 6. Twin API

The Twin API is the public interface for all graph operations. Agents, the orchestrator, and the gateway interact with the Twin exclusively through this API.

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
    async def add_edge(self, source_id: UUID, target_id: UUID, edge_type: str, metadata: dict | None = None) -> EdgeBase:
        ...

    @abstractmethod
    async def get_edges(self, node_id: UUID, direction: str = "outgoing", edge_type: str | None = None) -> list[EdgeBase]:
        ...

    @abstractmethod
    async def remove_edge(self, source_id: UUID, target_id: UUID, edge_type: str) -> bool:
        ...

    # --- Queries ---
    @abstractmethod
    async def get_subgraph(self, root_id: UUID, depth: int = 2, edge_types: list[str] | None = None) -> "SubGraph":
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

### SubGraph Response

```python
class SubGraph(BaseModel):
    nodes: list[Artifact | Constraint | Component | AgentNode]
    edges: list[EdgeBase]
    root_id: UUID
    depth: int
```

---

## 7. Neo4j Implementation

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
