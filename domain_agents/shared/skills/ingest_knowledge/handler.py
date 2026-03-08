"""Handler for the ingest_knowledge skill."""

from __future__ import annotations

import structlog

from digital_twin.knowledge.embedding_service import EmbeddingService
from digital_twin.knowledge.store import KnowledgeEntry, KnowledgeStore
from observability.tracing import get_tracer
from skill_registry.skill_base import SkillBase

from .schema import IngestKnowledgeInput, IngestKnowledgeOutput

logger = structlog.get_logger(__name__)
tracer = get_tracer("skill.ingest_knowledge")


class IngestKnowledgeHandler(SkillBase[IngestKnowledgeInput, IngestKnowledgeOutput]):
    """Ingests knowledge by embedding and storing content."""

    input_type = IngestKnowledgeInput
    output_type = IngestKnowledgeOutput

    def __init__(
        self,
        context: object,
        store: KnowledgeStore,
        embedding_service: EmbeddingService,
    ) -> None:
        super().__init__(context)  # type: ignore[arg-type]
        self._store = store
        self._embedding = embedding_service

    async def execute(self, input_data: IngestKnowledgeInput) -> IngestKnowledgeOutput:
        """Embed content and store in the knowledge store."""
        with tracer.start_as_current_span("ingest_knowledge.execute") as span:
            span.set_attribute("skill.name", "ingest_knowledge")
            span.set_attribute("skill.domain", "shared")
            span.set_attribute("knowledge.type", str(input_data.knowledge_type))

            self.logger.info(
                "ingest_knowledge_start",
                content_length=len(input_data.content),
                knowledge_type=str(input_data.knowledge_type),
            )

            # Embed the content
            embedded = False
            embedding: list[float] = []
            try:
                embedding = await self._embedding.embed(input_data.content)
                embedded = len(embedding) > 0 and any(v != 0.0 for v in embedding)
            except Exception as exc:
                span.record_exception(exc)
                self.logger.warning(
                    "ingest_knowledge_embed_failed",
                    error=str(exc),
                )

            entry = KnowledgeEntry(
                content=input_data.content,
                embedding=embedding,
                knowledge_type=input_data.knowledge_type,
                metadata=input_data.metadata,
                source_artifact_id=input_data.source_artifact_id,
            )
            stored = await self._store.store(entry)

            self.logger.info(
                "ingest_knowledge_done",
                entry_id=str(stored.id),
                embedded=embedded,
            )

            return IngestKnowledgeOutput(
                entry_id=stored.id,
                embedded=embedded,
            )
