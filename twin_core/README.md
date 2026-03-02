# Digital Twin Core

The **Digital Twin** is the single source of design truth in MetaForge. It is a versioned, directed property graph stored in Neo4j that captures every artifact, constraint, relationship, and version in a hardware design.

## What is the Digital Twin?

The Digital Twin is a graph database that stores:

- **Artifacts**: Design outputs (schematics, BOMs, CAD models, firmware, test plans, etc.)
- **Constraints**: Rules that must be satisfied across artifacts
- **Relationships**: Dependencies and connections between artifacts
- **Versions**: Git-like version history with branching and merging
- **Components**: Physical parts with supply chain metadata
- **Agents**: Provenance tracking for which agent produced which artifacts

**Prime Rule**: All agents read from and propose changes to the Twin. No agent maintains its own persistent state.

---

## Architecture

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

---

## Quick Start

### 1. Start Neo4j

```bash
docker run -d \
  --name metaforge-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/test \
  neo4j:latest
```

### 2. Install Dependencies

```bash
pip install pydantic neo4j pydantic-settings
```

### 3. Initialize Schema

```bash
python -m twin_core.init_schema
```

### 4. Use the Twin API

```python
from twin_core.api import Neo4jTwinAPI
from twin_core.models import Artifact, ArtifactType

# Initialize API
api = Neo4jTwinAPI()

# Create an artifact
artifact = Artifact(
    name="chassis_v1",
    type=ArtifactType.CAD_MODEL,
    domain="mechanical",
    file_path="models/chassis.step",
    content_hash="abc123...",  # SHA-256 of file
    format="step",
    created_by="agent_mechanical_001",
)

created = await api.create_artifact(artifact)
print(f"Created artifact: {created.id}")

# Close connection
api.close()
```

---

## Project Structure

```
twin_core/
├── models/                     # Pydantic models
│   ├── artifact.py             # Artifact + ArtifactType enum
│   ├── constraint.py           # Constraint + evaluation models
│   ├── version.py              # Version + diff models
│   ├── relationship.py         # EdgeBase + specialized edges
│   ├── component.py            # Component + lifecycle enum
│   ├── agent.py                # AgentNode model
│   └── __init__.py             # Module exports
│
├── graph_engine.py             # Neo4j CRUD operations
├── api.py                      # Public Twin API (use this!)
│
├── constraint_engine/          # Constraint validation
│   ├── validator.py            # Expression evaluator
│   └── resolver.py             # Conflict resolution
│
├── validation_engine/          # Schema validation
│   ├── schema_validator.py     # Artifact schema validator
│   └── schemas/                # JSON schemas per artifact type
│       ├── bom_schema.json
│       ├── cad_model_schema.json
│       └── simulation_result_schema.json
│
├── versioning/                 # Git-like version control
│   ├── branch.py               # Branch operations
│   ├── diff.py                 # Diff computation
│   └── merge.py                # Merge logic
│
├── config.py                   # Configuration (Neo4j URI, etc.)
├── exceptions.py               # Custom exception classes
├── init_schema.py              # Schema initialization script
└── __init__.py                 # Package exports
```

---

## Configuration

All configuration is done via environment variables with the `TWIN_` prefix.

Create a `.env` file:

```bash
TWIN_NEO4J_URI=bolt://localhost:7687
TWIN_NEO4J_USER=neo4j
TWIN_NEO4J_PASSWORD=test
TWIN_CONSTRAINT_EVAL_TIMEOUT_MS=5000
TWIN_MAX_SUBGRAPH_DEPTH=10
```

Or use defaults defined in `config.py`.

---

## Core Concepts

### Artifacts

Artifacts represent design outputs. Each artifact has:

- `id`: Unique UUID
- `name`: Human-readable name
- `type`: One of 15 artifact types (CAD_MODEL, BOM, SCHEMATIC, etc.)
- `domain`: Engineering domain (mechanical, electronics, firmware)
- `file_path`: Relative path to file on disk
- `content_hash`: SHA-256 hash of file contents
- `format`: File format (step, json, kicad_sch, etc.)
- `metadata`: Domain-specific key-value pairs
- `created_by`: Agent ID or "human"

**Example**:

```python
artifact = Artifact(
    name="power_bom",
    type=ArtifactType.BOM,
    domain="electronics",
    file_path="bom/power.csv",
    content_hash=compute_content_hash("bom/power.csv"),
    format="csv",
    metadata={"total_cost": 45.50, "component_count": 23},
    created_by="agent_electronics_001",
)
```

### Constraints

Constraints are first-class nodes that represent rules evaluated against the graph.

- `expression`: Python expression (e.g., `ctx.artifact('bom').metadata['total_cost'] < 50`)
- `severity`: ERROR (blocks commit), WARNING, or INFO
- `status`: PASS, FAIL, WARN, UNEVALUATED, SKIPPED

**Example**:

```python
constraint = Constraint(
    name="max_bom_cost",
    expression="ctx.artifact('bom').metadata.get('total_cost', 0) < 50.0",
    severity=ConstraintSeverity.ERROR,
    domain="electronics",
    source="user",
    message="BOM cost must stay under $50",
)
```

### Versioning

The Twin uses Git-like version control:

- **Branches**: `main`, `agent/<domain>/<task>`, `review/<id>`
- **Commits**: Create version snapshots with commit messages
- **Merge**: Three-way merge with conflict detection
- **Diff**: Compare two versions to see what changed

**Example**:

