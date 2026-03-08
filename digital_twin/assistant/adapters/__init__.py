"""Domain-specific file change adapters for the assistant pipeline.

Each adapter knows how to parse a specific file format and produce
``GraphMutation`` objects that describe changes to the Digital Twin.
"""

from digital_twin.assistant.adapters.base import FileChangeAdapter, GraphMutation, MutationType
from digital_twin.assistant.adapters.firmware_adapter import FirmwareAdapter
from digital_twin.assistant.adapters.freecad_adapter import FreecadAdapter
from digital_twin.assistant.adapters.kicad_adapter import KicadAdapter

__all__ = [
    "FileChangeAdapter",
    "FirmwareAdapter",
    "FreecadAdapter",
    "GraphMutation",
    "KicadAdapter",
    "MutationType",
]
