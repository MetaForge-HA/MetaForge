"""Unit tests for the L1 ``KnowledgeService`` interface (MET-346).

No I/O. Verifies the dataclasses' construction shape and that the
LightRAG adapter satisfies the runtime-checkable Protocol. Also locks
the factory contract so callers can rely on `create_knowledge_service`.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from digital_twin.knowledge import create_knowledge_service
from digital_twin.knowledge.lightrag_service import LightRAGKnowledgeService
from digital_twin.knowledge.service import (
    IngestResult,
    KnowledgeService,
    SearchHit,
)

# ---------------------------------------------------------------------------
# Dataclass conformance
# ---------------------------------------------------------------------------


class TestSearchHit:
    def test_search_hit_defaults(self) -> None:
        hit = SearchHit(
            content="text",
            similarity_score=0.5,
            source_path=None,
            heading=None,
            chunk_index=None,
            total_chunks=None,
        )
        assert hit.metadata == {}
        assert hit.knowledge_type is None
        assert hit.source_work_product_id is None

    def test_search_hit_accepts_all_fields(self) -> None:
        from digital_twin.knowledge.types import KnowledgeType

        wp_id = uuid4()
        hit = SearchHit(
            content="text",
            similarity_score=0.9,
            source_path="docs/decision.md",
            heading="## Decision",
            chunk_index=2,
            total_chunks=5,
            metadata={"author": "mech"},
            knowledge_type=KnowledgeType.DESIGN_DECISION,
            source_work_product_id=wp_id,
        )
        assert hit.heading == "## Decision"
        assert hit.knowledge_type == KnowledgeType.DESIGN_DECISION
        assert hit.source_work_product_id == wp_id


class TestIngestResult:
    def test_ingest_result_constructs_with_uuid_list(self) -> None:
        ids = [uuid4(), uuid4(), uuid4()]
        result = IngestResult(
            entry_ids=ids,
            chunks_indexed=3,
            source_path="docs/a.md",
        )
        assert result.entry_ids == ids
        assert result.chunks_indexed == 3
        assert result.source_path == "docs/a.md"


# ---------------------------------------------------------------------------
# Protocol conformance + factory
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_lightrag_service_satisfies_protocol(self) -> None:
        # Construct without ``initialize()`` — the Protocol check is
        # structural, so no real backend is needed.
        service = LightRAGKnowledgeService(working_dir="/tmp/lightrag-protocol-check")
        assert isinstance(service, KnowledgeService)


class TestFactory:
    def test_factory_returns_lightrag_when_requested(self) -> None:
        service = create_knowledge_service("lightrag", working_dir="/tmp/lightrag-factory-check")
        assert type(service).__name__ == "LightRAGKnowledgeService"
        assert isinstance(service, KnowledgeService)

    def test_factory_default_is_lightrag(self) -> None:
        service = create_knowledge_service(working_dir="/tmp/lightrag-default-check")
        assert type(service).__name__ == "LightRAGKnowledgeService"

    def test_factory_raises_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="nonexistent"):
            create_knowledge_service("nonexistent")  # type: ignore[arg-type]

    def test_factory_llamaindex_not_implemented(self) -> None:
        # Documented fallback: ADR-008 leaves room for a LlamaIndex
        # adapter. It is not implemented in MET-346 — surfacing a clear
        # error keeps callers honest until it lands.
        with pytest.raises(NotImplementedError, match="llamaindex"):
            create_knowledge_service("llamaindex")
