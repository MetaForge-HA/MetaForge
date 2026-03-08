"""Assistant Mode — file change detection pipeline and drift reconciler.

Monitors engineer file saves (KiCad, FreeCAD, firmware) and ingests
changes into the Digital Twin graph, keeping file state and graph
state in sync.
"""

from digital_twin.assistant.reconciler import (
    DriftDirection,
    DriftReconciler,
    DriftResult,
    StateLink,
)
from digital_twin.assistant.watcher import FileChangeEvent, FileWatcher

__all__ = [
    "DriftDirection",
    "DriftReconciler",
    "DriftResult",
    "FileChangeEvent",
    "FileWatcher",
    "StateLink",
]
