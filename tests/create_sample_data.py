#!/usr/bin/env python3
"""Create sample data in Neo4j for visual testing.

Run this script to populate the Digital Twin with sample artifacts,
constraints, and relationships. Then view them in Neo4j Browser at:
http://localhost:7474

Usage:
    python tests/create_sample_data.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from twin_core.api import Neo4jTwinAPI
from twin_core.models import (
    Artifact,
    ArtifactType,
    Component,
    ComponentLifecycle,
    Constraint,
    ConstraintSeverity,
)


async def create_sample_drone_design():
    """Create a sample drone design with artifacts, components, and constraints."""
    print("=" * 70)
    print("🚁 Creating Sample Drone Design in Digital Twin")
    print("=" * 70)

    api = Neo4jTwinAPI()

    try:
        # 1. Create CAD Model (Chassis)
        print("\n1️⃣  Creating Drone Chassis (CAD Model)...")
        chassis = Artifact(
            name="Drone_Chassis_V1",
            type=ArtifactType.CAD_MODEL,
            domain="mechanical",
            file_path="mechanical/chassis.step",
            content_hash="a1b2c3d4" * 8,  # 64 chars
            format="step",
            metadata={
                "mass_kg": 0.5,
                "material": "carbon_fiber",
                "dimensions_mm": [300, 300, 80],
                "units": "mm",
            },
            created_by="human",
        )
        chassis = await api.create_artifact(chassis)
        print(f"   ✅ Created: {chassis.name} (ID: {str(chassis.id)[:8]}...)")

        # 2. Create BOM
        print("\n2️⃣  Creating Bill of Materials...")
        bom = Artifact(
            name="Drone_BOM",
            type=ArtifactType.BOM,
            domain="electronics",
            file_path="electronics/bom.csv",
            content_hash="b1c2d3e4" * 8,
            format="csv",
            metadata={
                "total_cost": 45.50,
                "component_count": 23,
                "currency": "USD",
                "components": [  # Required by BOM schema
                    {"reference": "U1", "part_number": "STM32F103C8T6", "quantity": 1, "unit_cost": 2.50},
                    {"reference": "M1", "part_number": "EMAX-RS2205", "quantity": 4, "unit_cost": 12.99},
                    {"reference": "R1", "part_number": "RES-10K-0603", "quantity": 5, "unit_cost": 0.02},
                ],
            },
            created_by="human",
        )
        bom = await api.create_artifact(bom)
        print(f"   ✅ Created: {bom.name} (ID: {str(bom.id)[:8]}...)")

        # 3. Create Schematic
        print("\n3️⃣  Creating Flight Controller Schematic...")
        schematic = Artifact(
            name="Flight_Controller_Schematic",
            type=ArtifactType.SCHEMATIC,
            domain="electronics",
            file_path="electronics/fc_schematic.kicad_sch",
            content_hash="c1d2e3f4" * 8,
            format="kicad_sch",
            metadata={
                "voltage_rail": "3.3V",
                "power_budget_mw": 1500,
                "net_count": 45,
            },
            created_by="agent_electronics_001",
        )
        schematic = await api.create_artifact(schematic)
        print(f"   ✅ Created: {schematic.name} (ID: {str(schematic.id)[:8]}...)")

        # 4. Create Simulation Result
        print("\n4️⃣  Creating Stress Analysis Result...")
        simulation = Artifact(
            name="Chassis_Stress_Analysis",
            type=ArtifactType.SIMULATION_RESULT,
            domain="mechanical",
            file_path="simulation/stress_analysis.json",
            content_hash="d1e2f3a4" * 8,
            format="json",
            metadata={
                "simulation_type": "fea",
                "max_stress_mpa": 380.0,  # Must be float, not int
                "safety_factor": 1.8,
                "status": "pass",
                "solver": "CalculiX",
            },
            created_by="agent_mechanical_001",
        )
        simulation = await api.create_artifact(simulation)
        print(f"   ✅ Created: {simulation.name} (ID: {str(simulation.id)[:8]}...)")

        # 5. Create Firmware
        print("\n5️⃣  Creating Firmware Source...")
        firmware = Artifact(
            name="Flight_Controller_Firmware",
            type=ArtifactType.FIRMWARE_SOURCE,
            domain="firmware",
            file_path="firmware/main.c",
            content_hash="e1f2a3b4" * 8,
            format="c",
            metadata={
                "target_mcu": "STM32F103",
                "compiler": "arm-none-eabi-gcc",
                "size_bytes": 45000,
            },
            created_by="agent_firmware_001",
        )
        firmware = await api.create_artifact(firmware)
        print(f"   ✅ Created: {firmware.name} (ID: {str(firmware.id)[:8]}...)")

        # 6. Create Components
        print("\n6️⃣  Creating Components...")

        mcu = Component(
            part_number="STM32F103C8T6",
            manufacturer="STMicroelectronics",
            description="32-bit ARM MCU, 64KB Flash, 20KB RAM",
            package="LQFP-48",
            lifecycle=ComponentLifecycle.ACTIVE,
            datasheet_url="https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
            specs={"voltage": "3.3V", "flash_kb": 64, "ram_kb": 20},
            unit_cost=2.50,
            quantity=1,
        )
        mcu = await api.add_component(mcu)
        print(f"   ✅ Added: {mcu.part_number}")

        motor = Component(
            part_number="EMAX-RS2205",
            manufacturer="EMAX",
            description="Brushless motor 2300KV",
            package="N/A",
            lifecycle=ComponentLifecycle.ACTIVE,
            specs={"kv_rating": 2300, "voltage": "3S-4S", "weight_g": 28},
            unit_cost=12.99,
            quantity=4,
        )
        motor = await api.add_component(motor)
        print(f"   ✅ Added: {motor.part_number}")

        # 7. Create Constraints
        print("\n7️⃣  Creating Constraints...")

        cost_constraint = Constraint(
            name="max_bom_cost",
            expression="ctx.artifact('Drone_BOM').metadata.get('total_cost', 0) < 50.0",
            severity=ConstraintSeverity.ERROR,
            domain="electronics",
            source="user",
            message="Total BOM cost must stay under $50",
        )
        cost_constraint = await api.create_constraint(cost_constraint)
        print(f"   ✅ Created: {cost_constraint.name}")

        stress_constraint = Constraint(
            name="max_stress_limit",
            expression="ctx.artifact('Chassis_Stress_Analysis').metadata.get('max_stress_mpa', 0) < 500",
            severity=ConstraintSeverity.ERROR,
            domain="mechanical",
            source="system",
            message="Maximum stress must be under 500 MPa",
        )
        stress_constraint = await api.create_constraint(stress_constraint)
        print(f"   ✅ Created: {stress_constraint.name}")

        weight_constraint = Constraint(
            name="max_chassis_weight",
            expression="ctx.artifact('Drone_Chassis_V1').metadata.get('mass_kg', 0) < 0.8",
            severity=ConstraintSeverity.WARNING,
            domain="mechanical",
            source="user",
            message="Chassis weight should be under 800g",
        )
        weight_constraint = await api.create_constraint(weight_constraint)
        print(f"   ✅ Created: {weight_constraint.name}")

        # 8. Create Relationships (Edges)
        print("\n8️⃣  Creating Relationships...")

        # BOM depends on Schematic
        await api.add_edge(
            bom.id,
            schematic.id,
            "DEPENDS_ON",
            metadata={"dependency_type": "hard", "description": "BOM generated from schematic"},
        )
        print(f"   ✅ BOM → DEPENDS_ON → Schematic")

        # Firmware depends on Schematic
        await api.add_edge(
            firmware.id,
            schematic.id,
            "DEPENDS_ON",
            metadata={"dependency_type": "hard", "description": "Firmware uses pinmap from schematic"},
        )
        print(f"   ✅ Firmware → DEPENDS_ON → Schematic")

        # Simulation validates Chassis
        await api.add_edge(
            simulation.id,
            chassis.id,
            "VALIDATES",
            metadata={"description": "Stress analysis validates chassis design"},
        )
        print(f"   ✅ Simulation → VALIDATES → Chassis")

        # Link constraints to artifacts
        await api.add_edge(
            bom.id,
            cost_constraint.id,
            "CONSTRAINED_BY",
            metadata={"scope": "local", "priority": 1},
        )
        print(f"   ✅ BOM → CONSTRAINED_BY → Cost Constraint")

        await api.add_edge(
            simulation.id,
            stress_constraint.id,
            "CONSTRAINED_BY",
            metadata={"scope": "local", "priority": 1},
        )
        print(f"   ✅ Simulation → CONSTRAINED_BY → Stress Constraint")

        await api.add_edge(
            chassis.id,
            weight_constraint.id,
            "CONSTRAINED_BY",
            metadata={"scope": "local", "priority": 2},
        )
        print(f"   ✅ Chassis → CONSTRAINED_BY → Weight Constraint")

        # Link BOM to components
        await api.add_edge(
            bom.id,
            mcu.id,
            "USES_COMPONENT",
            metadata={"reference_designator": "U1", "quantity": 1},
        )
        print(f"   ✅ BOM → USES_COMPONENT → MCU")

        await api.add_edge(
            bom.id,
            motor.id,
            "USES_COMPONENT",
            metadata={"reference_designator": "M1-M4", "quantity": 4},
        )
        print(f"   ✅ BOM → USES_COMPONENT → Motor")

        # 9. Summary
        print("\n" + "=" * 70)
        print("✨ Sample Data Created Successfully!")
        print("=" * 70)
        print("\n📊 Summary:")
        print(f"   • 5 Artifacts (CAD, BOM, Schematic, Simulation, Firmware)")
        print(f"   • 2 Components (MCU, Motor)")
        print(f"   • 3 Constraints (Cost, Stress, Weight)")
        print(f"   • 10 Relationships (Dependencies, Validations, Constraints)")

        print("\n🌐 View in Neo4j Browser:")
        print("   1. Open: http://localhost:7474")
        print("   2. Login: neo4j / test1234")
        print("   3. Run:")
        print("")
        print("      // See all nodes and relationships")
        print("      MATCH (n)-[r]->(m) RETURN n, r, m")
        print("")
        print("      // See just artifacts")
        print("      MATCH (a:Artifact) RETURN a")
        print("")
        print("      // See the full graph")
        print("      MATCH (n) RETURN n LIMIT 50")
        print("")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        api.close()
        print("\n✅ Connection closed.")


if __name__ == "__main__":
    print("\n🔍 Checking Neo4j connection...")
    try:
        asyncio.run(create_sample_drone_design())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        print("\nMake sure Neo4j is running:")
        print("  docker ps | grep neo4j")
        sys.exit(1)
