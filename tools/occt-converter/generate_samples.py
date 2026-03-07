"""Generate sample STEP files for testing the OCCT converter.

Requires cadquery: pip install cadquery

Usage:
    python generate_samples.py
"""

from __future__ import annotations

from pathlib import Path


def generate_simple_bracket(out_dir: Path) -> None:
    """Generate a simple L-bracket as a single-part STEP file."""
    import cadquery as cq

    bracket = (
        cq.Workplane("XY")
        .box(40, 10, 5)
        .faces(">Z")
        .workplane()
        .transformed(offset=(15, 0, 0))
        .box(10, 10, 30)
    )
    path = out_dir / "simple-bracket.step"
    cq.exporters.export(bracket, str(path))
    print(f"Created: {path}")


def generate_assembly(out_dir: Path) -> None:
    """Generate a 3-part assembly as a compound STEP file."""
    import cadquery as cq

    base = cq.Workplane("XY").box(50, 30, 5)
    pillar = cq.Workplane("XY").transformed(offset=(0, 0, 15)).cylinder(25, 5)
    cap = cq.Workplane("XY").transformed(offset=(0, 0, 30)).box(20, 20, 3)

    assembly = cq.Assembly()
    assembly.add(base, name="base_plate")
    assembly.add(pillar, name="support_pillar")
    assembly.add(cap, name="top_cap")

    path = out_dir / "assembly-3part.step"
    assembly.save(str(path))
    print(f"Created: {path}")


def main() -> None:
    out_dir = Path(__file__).parent / "samples"
    out_dir.mkdir(exist_ok=True)

    try:
        generate_simple_bracket(out_dir)
        generate_assembly(out_dir)
        print("Sample files generated successfully.")
    except ImportError:
        print("cadquery not installed — skipping sample generation.")
        print("Install with: pip install cadquery")
        # Create placeholder README instead
        readme = out_dir / "README.md"
        readme.write_text(
            "# Sample STEP Files\n\n"
            "Generate sample files by running:\n\n"
            "```bash\n"
            "pip install cadquery\n"
            "python generate_samples.py\n"
            "```\n\n"
            "Or place your own `.step` / `.stp` files here for testing.\n"
        )
        print(f"Created placeholder: {readme}")


if __name__ == "__main__":
    main()
