"""Agent models for the Digital Twin.

Agent nodes record which agent produced or modified artifacts,
connecting the provenance chain from human intent through agent execution
to artifact output.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentNode(BaseModel):
    """An agent execution session node in the Digital Twin graph.

    Attributes:
        id: Unique identifier (auto-generated)
        agent_type: Agent discipline (e.g., "mechanical", "electronics")
        domain: Engineering domain this agent covers
        session_id: Current execution session
        skills_used: Skill IDs invoked during this session
        started_at: Session start time
        completed_at: Session completion time
        status: "running", "completed", or "failed"
    """

    id: UUID = Field(default_factory=uuid4)
    agent_type: str
    domain: str
    session_id: UUID
    skills_used: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: str = "running"

    def mark_completed(self) -> None:
        """Mark the agent session as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        """Mark the agent session as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc)

    def to_neo4j_props(self) -> dict:
        """Convert to Neo4j node properties."""
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "domain": self.domain,
            "session_id": str(self.session_id),
            "skills_used": self.skills_used,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
        }

    @classmethod
    def from_neo4j_props(cls, props: dict) -> "AgentNode":
        """Create AgentNode from Neo4j node properties."""
        return cls(
            id=UUID(props["id"]),
            agent_type=props["agent_type"],
            domain=props["domain"],
            session_id=UUID(props["session_id"]),
            skills_used=props.get("skills_used", []),
            started_at=datetime.fromisoformat(props["started_at"]),
            completed_at=datetime.fromisoformat(props["completed_at"])
            if props.get("completed_at")
            else None,
            status=props.get("status", "running"),
        )
