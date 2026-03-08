"""Skill-specific tests for retrieve_knowledge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from digital_twin.knowledge.store import InMemoryKnowledgeStore, KnowledgeEntry, KnowledgeType
from skill_registry.skill_base import SkillContext

from .handler import RetrieveKnowledgeHandler
from .schema import RetrieveKnowledgeInput


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
    svc.embed.return_value = [1.0, 0.0, 0.0]
    svc.embed_batch.return_value = [[1.0, 0.0, 0.0]]
    return svc


class TestRetrieveKnowledgeSkill:
    """Smoke tests for the retrieve_knowledge handler."""

    async def test_execute_returns_results(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
        mock_embedding: AsyncMock,
    ) -> None:
        entry = KnowledgeEntry(
            content="Use aluminum 6061 for the bracket",
            embedding=[1.0, 0.0, 0.0],
            knowledge_type=KnowledgeType.DESIGN_DECISION,
        )
        await knowledge_store.store(entry)

        handler = RetrieveKnowledgeHandler(mock_context, knowledge_store, mock_embedding)
        inp = RetrieveKnowledgeInput(query="bracket material")
        output = await handler.execute(inp)

        assert output.total_found == 1
        assert output.results[0].content == entry.content
        assert output.query == "bracket material"

    async def test_execute_empty_store(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
        mock_embedding: AsyncMock,
    ) -> None:
        handler = RetrieveKnowledgeHandler(mock_context, knowledge_store, mock_embedding)
        inp = RetrieveKnowledgeInput(query="anything")
        output = await handler.execute(inp)

        assert output.total_found == 0
        assert output.results == []

    async def test_execute_filters_by_type(
        self,
        mock_context: SkillContext,
        knowledge_store: InMemoryKnowledgeStore,
        mock_embedding: AsyncMock,
    ) -> None:
        await knowledge_store.store(
            KnowledgeEntry(
                content="decision content",
                embedding=[1.0, 0.0, 0.0],
                knowledge_type=KnowledgeType.DESIGN_DECISION,
            )
        )
        await knowledge_store.store(
            KnowledgeEntry(
                content="component content",
                embedding=[0.9, 0.1, 0.0],
                knowledge_type=KnowledgeType.COMPONENT,
            )
        )

        handler = RetrieveKnowledgeHandler(mock_context, knowledge_store, mock_embedding)
        inp = RetrieveKnowledgeInput(
            query="test", knowledge_type=KnowledgeType.COMPONENT
        )
        output = await handler.execute(inp)

        assert output.total_found == 1
        assert output.results[0].knowledge_type == KnowledgeType.COMPONENT