```python
# Create a branch
await api.create_branch("agent/mechanical/chassis-update", from_branch="main")

# Commit changes
version = await api.commit(
    branch="agent/mechanical/chassis-update",
    message="Update chassis CAD model",
    author="agent_mechanical_001"
)

# Merge to main
merge_version = await api.merge(
    source="agent/mechanical/chassis-update",
    target="main",
    message="Merge chassis updates",
    author="human"
)
```

---

## Twin API Reference

### Artifact Operations

```python
# Create
artifact = await api.create_artifact(artifact, branch="main")

# Read
artifact = await api.get_artifact(artifact_id, branch="main")

# Update
artifact = await api.update_artifact(
    artifact_id,
    {"metadata": {"total_cost": 48.00}},
    branch="main"
)

# Delete
deleted = await api.delete_artifact(artifact_id, branch="main")

# List with filters
artifacts = await api.list_artifacts(
    branch="main",
    domain="electronics",
    artifact_type=ArtifactType.BOM
)
```

### Constraint Operations

```python
# Create constraint
constraint = await api.create_constraint(constraint)

# Link constraint to artifact
await api.add_edge(
    source_id=artifact.id,
    target_id=constraint.id,
    edge_type="CONSTRAINED_BY",
    metadata={"scope": "global", "priority": 1}
)

# Evaluate all constraints
result = await api.evaluate_constraints(branch="main")
if not result.passed:
    print("Violations:")
    for v in result.violations:
        print(f"  - {v.message}")
```

### Versioning Operations

```python
# Create branch
await api.create_branch("agent/electronics/bom-update", from_branch="main")

# Commit (TODO: implement)
version = await api.commit(
    branch="agent/electronics/bom-update",
    message="Add missing capacitors to BOM",
    author="agent_electronics_001"
)

# Diff
diff = await api.diff("main", "agent/electronics/bom-update")
print(f"Added: {len([c for c in diff.changes if c.change_type == 'added'])}")
print(f"Modified: {len([c for c in diff.changes if c.change_type == 'modified'])}")

# Merge
merge_version = await api.merge(
    source="agent/electronics/bom-update",
    target="main",
    message="Merge BOM updates",
    author="human"
)

# Log
history = await api.log(branch="main", limit=10)
for version in history:
    print(f"{version.id}: {version.commit_message}")
```

### Component Operations

```python
# Add component
component = Component(
    part_number="STM32F103C8T6",
    manufacturer="STMicroelectronics",
    package="LQFP-48",
    lifecycle=ComponentLifecycle.ACTIVE,
    unit_cost=2.50,
)
added = await api.add_component(component)

# Find components
results = await api.find_components({
    "manufacturer": "STMicroelectronics",
    "package": "LQFP-48"
})
```

### Relationship Operations

```python
# Add dependency edge
await api.add_edge(
    source_id=pcb_artifact.id,
    target_id=schematic_artifact.id,
    edge_type="DEPENDS_ON",
    metadata={"dependency_type": "hard", "description": "PCB layout depends on schematic"}
)

# Get all edges for a node
edges = await api.get_edges(
    node_id=artifact.id,
    direction="outgoing",
    edge_type="DEPENDS_ON"
)

# Remove edge
await api.remove_edge(source_id, target_id, "DEPENDS_ON")
```

### Query Operations

```python
# Get subgraph
subgraph = await api.get_subgraph(
    root_id=artifact.id,
    depth=3,
    edge_types=["DEPENDS_ON", "IMPLEMENTS"]
)

# Raw Cypher query
results = await api.query_cypher(
    "MATCH (a:Artifact {domain: $domain}) RETURN a",
    params={"domain": "mechanical"}
)
```

---

## Testing

### Run Basic Tests

```bash
# Test models (no Neo4j required)
pytest tests/test_twin_basic.py -v
```

### Integration Tests (TODO)

```bash
# Requires Neo4j running
pytest tests/integration/twin_core/ -v
```

---

## Implementation Status

| Component | Status | LOC | Notes |
|-----------|--------|-----|-------|
| **Models** | ✅ Complete | 640 | All 6 model files + enums |
| **Graph Engine** | 🟡 Skeleton | 700 | Neo4j CRUD, needs async impl |
| **Constraint Engine** | 🟡 Skeleton | 600 | Validator + resolver, needs impl |
| **Validation Engine** | 🟡 Skeleton | 300 | Schema validator with JSON schemas |
| **Versioning** | 🟡 Skeleton | 800 | Branch/diff/merge, needs impl |
| **Twin API** | 🟡 Skeleton | 800 | All 28 methods defined, partial impl |
| **Tests** | 🟡 Partial | 200 | Model tests complete, integration TODO |

**Legend**:
- ✅ **Complete**: Fully implemented and tested
- 🟡 **Skeleton**: Structure in place, needs implementation
- ⏳ **Planned**: Not yet started

---

## Next Steps

### Week 1: Complete Graph Engine

1. Implement async wrappers for Neo4j operations
2. Complete all CRUD methods
3. Write integration tests against local Neo4j

### Week 2: Constraint Engine

1. Implement constraint expression evaluation
2. Complete ConstraintContext graph queries
3. Add cross-domain constraint propagation

### Week 3: Versioning

1. Implement branch operations
2. Complete diff computation
3. Implement merge with conflict detection

### Week 4: Integration

1. Wire everything together in Twin API
2. Complete commit operation
3. Write end-to-end test for MET-8 mechanical vertical

---

## References

- **Specification**: `docs/twin_schema.md` - Complete graph schema
- **Implementation Plan**: `docs/implementation/twin_phase1_plan.md` - Detailed roadmap
- **Architecture**: `MetaForge-Planner/docs/architecture/architecture.md` - System design

---

## License

Part of the MetaForge project. See LICENSE file in repository root.
