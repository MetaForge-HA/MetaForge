"""DesignElement node — a logical design block with AAS-aligned parameters."""

from uuid import UUID, uuid4

from pydantic import Field

from twin_core.models.base import NodeBase
from twin_core.models.enums import NodeType


class DesignElement(NodeBase):
    """A logical design element (sub-assembly, module, functional block).

    Captures design-level parameters that can carry AAS-aligned keys such as
    ``hardwareVersion`` and ``softwareVersion`` in the ``parameters`` dict.
    """

    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType = NodeType.DESIGN_ELEMENT
    name: str
    element_type: str = ""
    domain: str = ""
    parameters: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
