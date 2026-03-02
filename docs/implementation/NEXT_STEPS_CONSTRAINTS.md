# Next Steps: Constraint Engine Implementation

**Created**: 2026-03-02
**Priority**: HIGH
**Estimated Time**: 1-2 days
**Branch**: `digital-twin-core-implementation`

---

## 🎯 What We're Building Next

The **Constraint Engine** is the "brain" that automatically checks design rules. It:
- Evaluates Python expressions against the graph
- Blocks invalid designs before they're saved
- Provides clear error messages when rules are violated

**Example**: If a constraint says "BOM cost must be under $50", and you try to save a BOM with cost $60, it will **BLOCK** the save and tell you why.

---

## 📊 Current Status

| Component | Status | What's Done | What's Missing |
|-----------|--------|-------------|----------------|
| Models | ✅ 100% | All constraint models working | Nothing |
| Structure | ✅ 100% | All classes defined with docstrings | Actual logic |
| Evaluator | 🟡 30% | Safe builtins defined | Expression evaluation |
| Context | 🟡 20% | Methods defined | Graph queries |
| Validator | 🟡 30% | Pipeline structure ready | Integration |

---

## 📁 Files to Work On

### 1. `twin_core/constraint_engine/validator.py` (Primary Focus)

**Current state**: Structure ready, all methods are stubs

**What needs implementation**:

#### A. `ConstraintContextImpl` (Lines 31-76)

This class provides graph access to constraint expressions.

**Methods to implement**:

```python
def artifact(self, name: str) -> Artifact:
    # TODO: Query graph for artifact by name
    # Current: Raises KeyError
    # Needed:
    #   1. Use self.graph.list_nodes("Artifact", {"name": name})
    #   2. Return Artifact.from_neo4j_props(result)
    #   3. Raise KeyError if not found
```

```python
def artifacts(self, domain: str | None, artifact_type: ArtifactType | None) -> list[Artifact]:
    # TODO: Query graph with filters
    # Current: Returns empty list
    # Needed:
    #   1. Build filters dict from domain and artifact_type
    #   2. Use self.graph.list_nodes("Artifact", filters)
    #   3. Convert to Artifact objects
```

```python
def components(self) -> list[Component]:
    # TODO: Query all components
    # Current: Returns empty list
    # Needed:
    #   1. Use self.graph.list_nodes("Component")
    #   2. Convert to Component objects
```

```python
def dependents(self, artifact_id: UUID) -> list[Artifact]:
    # TODO: Follow DEPENDS_ON edges backward
    # Current: Returns empty list
    # Needed:
    #   1. Use self.graph.get_edges(artifact_id, direction="incoming", edge_type="DEPENDS_ON")
    #   2. For each edge, get source artifact
    #   3. Return list of Artifact objects
```

**Estimated time**: 2-3 hours

---

#### B. `ConstraintValidator.evaluate_constraints_for_commit()` (Lines 132-183)

This is the main evaluation pipeline.

**What needs implementation**:

```python
async def _load_affected_constraints(self, artifact_ids: list[UUID]) -> list[Constraint]:
    # TODO: Query for constraints linked via CONSTRAINED_BY edges
    # Current: Returns empty list
    # Needed:
    #   1. For each artifact_id:
    #      - Use self.graph.get_edges(artifact_id, edge_type="CONSTRAINED_BY")
    #   2. For each edge, get target constraint node
    #   3. Convert to Constraint objects
    #   4. Deduplicate and return
```

```python
async def _expand_cross_domain_constraints(self, constraints: list[Constraint]) -> list[Constraint]:
    # TODO: Find cross-domain constraints
    # Current: Returns input unchanged
    # Needed:
    #   1. For each constraint with cross_domain=True:
    #      - Find transitively related artifacts
    #      - Load their constraints too
    #   2. Deduplicate and return expanded list
```

```python
async def _update_constraint_status(self, constraint_id: UUID, status: ConstraintStatus) -> None:
    # TODO: Update constraint node in graph
    # Current: Does nothing
    # Needed:
    #   1. Use self.graph.update_node(constraint_id, "Constraint", {"status": status.value})
    #   2. Also update "last_evaluated" timestamp
```

**Estimated time**: 3-4 hours

---

### 2. `twin_core/constraint_engine/resolver.py` (Secondary Focus)

**What needs implementation**:

```python
async def find_conflicting_constraints(self, constraint_ids: list[UUID]) -> list[tuple[UUID, UUID]]:
    # Query for CONFLICTS_WITH edges
    # Example Cypher:
    # MATCH (c1:Constraint)-[:CONFLICTS_WITH]-(c2:Constraint)
    # WHERE c1.id IN $constraint_ids AND c2.id IN $constraint_ids
    # RETURN c1.id, c2.id
```

```python
def resolve_constraint_priority(self, constraints: list[Constraint]) -> list[Constraint]:
    # Query edge metadata for priority values
    # Sort constraints by priority (highest first)
```

