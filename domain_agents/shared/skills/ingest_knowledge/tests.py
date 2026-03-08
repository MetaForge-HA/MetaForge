"""Skill-specific tests for ingest_knowledge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from digital_twin.knowledge.store import InMemoryKnowledgeStore, KnowledgeType
from skill_registry.skill_base import SkillContext

from .handler import IngestKnowledgeHandler
from .schema import IngestKnowledgeInput


@pytest.fixture()
def mock_context() -> SkillContext:
    ctx = MagicMock(spec=SkillContext)
    ctx.twin = AsyncMock()
    ctx.mcp = MagicMock()
    ctx.logger = MagicMock()
    ctx.logger.bind = MagicMock(return_value=ctx.logger)
    ctx.session_id = uuid4()
    ctx.branch = "main"
    return ctx


@pytest.fixture()
def knowledge_store() -> InMemoryKnowledgeStore:
    return InMemoryKnowledgeStore()


@pytest.fixture()
def mock_embedding() -> AsyncMock:
    svc = AsyncMock()
    svc.embed.return_value = [0.5, 0.5, 0.0]
    svc.embed_batch.return_value = [[0.5, 0.5, 0.0]]
    return svc


class TestIngestKnowledgeSkill:
    """Smoke tests for the ingest_knowledge handler."""

    async def test_execute_stores_entry(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
        mock_embedding: AsyncMock,
    ) -> None:
        handler = IngestKnowledgeHandler(mock_context, knowledge_store, mock_embedding)
        inp = IngestKnowledgeInput(
            content="Use M3 screws for the enclosure",
            knowledge_type=KnowledgeType.DESIGN_DECISION,
            metadata={"source": "review"},
        )
        output = await handler.execute(inp)

        assert output.embedded is True
        assert output.entry_id is not None

        stored = await knowledge_store.get(output.entry_id)
        assert stored is not None
        assert stored.content == "Use M3 screws for the enclosure"

    async def test_execute_handles_embed_failure(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
    ) -> None:
        failing_embedding = AsyncMock()
        failing_embedding.embed.side_effect = RuntimeError("model not loaded")

        handler = IngestKnowledgeHandler(mock_context, knowledge_store, failing_embedding)
        inp = IngestKnowledgeInput(
            content="Some content",
            knowledge_type=KnowledgeType.SESSION,
        )
        output = await handler.execute(inp)

        # Entry should still be stored, just not embedded
        assert output.embedded is False
        stored = await knowledge_store.get(output.entry_id)
        assert stored is not None

    async def test_execute_with_artifact_id(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
        mock_embedding: AsyncMock,
    ) -> None:
        artifact_id = uuid4()
        handler = IngestKnowledgeHandler(mock_context, knowledge_store, mock_embedding)
        inp = IngestKnowledgeInput(
            content="Component datasheet content",
            knowledge_type=KnowledgeType.COMPONENT,
            source_artifact_id=artifact_id,
        )
        output = await handler.execute(inp)

        stored = await knowledge_store.get(output.entry_id)
        assert stored is not None
        assert stored.source_artifact_id == artifact_id
