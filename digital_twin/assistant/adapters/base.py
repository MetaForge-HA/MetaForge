"""Base adapter interface for file change parsing.

Every domain adapter (KiCad, FreeCAD, firmware) inherits from
``FileChangeAdapter`` and implements ``parse_change`` to convert a
``FileChangeEvent`` into a list of ``GraphMutation`` objects describing
how the Digital Twin graph should be updated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from digital_twin.assistant.watcher import FileChangeEvent


class MutationType(StrEnum):
    """Kind of graph operation."""

    NODE_CREATED = "node_created"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"
    EDGE_CREATED = "edge_created"
    EDGE_DELETED = "edge_deleted"


class GraphMutation(BaseModel):
    """A single proposed change to the Digital Twin graph."""

    mutation_type: MutationType
    node_type: str
    node_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_file: str


class FileChangeAdapter(ABC):
    """Abstract base class for domain-specific file change adapters."""

    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """File extensions this adapter can handle."""
        ...

    @abstractmethod
    async def parse_change(self, event: FileChangeEvent) -> list[GraphMutation]:
        """Parse a file change event into graph mutations.

        Implementations must handle parse errors gracefully (return an
        empty list and log the error) rather than raising exceptions.
        """
        ...