**Estimated time**: 2 hours

---

## 🔨 Implementation Steps (Day-by-Day)

### Day 1: Make Constraints Work End-to-End

#### Morning (3-4 hours)

**Goal**: Implement `ConstraintContextImpl` graph queries

1. **Start with `artifact(name)`** (easiest):
   ```python
   async def artifact(self, name: str) -> Artifact:
       # Use existing graph.list_nodes()
       props_list = await self.graph.list_nodes("Artifact", {"name": name})
       if not props_list:
           raise KeyError(f"Artifact '{name}' not found")
       return Artifact.from_neo4j_props(props_list[0])
   ```

2. **Then `artifacts(domain, type)`**:
   ```python
   async def artifacts(self, domain: str | None, artifact_type: ArtifactType | None) -> list[Artifact]:
       filters = {}
       if domain:
           filters["domain"] = domain
       if artifact_type:
           filters["type"] = artifact_type.value

       props_list = await self.graph.list_nodes("Artifact", filters)
       return [Artifact.from_neo4j_props(p) for p in props_list]
   ```

3. **Test it**:
   ```python
   # Create a quick test
   context = ConstraintContextImpl(graph_engine, "main")
   artifact = await context.artifact("Drone_BOM")
   print(f"Found: {artifact.name}")
   ```

#### Afternoon (3-4 hours)

**Goal**: Implement constraint loading and evaluation

1. **Implement `_load_affected_constraints()`**:
   - Query CONSTRAINED_BY edges
   - Load constraint nodes
   - Convert to Constraint objects

2. **Test constraint evaluation**:
   ```python
   # Run a simple constraint
   result = await validator.evaluate_constraints_for_commit("main", [bom_id])
   print(f"Passed: {result.passed}")
   print(f"Violations: {result.violations}")
   ```

3. **Wire it into Twin API**:
   - Update `api.create_artifact()` to call constraint validation
   - Block saves if constraints fail

---

### Day 2: Polish and Test

#### Morning (2-3 hours)

**Goal**: Complete remaining methods

1. **Implement `components()` and `dependents()`**
2. **Implement `_update_constraint_status()`**
3. **Implement conflict detection in resolver**

#### Afternoon (2-3 hours)

**Goal**: Testing and integration

1. **Write integration tests**:
   - Create artifact with constraint
   - Try to violate constraint (should FAIL)
   - Fix violation (should PASS)

2. **Test with sample data**:
   ```bash
   python tests/create_sample_data.py
   # Then test constraints against that data
   ```

3. **Visual demo**:
   - Show constraint blocking in action
   - View constraint status in Neo4j UI

---

## 🧪 How to Test

### Manual Test Script

Create `tests/test_constraints_manual.py`:

```python
import asyncio
from twin_core.api import Neo4jTwinAPI
from twin_core.models import Artifact, ArtifactType, Constraint, ConstraintSeverity

async def test_cost_constraint():
    api = Neo4jTwinAPI()

    # 1. Create a BOM with cost $40 (under limit)
    bom = Artifact(
        name="Test_BOM",
        type=ArtifactType.BOM,
        domain="electronics",
        file_path="test_bom.csv",
        content_hash="a" * 64,
        format="csv",
        metadata={"total_cost": 40.0},
        created_by="test",
    )
    bom = await api.create_artifact(bom)
    print(f"✅ Created BOM with cost $40")

    # 2. Create constraint: cost must be < $50
    constraint = Constraint(
        name="max_cost",
        expression="ctx.artifact('Test_BOM').metadata.get('total_cost', 0) < 50.0",
        severity=ConstraintSeverity.ERROR,
        domain="electronics",
        source="user",
        message="Cost must be under $50",
    )
    constraint = await api.create_constraint(constraint)

    # 3. Link BOM to constraint
    await api.add_edge(bom.id, constraint.id, "CONSTRAINED_BY")
    print(f"✅ Linked BOM to constraint")

    # 4. Evaluate constraints
    result = await api.evaluate_constraints("main")
    print(f"\n📊 Constraint Evaluation:")
    print(f"   Passed: {result.passed}")
    print(f"   Violations: {len(result.violations)}")

    # 5. Try to update BOM to cost $60 (over limit) - should FAIL
    try:
        await api.update_artifact(
            bom.id,
            {"metadata": '{"total_cost": 60.0}'}
        )
        # Re-evaluate
        result = await api.evaluate_constraints("main")
        if not result.passed:
            print(f"\n❌ Constraint BLOCKED invalid update!")
            for v in result.violations:
                print(f"   - {v.message}")
        else:
            print(f"\n⚠️  Constraint should have failed!")
    except Exception as e:
        print(f"\n✅ Update blocked by constraint: {e}")

    api.close()

asyncio.run(test_cost_constraint())
```

---

## 🎯 Success Criteria

When you're done, you should be able to:

