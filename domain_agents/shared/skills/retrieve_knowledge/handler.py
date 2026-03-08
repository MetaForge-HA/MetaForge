"""Handler for the retrieve_knowledge skill."""

from __future__ import annotations

import structlog

from digital_twin.knowledge.embedding_service import EmbeddingService
from digital_twin.knowledge.store import KnowledgeStore
from observability.tracing import get_tracer
from skill_registry.skill_base import SkillBase

from .schema import KnowledgeResult, RetrieveKnowledgeInput, RetrieveKnowledgeOutput

logger = structlog.get_logger(__name__)
tracer = get_tracer("skill.retrieve_knowledge")


class RetrieveKnowledgeHandler(SkillBase[RetrieveKnowledgeInput, RetrieveKnowledgeOutput]):
    """Retrieves relevant knowledge entries via semantic search."""

    input_type = RetrieveKnowledgeInput
    output_type = RetrieveKnowledgeOutput

    def __init__(
        self,
        context: object,
        store: KnowledgeStore,
        embedding_service: EmbeddingService,
    ) -> None:
        super().__init__(context)  # type: ignore[arg-type]
        self._store = store
        self._embedding = embedding_service

    async def execute(self, input_data: RetrieveKnowledgeInput) -> RetrieveKnowledgeOutput:
        """Embed the query and search the knowledge store."""
        with tracer.start_as_current_span("retrieve_knowledge.execute") as span:
            span.set_attribute("skill.name", "retrieve_knowledge")
            span.set_attribute("skill.domain", "shared")

            self.logger.info(
                "retrieve_knowledge_start",
                query=input_data.query[:100],
                knowledge_type=str(input_data.knowledge_type) if input_data.knowledge_type else None,
                limit=input_data.limit,
            )

            query_embedding = await self._embedding.embed(input_data.query)
            entries = await self._store.search(
                embedding=query_embedding,
                knowledge_type=input_data.knowledge_type,
                limit=input_data.limit,
            )

            results = [
                KnowledgeResult(
                    id=e.id,
                    content=e.content,
                    knowledge_type=e.knowledge_type,
                    metadata=e.metadata,
                    source_artifact_id=e.source_artifact_id,
                    created_at=e.created_at,
                )
                for e in entries
            ]

            self.logger.info(
                "retrieve_knowledge_done",
                total_found=len(results),
            )

            return RetrieveKnowledgeOutput(
                results=results,
                query=input_data.query,
                total_found=len(results),
            )
