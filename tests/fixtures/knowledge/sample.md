# Sample Design Decision: Bracket Material Selection

This fixture exercises the L1 ingest path with H1, H2, and H3 headings.
It is loaded by ``tests/integration/test_knowledge_service.py`` and is
not safe to delete without updating those tests.

## Background

The SR-7 mounting bracket is a load-bearing structural component for
the drone flight controller. It must survive a 3 g vibration load while
maintaining better than 0.05 mm flatness across the mounting face. The
prior aluminium 6061-T6 prototype failed pull-out testing at the heat
inserts after 200 thermal cycles between -20 °C and 85 °C.

### Failure Mode

Pull-out occurred at the threaded inserts. Root cause: the heat-set
inserts relaxed under thermal cycling because the surrounding aluminium
crept slightly above its 0.2 % proof stress. The traceable failure mode
is "insert pull-out, thermal-cycle induced".

## Decision

We move from aluminium 6061-T6 to titanium grade 5 (Ti-6Al-4V) for the
load path. Heat-set inserts are replaced with Helicoil thread inserts
that lock into a tapped titanium boss. Cost increases by 18 USD per
unit; mass drops by 9 grams; predicted thermal-cycle life increases
from 200 cycles to over 5000.

### Trade-offs

* Titanium grade 5 is roughly 4x the per-kg material cost of 6061-T6.
* Machining time goes up because of titanium's lower thermal
  conductivity and faster tool wear — adds about 12 minutes per part
  on the existing CNC.
* The Helicoil inserts add an assembly step but remove the 24-hour
  thermal cure of the heat-insert glue, so net assembly time falls.

### Approval

Approved by the Mechanical Engineering reviewer on 2026-04-12 with the
condition that thermal-cycle test results from the next prototype
batch are filed in the digital thread before EVT.

## References

* SR-7-MECH-014 — bracket structural requirement
* SR-7-FAIL-002 — insert pull-out failure log
* `tests/fixtures/knowledge/sample.md` — this document
