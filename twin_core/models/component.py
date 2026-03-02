"""Component models for the Digital Twin.

Components represent physical parts used in the design (ICs, resistors,
connectors, etc.) with supply chain metadata.
"""

import json
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ComponentLifecycle(StrEnum):
    """Production lifecycle status of a component."""

    ACTIVE = "active"
    NRND = "nrnd"  # Not recommended for new designs
    EOL = "eol"  # End of life
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"


class Component(BaseModel):
    """A component (physical part) in the Digital Twin graph.

    Attributes:
        id: Unique identifier (auto-generated)
        part_number: Manufacturer part number
        manufacturer: Manufacturer name
        description: Part description
        package: Physical package (e.g., "QFP-48", "0402")
        lifecycle: Production status
        datasheet_url: Link to datasheet
        specs: Key electrical/mechanical specifications
        alternates: Alternative part numbers
        unit_cost: Per-unit cost in USD
        lead_time_days: Estimated lead time
        quantity: Quantity used in design
    """

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

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j node properties."""
        return {
            "id": str(self.id),
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "description": self.description,
            "package": self.package,
            "lifecycle": self.lifecycle.value,
            "datasheet_url": self.datasheet_url,
            "specs": json.dumps(self.specs),  # JSON serialize
            "alternates": json.dumps(self.alternates),  # JSON serialize
            "unit_cost": self.unit_cost,
            "lead_time_days": self.lead_time_days,
            "quantity": self.quantity,
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "Component":
        """Create Component from Neo4j node properties."""
        # Deserialize specs and alternates
        specs = props.get("specs", "{}")
        if isinstance(specs, str):
            specs = json.loads(specs)

        alternates = props.get("alternates", "[]")
        if isinstance(alternates, str):
            alternates = json.loads(alternates)

        return cls(
            id=UUID(props["id"]),
            part_number=props["part_number"],
            manufacturer=props["manufacturer"],
            description=props.get("description", ""),
            package=props.get("package", ""),
            lifecycle=ComponentLifecycle(props.get("lifecycle", "active")),
            datasheet_url=props.get("datasheet_url", ""),
            specs=specs,
            alternates=alternates,
            unit_cost=props.get("unit_cost"),
            lead_time_days=props.get("lead_time_days"),
            quantity=props.get("quantity", 1),
        )
