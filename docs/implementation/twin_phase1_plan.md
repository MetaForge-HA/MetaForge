# Digital Twin Phase 1 Implementation Plan

> **Epic**: MET-5 - Digital Twin Core
> **Phase**: Phase 1 (v0.1-0.3)
> **Status**: Planning
> **Timeline**: 6-8 weeks
> **Last Updated**: 2026-03-02

---

## Executive Summary

This document outlines the detailed implementation plan for the **Digital Twin Core**, the foundational component of MetaForge. The Digital Twin is a versioned property graph stored in Neo4j that serves as the single source of design truth for all hardware artifacts, constraints, relationships, and version history.

**Current Status**: All scaffolding is in place, but implementation is at 0%. All 12 core files are empty.

**Goal**: Deliver a fully functional Digital Twin that supports the mechanical vertical (MET-8) and provides the foundation for all future agent integrations.

---

## Table of Contents

1. [Scope & Objectives](#scope--objectives)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Phases](#implementation-phases)
4. [Detailed Component Breakdown](#detailed-component-breakdown)
5. [Dependencies & Setup](#dependencies--setup)
6. [Testing Strategy](#testing-strategy)
7. [Success Criteria](#success-criteria)
8. [Timeline & Milestones](#timeline--milestones)
9. [Risk Assessment](#risk-assessment)
10. [References](#references)

---

## Scope & Objectives

### What We're Building

A complete graph-based design database with:

- **Artifact Management**: Store and version all design outputs (CAD, schematics, BOMs, firmware, etc.)
- **Constraint System**: First-class constraint nodes with automatic evaluation
- **Version Control**: Git-like branching, merging, and diff operations
- **Relationship Tracking**: Explicit dependencies between artifacts
- **Component Library**: Supply chain metadata for parts used in designs
- **Agent Provenance**: Track which agent produced which artifacts

### What We're NOT Building (Out of Scope)

- File storage backend (artifacts reference files on disk; Twin stores metadata only)
- Tool integrations (that's MCP layer - separate epic)
- Agent orchestration (that's the Orchestrator - separate epic)
- User authentication (that's Gateway - separate epic)
- Frontend/UI (Phase 2+)

### Phase 1 Subset for MET-8 (Mechanical Vertical)

The first end-to-end test will use:

- **Node Types**: Artifact (CAD_MODEL, SIMULATION_RESULT), Constraint, Version, Component, Agent
- **Edge Types**: DEPENDS_ON, CONSTRAINED_BY, PRODUCED_BY, VERSIONED_BY, USES_COMPONENT

Full schema support is required, but MET-8 will validate this subset works end-to-end.

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Twin API                           │
│  (Public interface - all operations go through here)    │
└────────────┬─────────────────────────────┬──────────────┘
             │                             │
      ┌──────▼────────┐            ┌──────▼──────────┐
      │ Graph Engine  │            │ Constraint Eng  │
      │  (Neo4j CRUD) │            │  (Validator)    │
      └──────┬────────┘            └──────┬──────────┘
             │                             │
      ┌──────▼────────┐            ┌──────▼──────────┐
      │  Versioning   │            │ Validation Eng  │
      │ (Branch/Merge)│            │ (Schema Check)  │
      └───────────────┘            └─────────────────┘
             │
      ┌──────▼────────┐
      │    Neo4j      │
      │   Database    │
      └───────────────┘
```

### Data Flow for Agent Operations

```
1. Agent proposes change (e.g., "add CAD model artifact")
        ↓
2. Twin API validates request schema
        ↓
3. Validation Engine checks artifact schema
        ↓
4. Graph Engine writes to branch (not main)
        ↓
5. Constraint Engine evaluates all affected constraints
        ↓
6. If PASS: allow commit; if FAIL: reject with violations
        ↓
7. Human reviews on branch
        ↓
8. Merge to main (with conflict detection)
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Core data models and infrastructure

- Set up development environment (Neo4j, Python deps)
- Implement all 6 Pydantic model files
- Create module structure with `__init__.py` files
- Write unit tests for models
- Set up Neo4j connection and schema initialization

**Deliverable**: Models can be instantiated, validated, and serialized

---

### Phase 2: Graph Engine (Week 2-3)

**Goal**: CRUD operations for all node/edge types

- Neo4j driver integration with connection pooling
- Create indexes and constraints (Section 7 of twin_schema.md)
- Implement node operations (create, read, update, delete)
- Implement edge operations (add, remove, query)
- Implement subgraph extraction and Cypher queries
- Write integration tests against local Neo4j instance

**Deliverable**: Can store and retrieve artifacts, constraints, versions, components, agents with relationships

---

### Phase 3: Validation & Constraints (Week 3-4)

**Goal**: Enforce rules and schemas

- Implement schema validator for artifacts
- Implement constraint expression evaluator with ConstraintContext
- Implement constraint resolver (conflict detection, cross-domain propagation)
- Create sandboxed Python expression evaluation environment
- Write unit tests for constraint expressions
- Write integration tests for constraint evaluation pipeline

**Deliverable**: Constraints can be evaluated on every commit and block invalid changes

---

### Phase 4: Versioning (Week 4-5)

**Goal**: Git-like version control

- Implement branch operations (create, list, get_head, log)
- Implement commit operation (create version, snapshot hash)
- Implement diff computation (added/modified/deleted artifacts)
- Implement merge logic with conflict detection (content + structural conflicts)
- Write integration tests for full branch/commit/merge cycle

**Deliverable**: Can create branches, commit changes, compute diffs, merge branches with conflict detection

---

### Phase 5: Twin API (Week 5-6)

**Goal**: Unified public interface

- Implement TwinAPI abstract base class
- Implement Neo4jTwinAPI concrete class
- Wire up all operations (artifacts, constraints, components, edges, queries, versioning)
- Add transaction management and error handling
- Write integration tests for complete API contract

**Deliverable**: All graph operations go through Twin API, ready for agent integration

---

### Phase 6: Testing & Validation (Week 6-8)

**Goal**: Production-ready quality

- Complete unit test suite (>90% coverage)
- Complete integration test suite (all workflows)
- Write e2e test simulating MET-8 mechanical vertical
- Performance testing (query latency, concurrent operations)
- Documentation review and updates
- Security review (constraint expression sandboxing)

**Deliverable**: Production-ready Twin Core with comprehensive test coverage

---

## Detailed Component Breakdown

### 1. Models (`twin_core/models/`)

#### 1.1 `models/artifact.py`

**Implementation Steps**:

1. Define `ArtifactType` enum (14 values from spec)
2. Create `Artifact` Pydantic model with:
   - UUID generation for `id` field
   - Auto-populated timestamps (`created_at`, `updated_at`)
   - SHA-256 hash validation for `content_hash`
   - File path validation
3. Add model validators:
   - `@field_validator` for `file_path` (must be relative, no `..`)
   - `@field_validator` for `format` (must match known formats)
4. Add helper methods:
   - `compute_content_hash(file_path: str) -> str`
   - `to_neo4j_props() -> dict` (serialize for Neo4j)
   - `from_neo4j_props(props: dict) -> Artifact` (deserialize)

**Test Cases**:
- Valid artifact creation with all fields
- Auto-generated UUID and timestamps
- Invalid file paths rejected
- Content hash validation
- Serialization round-trip (Pydantic → Neo4j → Pydantic)

**Lines of Code**: ~100

---

#### 1.2 `models/constraint.py`

**Implementation Steps**:

1. Define `ConstraintSeverity` and `ConstraintStatus` enums
2. Create `Constraint` Pydantic model
3. Create `ConstraintContext` model with methods:
   - `artifact(name: str) -> Artifact`
   - `artifacts(domain: str | None, type: ArtifactType | None) -> list[Artifact]`
   - `components() -> list[Component]`
   - `dependents(artifact_id: UUID) -> list[Artifact]`
   - (Note: actual graph queries will be injected by constraint engine)
4. Create `ConstraintViolation` model
5. Create `ConstraintEvaluationResult` model

**Test Cases**:
- Constraint model validation
- Expression string format validation
- Severity and status enum values
- ConstraintContext method signatures
- Violation result serialization

**Lines of Code**: ~150

---

#### 1.3 `models/version.py`

**Implementation Steps**:

1. Create `Version` Pydantic model
2. Create `ArtifactChange` model (for diffs)
3. Create `VersionDiff` model
4. Add validators:
   - Branch name format validation (`main`, `agent/<domain>/<task>`, `review/<id>`)
   - Parent ID consistency (merge commits must have two parents)
5. Add helper methods:
   - `is_merge_commit() -> bool`
   - `compute_snapshot_hash(artifact_hashes: list[str]) -> str`

**Test Cases**:
- Version creation with single parent
- Merge commit with two parents
- Branch name validation
- Snapshot hash computation
- Diff computation logic

**Lines of Code**: ~120

---

#### 1.4 `models/relationship.py`

**Implementation Steps**:

1. Define edge type constants or enum (10 edge types)
2. Create `EdgeBase` Pydantic model
3. Create specialized edge models:
   - `DependsOnEdge(EdgeBase)` with `dependency_type` and `description`
   - `UsesComponentEdge(EdgeBase)` with `reference_designator` and `quantity`
   - `ConstrainedByEdge(EdgeBase)` with `scope` and `priority`
4. Add serialization helpers

**Test Cases**:
- Base edge creation
- Specialized edge creation with additional properties
- Edge type validation
- Bidirectional relationship consistency

**Lines of Code**: ~100

---

#### 1.5 `models/component.py` (NEW FILE)

**Implementation Steps**:

1. Define `ComponentLifecycle` enum (ACTIVE, NRND, EOL, OBSOLETE, UNKNOWN)
2. Create `Component` Pydantic model per spec Section 2.4
3. Add validators for part numbers, manufacturer names
4. Add cost calculation helpers

**Test Cases**:
- Component creation with full specs
- Lifecycle status validation
- Cost and lead time calculations
- Alternate parts list management

**Lines of Code**: ~80

---

#### 1.6 `models/agent.py` (NEW FILE)

**Implementation Steps**:

1. Create `AgentNode` Pydantic model per spec Section 2.5
2. Add session lifecycle helpers (start, complete, fail)
3. Add skill tracking

**Test Cases**:
- Agent session creation
- Status transitions
- Skill usage tracking

**Lines of Code**: ~60

---

#### 1.7 `models/__init__.py` (NEW FILE)

**Implementation Steps**:

Export all models and enums for clean imports:

```python
from .artifact import Artifact, ArtifactType
from .constraint import (
    Constraint, ConstraintSeverity, ConstraintStatus,
    ConstraintContext, ConstraintViolation, ConstraintEvaluationResult
)
from .version import Version, ArtifactChange, VersionDiff
from .relationship import EdgeBase, DependsOnEdge, UsesComponentEdge, ConstrainedByEdge
from .component import Component, ComponentLifecycle
from .agent import AgentNode

__all__ = [
    "Artifact", "ArtifactType",
    "Constraint", "ConstraintSeverity", "ConstraintStatus",
    "ConstraintContext", "ConstraintViolation", "ConstraintEvaluationResult",
    "Version", "ArtifactChange", "VersionDiff",
    "EdgeBase", "DependsOnEdge", "UsesComponentEdge", "ConstrainedByEdge",
    "Component", "ComponentLifecycle",
    "AgentNode",
]
```

**Lines of Code**: ~30

---

### 2. Graph Engine (`twin_core/graph_engine.py`)

**Implementation Steps**:

1. **Neo4j Connection Management**:
   - Connection pool with configurable URI, auth
   - Session management (read vs write transactions)
   - Retry logic for transient failures
   - Health check endpoint

2. **Schema Initialization** (run once on startup):
   - Create all constraints (5 unique ID constraints from spec Section 7)
   - Create all indexes (8 lookup indexes from spec Section 7)
   - Idempotent (safe to run multiple times)

3. **Node CRUD Operations**:
   ```python
   async def create_node(node_type: str, properties: dict) -> UUID
   async def get_node(node_id: UUID, node_type: str) -> dict | None
   async def update_node(node_id: UUID, node_type: str, updates: dict) -> dict
   async def delete_node(node_id: UUID, node_type: str) -> bool
   async def list_nodes(node_type: str, filters: dict) -> list[dict]
   ```

4. **Edge CRUD Operations**:
   ```python
   async def create_edge(source_id: UUID, target_id: UUID, edge_type: str, props: dict) -> EdgeBase
   async def get_edges(node_id: UUID, direction: str, edge_type: str | None) -> list[EdgeBase]
   async def delete_edge(source_id: UUID, target_id: UUID, edge_type: str) -> bool
   ```

5. **Query Operations**:
   ```python
   async def get_subgraph(root_id: UUID, depth: int, edge_types: list[str] | None) -> SubGraph
   async def query_cypher(query: str, params: dict | None) -> list[dict]
   ```

6. **Batch Operations** (for performance):
   ```python
   async def create_nodes_batch(nodes: list[tuple[str, dict]]) -> list[UUID]
   async def create_edges_batch(edges: list[tuple[UUID, UUID, str, dict]]) -> list[EdgeBase]
   ```

**Test Cases**:
- Connection pool lifecycle
- Schema initialization idempotency
- CRUD for all node types (Artifact, Constraint, Version, Component, Agent)
- CRUD for all edge types
- Subgraph extraction at various depths
- Raw Cypher query execution
- Batch operations performance
- Transaction rollback on error
- Concurrent operations

**Lines of Code**: ~600-800

---

### 3. Constraint Engine (`twin_core/constraint_engine/`)

#### 3.1 `constraint_engine/validator.py`

**Implementation Steps**:

1. **Expression Evaluator**:
   ```python
   class ConstraintExpressionEvaluator:
       def __init__(self, safe_builtins: dict):
           # Sandboxed eval environment (no __import__, no file I/O, etc.)
           self.safe_globals = {"__builtins__": safe_builtins}

       def evaluate(self, expression: str, context: ConstraintContext) -> bool:
           # Inject context as 'ctx' variable
           # Evaluate expression safely
           # Return boolean result
   ```

2. **Constraint Context Implementation**:
   ```python
   class ConstraintContextImpl(ConstraintContext):
       def __init__(self, graph_engine: GraphEngine, branch: str):
           self.graph = graph_engine
           self.branch = branch

       def artifact(self, name: str) -> Artifact:
           # Query graph for artifact by name on current branch

       def artifacts(self, domain: str | None, type: ArtifactType | None) -> list[Artifact]:
           # Query graph with filters

       def components(self) -> list[Component]:
           # Query all components

       def dependents(self, artifact_id: UUID) -> list[Artifact]:
           # Follow DEPENDS_ON edges backward
   ```

3. **Constraint Evaluation Pipeline**:
   ```python
   async def evaluate_constraints_for_commit(
       branch: str,
       modified_artifact_ids: list[UUID]
   ) -> ConstraintEvaluationResult:
       # 1. Load constraints linked to modified artifacts
       # 2. Expand to cross-domain constraints
       # 3. Evaluate each expression
       # 4. Collect PASS/FAIL/WARN results
       # 5. Return evaluation result
   ```

**Test Cases**:
- Safe expression evaluation (no dangerous operations)
- ConstraintContext queries against test graph
- Simple constraint expressions (arithmetic, comparisons)
- Complex constraints (all(), any(), loops)
- Cross-domain constraint propagation
- Performance test (1000 constraints)

**Lines of Code**: ~400

---

#### 3.2 `constraint_engine/resolver.py`

**Implementation Steps**:

1. **Conflict Detection**:
   ```python
   async def find_conflicting_constraints(
       constraint_ids: list[UUID]
   ) -> list[tuple[UUID, UUID]]:
       # Query for CONFLICTS_WITH edges between constraints
       # Return pairs of conflicting constraint IDs
   ```

2. **Priority Resolution**:
   ```python
   def resolve_constraint_priority(
       constraints: list[Constraint]
   ) -> list[Constraint]:
       # Sort by priority (from edge metadata)
       # Higher priority constraints evaluated first
   ```

3. **Cross-Domain Propagation**:
   ```python
   async def expand_to_cross_domain_constraints(
       artifact_ids: list[UUID]
   ) -> list[UUID]:
       # Find all constraints with cross_domain=True
       # That transitively constrain the given artifacts
   ```

**Test Cases**:
- Conflicting constraint detection
- Priority-based ordering
- Cross-domain constraint expansion
- Transitive dependency resolution

**Lines of Code**: ~200

---

### 4. Validation Engine (`twin_core/validation_engine/`)

#### 4.1 `validation_engine/schema_validator.py`

**Implementation Steps**:

1. **Artifact Schema Validation**:
   ```python
   class ArtifactSchemaValidator:
       def validate_artifact(self, artifact: Artifact) -> ValidationResult:
           # Check that artifact conforms to ArtifactType expectations
           # E.g., BOM must have metadata.total_cost, metadata.components
           # E.g., CAD_MODEL must have format in ["step", "stl", "obj"]
   ```

2. **Metadata Schema Validation**:
   ```python
   def validate_metadata(self, artifact_type: ArtifactType, metadata: dict) -> ValidationResult:
       # Load JSON schema for artifact type
       # Validate metadata against schema
   ```

3. **Content Hash Verification**:
   ```python
   def verify_content_hash(self, file_path: str, expected_hash: str) -> bool:
       # Compute SHA-256 of file
       # Compare to expected hash
   ```

4. **File Format Validation**:
   ```python
   def validate_file_format(self, file_path: str, expected_format: str) -> ValidationResult:
       # Basic file extension check
       # Optional: magic number validation for common formats
   ```

**Test Cases**:
- Valid artifact schemas for each ArtifactType
- Invalid metadata rejected
- Content hash mismatch detection
- File format validation

**Lines of Code**: ~300

---

#### 4.2 `validation_engine/schemas/` (NEW DIRECTORY)

**Implementation Steps**:

Create JSON schemas for common artifact types:

1. `bom_schema.json`:
   ```json
   {
     "type": "object",
     "required": ["total_cost", "components"],
     "properties": {
       "total_cost": {"type": "number", "minimum": 0},
       "components": {"type": "array"},
       "currency": {"type": "string", "default": "USD"}
     }
   }
   ```

2. `cad_model_schema.json`
3. `simulation_result_schema.json`
4. `pcb_layout_schema.json`

**Lines of Code**: ~200 (JSON)

---

### 5. Versioning (`twin_core/versioning/`)

#### 5.1 `versioning/branch.py`

**Implementation Steps**:

1. **Branch Operations**:
   ```python
   class BranchManager:
       def __init__(self, graph_engine: GraphEngine):
           self.graph = graph_engine

       async def create_branch(self, name: str, from_version: UUID | None) -> str:
           # Create new branch pointer
           # If from_version is None, use HEAD of main
           # Validate branch name format

       async def get_head(self, branch: str) -> Version:
           # Query for latest version on branch

       async def log(self, branch: str, limit: int) -> list[Version]:
           # Query version history for branch
           # Follow PARENT_OF edges backward

       async def list_branches(self) -> list[str]:
           # Return all active branch names

       async def delete_branch(self, name: str) -> bool:
           # Delete branch (versions remain in history)
   ```

**Test Cases**:
- Create branch from HEAD
- Create branch from specific version
- Branch name validation (must match patterns)
- Get HEAD of branch
- Log with limit
- List all branches
- Delete branch (idempotent)

**Lines of Code**: ~250

---

#### 5.2 `versioning/diff.py`

**Implementation Steps**:

1. **Diff Computation**:
   ```python
   class DiffEngine:
       async def diff(self, version_a: UUID, version_b: UUID) -> VersionDiff:
           # 1. Load artifact snapshots for both versions
           # 2. Compare content hashes
           # 3. Categorize as added/modified/deleted
           # 4. Diff constraints (added/removed)
           # 5. Return VersionDiff

       def _compute_artifact_changes(
           self, artifacts_a: list[Artifact], artifacts_b: list[Artifact]
       ) -> list[ArtifactChange]:
           # Set operations to find added, modified, deleted
   ```

**Test Cases**:
- No changes (same version)
- Added artifacts
- Modified artifacts (different content hash)
- Deleted artifacts
- Constraint changes
- Large diffs (performance test)

**Lines of Code**: ~200

---

#### 5.3 `versioning/merge.py`

**Implementation Steps**:

1. **Merge Logic**:
   ```python
   class MergeEngine:
       async def merge(
           self, source_branch: str, target_branch: str, message: str, author: str
       ) -> Version:
           # 1. Find merge base (common ancestor)
           # 2. Compute diffs: base→source, base→target
           # 3. Detect conflicts
           # 4. If conflicts: raise MergeConflictError
           # 5. If clean: apply changes, create merge commit

       async def _find_merge_base(self, version_a: UUID, version_b: UUID) -> UUID:
           # Graph traversal to find lowest common ancestor

       def _detect_conflicts(
           self, base_to_source: VersionDiff, base_to_target: VersionDiff
       ) -> list[MergeConflict]:
           # Content conflicts: same artifact modified differently
           # Structural conflicts: deleted artifact with new dependencies
   ```

2. **Conflict Types**:
   ```python
   class MergeConflict(BaseModel):
       conflict_type: str  # "content" or "structural"
       artifact_id: UUID
       source_hash: str | None
       target_hash: str | None
       description: str

   class MergeConflictError(Exception):
       conflicts: list[MergeConflict]
   ```

**Test Cases**:
- Clean merge (no conflicts)
- Content conflict (same file modified in both branches)
- Structural conflict (deleted artifact with dependencies)
- Merge base computation
- Merge commit creation (two parents)
- Auto-merge for non-overlapping changes

**Lines of Code**: ~350

---

### 6. Twin API (`twin_core/api.py`)

**Implementation Steps**:

1. **Abstract Base Class**:
   ```python
   from abc import ABC, abstractmethod

   class TwinAPI(ABC):
       # All 28 abstract methods from spec Section 6
       # (see spec for full list)
   ```

2. **Neo4j Implementation**:
   ```python
   class Neo4jTwinAPI(TwinAPI):
       def __init__(
           self,
           neo4j_uri: str,
           neo4j_user: str,
           neo4j_password: str
       ):
           self.graph = GraphEngine(neo4j_uri, neo4j_user, neo4j_password)
           self.constraint_engine = ConstraintValidator(self.graph)
           self.version_engine = VersionEngine(self.graph)
           self.validator = ArtifactSchemaValidator()

       # Implement all 28 methods, delegating to engines
   ```

3. **Transaction Management**:
   - Artifact create/update/delete wrapped in transactions
   - Rollback on constraint failures
   - Optimistic locking for concurrent updates

4. **Error Handling**:
   - Custom exceptions: `ArtifactNotFoundError`, `ConstraintViolationError`, `MergeConflictError`
   - Structured error responses with context

**Test Cases**:
- All 28 API methods tested individually
- Transaction rollback on error
- Concurrent updates to same artifact (optimistic locking)
- Error handling for all failure modes
- Full workflow tests (create → update → version → merge)

**Lines of Code**: ~800

---

### 7. Configuration & Infrastructure

#### 7.1 `twin_core/config.py` (NEW FILE)

**Implementation Steps**:

```python
from pydantic_settings import BaseSettings

class TwinCoreConfig(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    constraint_eval_timeout_ms: int = 5000
    max_subgraph_depth: int = 10

    class Config:
        env_file = ".env"
        env_prefix = "TWIN_"
```

**Lines of Code**: ~40

---

#### 7.2 `twin_core/__init__.py` (NEW FILE)

**Implementation Steps**:

```python
from .api import TwinAPI, Neo4jTwinAPI
from .models import (
    Artifact, ArtifactType,
    Constraint, ConstraintSeverity, ConstraintStatus,
    Version, VersionDiff,
    Component, ComponentLifecycle,
    AgentNode,
)

__version__ = "0.1.0"

__all__ = [
    "TwinAPI",
    "Neo4jTwinAPI",
    "Artifact",
    "ArtifactType",
    "Constraint",
    # ... all models
]
```

**Lines of Code**: ~50

---

## Dependencies & Setup

### Python Dependencies

Add to `pyproject.toml` or `requirements.txt`:

```toml
[project]
dependencies = [
    "pydantic>=2.0.0",
    "neo4j>=5.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.0.0",
    "opentelemetry-api>=1.20.0",
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
]
```

---

### Neo4j Setup

#### Option 1: Docker (Recommended for Development)

```bash
docker run -d \
  --name metaforge-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/metaforge \
  -v $PWD/data/neo4j:/data \
  neo4j:5.14-community
```

#### Option 2: Local Install

Download from https://neo4j.com/download/

#### Environment Variables

Create `.env`:

```bash
TWIN_NEO4J_URI=bolt://localhost:7687
TWIN_NEO4J_USER=neo4j
TWIN_NEO4J_PASSWORD=metaforge
```

---

### Development Setup Checklist

- [ ] Python 3.11+ installed
- [ ] Neo4j running (Docker or local)
- [ ] Dependencies installed (`pip install -e ".[dev]"`)
- [ ] `.env` file configured
- [ ] Neo4j accessible at `bolt://localhost:7687`
- [ ] Database initialized with schema (run `init_schema.py`)

---

## Testing Strategy

### Test Pyramid

```
           ┌─────────────┐
           │   E2E (5)   │  Full MET-8 mechanical vertical
           └─────────────┘
          ┌───────────────┐
          │ Integration   │  Graph + Versioning + Constraints
          │    (30)       │
          └───────────────┘
        ┌───────────────────┐
        │   Unit Tests      │  Models, validators, helpers
        │     (100+)        │
        └───────────────────┘
```

---

### Unit Tests (`tests/unit/twin_core/`)

**Files to Create**:

1. `test_models.py` - Pydantic model validation (~50 tests)
2. `test_constraint_expressions.py` - Expression evaluation (~20 tests)
3. `test_version_diff.py` - Diff computation (~15 tests)
4. `test_merge_conflicts.py` - Conflict detection (~15 tests)
5. `test_schema_validator.py` - Artifact schema validation (~10 tests)

**Coverage Target**: >90% for all model and utility code

---

### Integration Tests (`tests/integration/twin_core/`)

**Files to Create**:

1. `test_graph_operations.py` - Neo4j CRUD (~15 tests)
   - Create/read/update/delete for all node types
   - Edge operations
   - Subgraph queries
   - Batch operations

2. `test_constraint_evaluation.py` - Full constraint pipeline (~10 tests)
   - Simple constraints (pass/fail)
   - Cross-domain constraints
   - Constraint conflicts
   - Blocking on ERROR severity

3. `test_versioning_workflow.py` - Branch/commit/merge cycle (~10 tests)
   - Create branch → commit → merge
   - Merge conflicts
   - Diff between branches
   - Version history

4. `test_twin_api.py` - API contract compliance (~20 tests)
   - All 28 API methods
   - Transaction semantics
   - Error handling
   - Concurrent operations

**Setup**: Each test file uses a fresh Neo4j database (Docker testcontainers or separate test database)

**Coverage Target**: >85% for all integration code

---

### E2E Tests (`tests/e2e/`)

**File**: `test_mechanical_vertical.py`

**Scenario**: Simulate MET-8 mechanical agent workflow

1. Agent creates CAD_MODEL artifact
2. Agent creates SIMULATION_RESULT artifact with stress data
3. Agent links artifacts with DEPENDS_ON edge
4. Agent creates constraint: "Max stress < 500 MPa"
5. System evaluates constraint (PASS)
6. Agent commits to branch `agent/mechanical/stress-validation`
7. Human reviews on branch
8. System merges to `main`
9. Verify version history is correct
10. Verify constraint status is tracked

**Coverage**: Full Twin API surface used in realistic workflow

**Runtime**: <30 seconds

---

### Test Infrastructure

#### Fixtures (`tests/conftest.py`)

```python
import pytest
from neo4j import GraphDatabase
from twin_core.api import Neo4jTwinAPI

@pytest.fixture(scope="session")
def neo4j_test_db():
    # Start Neo4j test container or use test database
    # Yield connection details
    # Cleanup after tests

@pytest.fixture
def twin_api(neo4j_test_db):
    api = Neo4jTwinAPI(
        neo4j_uri=neo4j_test_db["uri"],
        neo4j_user=neo4j_test_db["user"],
        neo4j_password=neo4j_test_db["password"],
    )
    # Initialize schema
    api.graph.init_schema()
    yield api
    # Clear database
    api.graph.clear_all()

@pytest.fixture
def sample_artifact():
    return Artifact(
        name="test_cad_model",
        type=ArtifactType.CAD_MODEL,
        domain="mechanical",
        file_path="models/test.step",
        content_hash="abcd1234...",
        format="step",
        created_by="test_agent",
    )
```

#### Test Helpers (`tests/helpers.py`)

```python
def create_test_graph(api: TwinAPI) -> dict:
    """Create a small test graph with artifacts, constraints, versions."""
    # Helper to set up common test scenarios

def assert_constraint_passes(api: TwinAPI, constraint_id: UUID):
    """Assert a constraint evaluates to PASS."""

def assert_merge_clean(api: TwinAPI, source: str, target: str):
    """Assert merge has no conflicts."""
```

---

## Success Criteria

### Functional Requirements

- [ ] All 6 Pydantic models implemented and validated
- [ ] Graph Engine supports CRUD for all Phase 1 node/edge types
- [ ] Constraint Engine evaluates expressions and blocks on ERROR violations
- [ ] Versioning supports branch, commit, merge, diff, log
- [ ] Twin API implements all 28 methods from spec
- [ ] Neo4j schema initialized with all indexes and constraints
- [ ] E2E test for MET-8 mechanical vertical passes

### Quality Requirements

- [ ] >90% unit test coverage
- [ ] >85% integration test coverage
- [ ] All tests pass on CI/CD
- [ ] Type checking passes (`mypy .`)
- [ ] Linting passes (`ruff check .`)
- [ ] Documentation complete (docstrings, README, architecture docs)

### Performance Requirements

- [ ] Artifact CRUD operations < 50ms (p95)
- [ ] Constraint evaluation for 100 constraints < 500ms
- [ ] Subgraph query (depth 5) < 200ms
- [ ] Diff computation for 1000 artifacts < 1s
- [ ] Merge with conflict detection < 500ms

### Security Requirements

- [ ] Constraint expression evaluation sandboxed (no file I/O, no imports)
- [ ] SQL injection prevented (parameterized Cypher queries)
- [ ] No sensitive data logged (passwords, tokens)

---

## Timeline & Milestones

### Week 1: Foundation
- **Days 1-2**: Environment setup, Neo4j running, dependencies installed
- **Days 3-4**: Implement all 6 model files with unit tests
- **Day 5**: Model integration tests, refine based on validation errors

**Milestone**: Models can be instantiated and serialized

---

### Week 2: Graph Engine Part 1
- **Days 1-2**: Neo4j connection, schema initialization
- **Days 3-4**: Node CRUD operations (Artifact, Constraint, Version)
- **Day 5**: Integration tests for node operations

**Milestone**: Can create and query artifacts in Neo4j

---

### Week 3: Graph Engine Part 2 + Validation
- **Days 1-2**: Edge CRUD, subgraph queries
- **Day 3**: Implement schema validator
- **Days 4-5**: Integration tests for full graph operations

**Milestone**: Can create artifact graphs with relationships

---

### Week 4: Constraint Engine
- **Days 1-2**: Expression evaluator with ConstraintContext
- **Day 3**: Constraint resolver (conflicts, cross-domain)
- **Days 4-5**: Constraint evaluation pipeline with tests

**Milestone**: Constraints can be evaluated on commits

---

### Week 5: Versioning
- **Days 1-2**: Branch operations (create, get_head, log)
- **Day 3**: Diff computation
- **Days 4-5**: Merge logic with conflict detection

**Milestone**: Full Git-like version control works

---

### Week 6: Twin API
- **Days 1-2**: TwinAPI abstract class and Neo4jTwinAPI implementation
- **Day 3**: Transaction management and error handling
- **Days 4-5**: Complete API integration tests

**Milestone**: Twin API is the only interface to the graph

---

### Week 7: Testing & Refinement
- **Days 1-2**: Complete unit test suite (fill gaps)
- **Day 3**: E2E test for MET-8
- **Days 4-5**: Performance testing and optimization

**Milestone**: >90% test coverage, all tests passing

---

### Week 8: Documentation & Handoff
- **Days 1-2**: Write comprehensive README and architecture docs
- **Day 3**: Security review (constraint sandboxing)
- **Days 4-5**: Final integration testing, bug fixes

**Milestone**: Production-ready Twin Core

---

## Risk Assessment

### High-Risk Items

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Constraint expression evaluation security** | CRITICAL | Implement strict sandboxing with whitelist of allowed builtins. Security audit before production. |
| **Merge conflict complexity** | HIGH | Start with simple cases, add edge cases iteratively. Extensive test coverage. |
| **Neo4j performance at scale** | MEDIUM | Use indexes aggressively. Benchmark early. Consider caching for read-heavy operations. |
| **Concurrent write conflicts** | MEDIUM | Implement optimistic locking. Clear error messages for users. |

---

### Medium-Risk Items

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Version graph complexity (DAG traversal)** | MEDIUM | Use Neo4j's built-in graph algorithms. Limit traversal depth. |
| **Constraint expression debugging** | MEDIUM | Provide detailed error messages with expression context. |
| **Test data generation** | LOW | Create fixtures and helpers early. Reuse across tests. |

---

## References

### Specifications

- **Twin Schema**: `/Users/dee_vyn/Documents/metaforge/MetaForge/docs/twin_schema.md`
- **Architecture**: `MetaForge-Planner/docs/architecture/architecture.md`
- **Constraint Engine**: `MetaForge-Planner/docs/architecture/constraint-engine.md`
- **Roadmap**: `/Users/dee_vyn/Documents/metaforge/MetaForge/docs/roadmap.md`

### External Documentation

- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/current/
- **Pydantic v2**: https://docs.pydantic.dev/latest/
- **PydanticAI**: https://ai.pydantic.dev/

### Related Epics

- **MET-5**: Digital Twin Core (THIS EPIC)
- **MET-6**: Skill System (depends on MET-5)
- **MET-7**: MCP Infrastructure (parallel to MET-5)
- **MET-8**: Mechanical Agent (depends on MET-5, MET-6, MET-7)

---

## Appendix A: File Checklist

### Files to Create (20 files)

#### Models (7 files)
- [ ] `twin_core/models/__init__.py`
- [ ] `twin_core/models/artifact.py`
- [ ] `twin_core/models/constraint.py`
- [ ] `twin_core/models/version.py`
- [ ] `twin_core/models/relationship.py`
- [ ] `twin_core/models/component.py`
- [ ] `twin_core/models/agent.py`

#### Core (3 files)
- [ ] `twin_core/__init__.py`
- [ ] `twin_core/config.py`
- [ ] `twin_core/graph_engine.py`

#### Constraint Engine (2 files)
- [ ] `twin_core/constraint_engine/validator.py`
- [ ] `twin_core/constraint_engine/resolver.py`

#### Validation Engine (1 file + schemas)
- [ ] `twin_core/validation_engine/schema_validator.py`
- [ ] `twin_core/validation_engine/schemas/bom_schema.json`
- [ ] `twin_core/validation_engine/schemas/cad_model_schema.json`

#### Versioning (3 files)
- [ ] `twin_core/versioning/branch.py`
- [ ] `twin_core/versioning/diff.py`
- [ ] `twin_core/versioning/merge.py`

#### API (1 file)
- [ ] `twin_core/api.py`

#### Infrastructure (2 files)
- [ ] `twin_core/init_schema.py` (Neo4j schema initialization script)
- [ ] `twin_core/exceptions.py` (Custom exception classes)

---

## Appendix B: Lines of Code Estimate

| Component | Estimated LOC |
|-----------|--------------|
| Models (7 files) | 640 |
| Graph Engine | 700 |
| Constraint Engine | 600 |
| Validation Engine | 300 |
| Versioning | 800 |
| Twin API | 800 |
| Config & Init | 200 |
| **Total Implementation** | **4,040** |
| Unit Tests | 2,000 |
| Integration Tests | 1,500 |
| E2E Tests | 300 |
| **Total with Tests** | **7,840** |

---

## Appendix C: Example Workflows

### Workflow 1: Agent Creates Artifact

```python
# Agent (mechanical) creates CAD model artifact
api = Neo4jTwinAPI(...)

# Create artifact on agent branch
branch = "agent/mechanical/chassis-design"
await api.create_branch(branch, from_branch="main")

artifact = Artifact(
    name="chassis_v1",
    type=ArtifactType.CAD_MODEL,
    domain="mechanical",
    file_path="models/chassis.step",
    content_hash=compute_hash("models/chassis.step"),
    format="step",
    created_by="agent_mechanical_001",
)

created = await api.create_artifact(artifact, branch=branch)

# Commit to branch
version = await api.commit(
    branch=branch,
    message="Add initial chassis CAD model",
    author="agent_mechanical_001"
)

# Human reviews and merges to main
merge_version = await api.merge(
    source=branch,
    target="main",
    message="Merge chassis design",
    author="human"
)
```

---

### Workflow 2: Constraint Evaluation Blocks Invalid Change

```python
# Create constraint: BOM cost must be under $50
constraint = Constraint(
    name="max_bom_cost",
    expression="ctx.artifact('bom').metadata.get('total_cost', 0) < 50.0",
    severity=ConstraintSeverity.ERROR,
    domain="electronics",
    source="user",
    message="BOM cost must stay under $50",
)

await api.create_constraint(constraint)

# Link constraint to BOM artifact
bom = await api.get_artifact(bom_id)
await api.add_edge(
    source_id=bom.id,
    target_id=constraint.id,
    edge_type="CONSTRAINED_BY",
    metadata={"scope": "global", "priority": 1}
)

# Agent tries to commit BOM with total_cost = $60
result = await api.evaluate_constraints(branch="agent/electronics/bom-update")

# Result: passed=False, violations=[ConstraintViolation(...)]
# Commit is blocked until cost is reduced
```

---

### Workflow 3: Merge with Conflict Detection

```python
# Two agents work on same artifact in parallel

# Agent 1: Update chassis mass
branch1 = "agent/mechanical/mass-reduction"
artifact1 = await api.get_artifact(chassis_id, branch=branch1)
artifact1.metadata["mass_kg"] = 2.5
await api.update_artifact(chassis_id, {"metadata": artifact1.metadata}, branch=branch1)
await api.commit(branch1, "Reduce chassis mass", "agent_mech_001")

# Agent 2: Update chassis material
branch2 = "agent/mechanical/material-change"
artifact2 = await api.get_artifact(chassis_id, branch=branch2)
artifact2.metadata["material"] = "aluminum_7075"
await api.update_artifact(chassis_id, {"metadata": artifact2.metadata}, branch=branch2)
await api.commit(branch2, "Change to 7075 aluminum", "agent_mech_002")

# Try to merge branch1 → main (succeeds)
await api.merge(branch1, "main", "Merge mass reduction", "human")

# Try to merge branch2 → main (CONFLICT!)
try:
    await api.merge(branch2, "main", "Merge material change", "human")
except MergeConflictError as e:
    # e.conflicts = [MergeConflict(type="content", artifact_id=chassis_id, ...)]
    # Human must resolve manually
```

---

**End of Document**

---

**Next Steps**:

1. Review this plan with stakeholders
2. Create Linear issues for each component (map to MET-5 epic)
3. Set up development environment (Neo4j, Python deps)
4. Begin Week 1 implementation: models layer

**Questions? Contact**: [Your team channel]

**Last Updated**: 2026-03-02