1. **Create a constraint** that checks a rule
2. **Link it to an artifact**
3. **Evaluate constraints** and see PASS/FAIL
4. **Block invalid saves** that violate constraints
5. **View constraint status** in Neo4j UI

### Visual Demo

```cypher
// See constraints and their status
MATCH (c:Constraint) RETURN c

// See which artifacts are constrained
MATCH (a:Artifact)-[:CONSTRAINED_BY]->(c:Constraint)
RETURN a.name, c.name, c.status
```

---

## 🔍 Debugging Tips

### If constraint evaluation fails:

1. **Check the expression**:
   ```python
   # Test expression in isolation
   expression = "ctx.artifact('Test_BOM').metadata.get('total_cost', 0) < 50.0"
   context = ConstraintContextImpl(graph, "main")
   result = eval(expression, {"__builtins__": safe_builtins, "ctx": context})
   ```

2. **Check artifact exists**:
   ```python
   artifact = await context.artifact('Test_BOM')
   print(artifact.metadata)
   ```

3. **Check edges exist**:
   ```cypher
   MATCH (a:Artifact)-[r:CONSTRAINED_BY]->(c:Constraint)
   RETURN a, r, c
   ```

---

## 📚 Reference Code Examples

### Example 1: Simple Constraint

```python
# Cost constraint
{
  "name": "max_bom_cost",
  "expression": "ctx.artifact('BOM').metadata.get('total_cost', 0) < 50.0",
  "severity": "ERROR",
  "message": "BOM cost must stay under $50"
}
```

### Example 2: Complex Constraint

```python
# All components must be ACTIVE
{
  "name": "active_components_only",
  "expression": "all(c.lifecycle == 'active' for c in ctx.components())",
  "severity": "ERROR",
  "message": "All components must have ACTIVE lifecycle status"
}
```

### Example 3: Cross-Domain Constraint

```python
# Firmware size must fit in MCU flash
{
  "name": "firmware_fits_flash",
  "expression": "ctx.artifact('Firmware').metadata.get('size_bytes', 0) < 65536",
  "severity": "ERROR",
  "cross_domain": True,
  "message": "Firmware must fit in 64KB flash"
}
```

---

## 🚀 Quick Start (Tomorrow Morning)

1. **Open the project**:
   ```bash
   cd /Users/dee_vyn/Documents/metaforge/MetaForge
   git status  # Should show: digital-twin-core-implementation
   ```

2. **Open the file to edit**:
   ```bash
   code twin_core/constraint_engine/validator.py
   ```

3. **Start with the easiest method**:
   - Find `def artifact(self, name: str)` (line ~51)
   - Replace `raise NotImplementedError` with actual implementation
   - Test it immediately

4. **Run tests to verify**:
   ```bash
   pytest tests/test_twin_basic.py -v  # Should still pass
   python tests/create_sample_data.py  # Create test data
   ```

5. **Continue to next method**

---

## 📝 Code Template to Get Started

Here's the starter code for `ConstraintContextImpl.artifact()`:

```python
async def artifact(self, name: str) -> Artifact:
    """Retrieve an artifact by name from the current graph state.

    Args:
        name: Name of the artifact to retrieve.

    Returns:
        Artifact instance.

    Raises:
        KeyError: If artifact not found.
    """
    # Check cache first
    if name in self._artifact_cache:
        return self._artifact_cache[name]

    # Query graph using graph engine
    filters = {"name": name}
    props_list = await self.graph.list_nodes("Artifact", filters)

    if not props_list:
        raise KeyError(f"Artifact '{name}' not found")

    # Convert to Artifact object
    artifact = Artifact.from_neo4j_props(props_list[0])

    # Cache it
    self._artifact_cache[name] = artifact

    return artifact
```

Copy this pattern for the other methods!

---

## 💡 Why This Matters

Once constraints work, you can:

1. **Prevent design mistakes** automatically
2. **Enforce company standards** (cost limits, safety factors, etc.)
3. **Cross-domain validation** (firmware fits in MCU flash, BOM matches schematic, etc.)
4. **Demo the "intelligence"** of the Digital Twin

This is the feature that makes MetaForge **smart** instead of just a database!

---

## ✅ Checklist for Tomorrow

- [ ] Read this document
- [ ] Open `twin_core/constraint_engine/validator.py`
- [ ] Implement `ConstraintContextImpl.artifact()`
- [ ] Test it manually
- [ ] Implement `ConstraintContextImpl.artifacts()`
- [ ] Implement `_load_affected_constraints()`
- [ ] Wire constraints into `api.create_artifact()`
- [ ] Test end-to-end with sample data
- [ ] Celebrate! 🎉

---

**Questions?**
- Refer to `docs/twin_schema.md` Section 5 (Constraint Engine)
- Check `twin_core/README.md` for API examples
- Look at test files for usage patterns

**Good luck tomorrow!** 🚀
