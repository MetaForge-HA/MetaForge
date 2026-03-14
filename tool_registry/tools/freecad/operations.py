"""FreeCAD operations -- conditional FreeCAD Python API usage.

Provides the core CAD operations (parametric creation, STEP export, mesh generation)
that the FreeCAD MCP adapter exposes. FreeCAD imports are conditional so the module
can be imported and tested without a real FreeCAD installation.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import structlog

from observability.tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer("tool_registry.tools.freecad.operations")

# Conditional FreeCAD import -- allows testing without FreeCAD installed
try:
    import FreeCAD  # type: ignore[import-untyped]
    import Part  # type: ignore[import-untyped]

    HAS_FREECAD = True
except ImportError:
    FreeCAD = None  # type: ignore[assignment]
    Part = None  # type: ignore[assignment]
    HAS_FREECAD = False

# Conditional Mesh import (FEM workbench)
try:
    import Mesh  # type: ignore[import-untyped]

    HAS_MESH = True
except ImportError:
    Mesh = None  # type: ignore[assignment]
    HAS_MESH = False


class FreecadNotAvailableError(RuntimeError):
    """Raised when FreeCAD Python bindings are not available."""

    def __init__(self) -> None:
        super().__init__(
            "FreeCAD Python bindings are not installed. "
            "Run inside the FreeCAD Docker container or install FreeCAD with Python support."
        )


# Shape dimension defaults per shape type
_SHAPE_DEFAULTS: dict[str, dict[str, float]] = {
    "box": {"length": 10.0, "width": 10.0, "height": 10.0},
    "cylinder": {"radius": 5.0, "height": 20.0},
    "sphere": {"radius": 10.0},
    "cone": {"radius1": 10.0, "radius2": 5.0, "height": 20.0},
    "bracket": {"length": 50.0, "width": 30.0, "thickness": 5.0, "hole_radius": 3.0},
    "plate": {"length": 100.0, "width": 50.0, "thickness": 2.0},
    "enclosure": {
        "length": 80.0,
        "width": 50.0,
        "height": 30.0,
        "wall_thickness": 2.0,
    },
}


class FreecadOperations:
    """Core FreeCAD CAD operations.

    All methods return structured dicts with file paths and metadata.
    Methods require FreeCAD Python bindings at runtime but can be tested
    with mocked internals.
    """

    def __init__(self, work_dir: str = "/workspace", timeout: float = 60.0) -> None:
        self.work_dir = work_dir
        self.timeout = timeout

    def _require_freecad(self) -> None:
        """Raise if FreeCAD is not available."""
        if not HAS_FREECAD:
            raise FreecadNotAvailableError

    def _ensure_output_dir(self, file_path: str) -> None:
        """Create parent directories for the output file if needed."""
        parent = Path(file_path).parent
        parent.mkdir(parents=True, exist_ok=True)

    def create_parametric(
        self,
        shape_type: str,
        parameters: dict[str, Any],
        material: str = "",
        output_path: str = "",
    ) -> dict[str, Any]:
        """Create a parametric shape and export to STEP.

        Args:
            shape_type: One of box, cylinder, sphere, cone, bracket, plate, enclosure.
            parameters: Shape-specific dimensions.
            material: Material name for metadata.
            output_path: Where to write the STEP file.

        Returns:
            Dict with cad_file path, volume, surface area, bounding box, and parameters.
        """
        self._require_freecad()

        with tracer.start_as_current_span("freecad.create_parametric") as span:
            span.set_attribute("shape.type", shape_type)
            span.set_attribute("shape.material", material or "unspecified")

            start = time.monotonic()

            if not output_path:
                output_path = os.path.join(self.work_dir, f"{shape_type}.step")
            self._ensure_output_dir(output_path)

            # Merge defaults with provided parameters
            defaults = _SHAPE_DEFAULTS.get(shape_type, {})
            merged = {**defaults, **parameters}

            try:
                shape = self._build_shape(shape_type, merged)
            except Exception as exc:
                span.record_exception(exc)
                raise

            # Compute properties
            volume = shape.Volume
            area = shape.Area
            bb = shape.BoundBox

            # Export STEP
            shape.exportStep(output_path)

            elapsed = time.monotonic() - start
            span.set_attribute("operation.duration_s", round(elapsed, 3))

            logger.info(
                "Created parametric shape",
                shape_type=shape_type,
                output_path=output_path,
                volume_mm3=round(volume, 2),
                duration_s=round(elapsed, 3),
            )

            return {
                "cad_file": output_path,
                "volume_mm3": round(volume, 2),
                "surface_area_mm2": round(area, 2),
                "bounding_box": {
                    "min_x": round(bb.XMin, 2),
                    "min_y": round(bb.YMin, 2),
                    "min_z": round(bb.ZMin, 2),
                    "max_x": round(bb.XMax, 2),
                    "max_y": round(bb.YMax, 2),
                    "max_z": round(bb.ZMax, 2),
                },
                "parameters_used": merged,
                "material": material,
            }

    def _build_shape(self, shape_type: str, params: dict[str, Any]) -> Any:
        """Build a FreeCAD Part shape from type and parameters."""
        if shape_type == "box":
            return Part.makeBox(
                params["length"],
                params["width"],
                params["height"],
            )
        elif shape_type == "cylinder":
            return Part.makeCylinder(params["radius"], params["height"])
        elif shape_type == "sphere":
            return Part.makeSphere(params["radius"])
        elif shape_type == "cone":
            return Part.makeCone(
                params["radius1"],
                params["radius2"],
                params["height"],
            )
        elif shape_type == "bracket":
            return self._build_bracket(params)
        elif shape_type == "plate":
            return Part.makeBox(
                params["length"],
                params["width"],
                params["thickness"],
            )
        elif shape_type == "enclosure":
            return self._build_enclosure(params)
        else:
            raise ValueError(f"Unsupported shape type: {shape_type}")

    def _build_bracket(self, params: dict[str, Any]) -> Any:
        """Build an L-bracket with a mounting hole."""
        length = params["length"]
        width = params["width"]
        thickness = params["thickness"]
        hole_radius = params.get("hole_radius", 3.0)

        # Horizontal plate
        base = Part.makeBox(length, width, thickness)
        # Vertical plate
        import FreeCAD as FC  # type: ignore[import-untyped]

        vert = Part.makeBox(thickness, width, length / 2)
        vert.translate(FC.Vector(0, 0, thickness))
        bracket = base.fuse(vert)

        # Mounting hole in the base plate
        hole = Part.makeCylinder(
            hole_radius,
            thickness * 2,
            FC.Vector(length * 0.75, width / 2, -thickness / 2),
            FC.Vector(0, 0, 1),
        )
        bracket = bracket.cut(hole)
        return bracket

    def _build_enclosure(self, params: dict[str, Any]) -> Any:
        """Build a hollow box enclosure."""
        length = params["length"]
        width = params["width"]
        height = params["height"]
        wall = params.get("wall_thickness", 2.0)

        outer = Part.makeBox(length, width, height)
        import FreeCAD as FC  # type: ignore[import-untyped]

        inner = Part.makeBox(
            length - 2 * wall,
            width - 2 * wall,
            height - wall,
        )
        inner.translate(FC.Vector(wall, wall, wall))
        return outer.cut(inner)

    def export_step(
        self,
        input_file: str,
        output_path: str = "",
    ) -> dict[str, Any]:
        """Load a CAD file and export to STEP format.

        Args:
            input_file: Path to the source CAD file.
            output_path: Where to write the STEP file.

        Returns:
            Dict with output file path and metadata.
        """
        self._require_freecad()

        with tracer.start_as_current_span("freecad.export_step") as span:
            span.set_attribute("input.file", input_file)

            start = time.monotonic()

            if not output_path:
                stem = Path(input_file).stem
                output_path = os.path.join(self.work_dir, f"{stem}.step")
            self._ensure_output_dir(output_path)

            try:
                doc = FreeCAD.openDocument(input_file)
                shapes = []
                for obj in doc.Objects:
                    if hasattr(obj, "Shape"):
                        shapes.append(obj.Shape)

                if not shapes:
                    raise ValueError(f"No shapes found in {input_file}")

                # Fuse all shapes or use the single shape
                if len(shapes) == 1:
                    combined = shapes[0]
                else:
                    combined = shapes[0]
                    for s in shapes[1:]:
                        combined = combined.fuse(s)

                combined.exportStep(output_path)
                file_size = os.path.getsize(output_path)

                FreeCAD.closeDocument(doc.Name)
            except Exception as exc:
                span.record_exception(exc)
                raise

            elapsed = time.monotonic() - start
            span.set_attribute("operation.duration_s", round(elapsed, 3))

            logger.info(
                "Exported STEP",
                input_file=input_file,
                output_path=output_path,
                file_size_bytes=file_size,
                duration_s=round(elapsed, 3),
            )

            return {
                "output_file": output_path,
                "file_size_bytes": file_size,
                "format": "step",
            }

    def generate_mesh(
        self,
        input_file: str,
        element_size: float = 1.0,
        algorithm: str = "netgen",
        output_format: str = "inp",
    ) -> dict[str, Any]:
        """Generate a finite element mesh from a CAD file.

        Args:
            input_file: Path to the source CAD file.
            element_size: Target element size for meshing.
            algorithm: Meshing algorithm (netgen, gmsh, mefisto).
            output_format: Output format (inp, unv, stl).

        Returns:
            Dict with mesh file path, node/element counts, and quality metrics.
        """
        self._require_freecad()

        with tracer.start_as_current_span("freecad.mesh") as span:
            span.set_attribute("input.file", input_file)
            span.set_attribute("mesh.element_size", element_size)
            span.set_attribute("mesh.algorithm", algorithm)

            start = time.monotonic()

            stem = Path(input_file).stem
            output_path = os.path.join(self.work_dir, f"{stem}.{output_format}")
            self._ensure_output_dir(output_path)

            try:
                doc = FreeCAD.openDocument(input_file)

                # Find the first shape object
                shape = None
                for obj in doc.Objects:
                    if hasattr(obj, "Shape"):
                        shape = obj.Shape
                        break

                if shape is None:
                    raise ValueError(f"No shapes found in {input_file}")

                # Use Mesh module for meshing
                if not HAS_MESH:
                    raise RuntimeError("FreeCAD Mesh module is not available")

                mesh_obj = Mesh.Mesh()
                mesh_obj.addFacets(shape.tessellate(element_size)[1])

                # Export
                mesh_obj.write(output_path)

                num_points = mesh_obj.CountPoints
                num_facets = mesh_obj.CountFacets

                FreeCAD.closeDocument(doc.Name)
            except Exception as exc:
                span.record_exception(exc)
                raise

            elapsed = time.monotonic() - start
            span.set_attribute("operation.duration_s", round(elapsed, 3))

            logger.info(
                "Generated mesh",
                input_file=input_file,
                output_path=output_path,
                num_nodes=num_points,
                num_elements=num_facets,
                duration_s=round(elapsed, 3),
            )

            return {
                "mesh_file": output_path,
                "num_nodes": num_points,
                "num_elements": num_facets,
                "element_types": ["triangle"],
                "quality_metrics": {
                    "element_size": element_size,
                    "algorithm": algorithm,
                },
            }
