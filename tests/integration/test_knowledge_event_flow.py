"""End-to-end knowledge event-flow tests (MET-307).

Opt in with ``pytest --integration``. Requires the dev
``metaforge-postgres-1`` (with the ``vector`` extension) running on
``localhost:5432`` and the default credentials.

These tests prove that:

* Publishing a ``WORK_PRODUCT_CREATED`` event to the gateway's bus
  results in a ``KnowledgeService.ingest`` call (the consumer is
  actually subscribed at boot).
* A subsequent ``WORK_PRODUCT_UPDATED`` for the same
  ``work_product_id`` does **not** create orphan duplicates — the
  consumer pre-deletes by source path before re-ingesting.
* The new content is searchable end-to-end via
  ``KnowledgeService.search``.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from digital_twin.knowledge import create_knowledge_service
from digital_twin.knowledge.consumer import KnowledgeConsumer
from orchestrator.event_bus.events import Event, EventType
from orchestrator.event_bus.subscribers import EventBus, create_default_bus

pytestmark = pytest.mark.integration


_DEFAULT_DSN = "postgresql://metaforge:metaforge@localhost:5432/metaforge"


def _dsn() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_DSN).replace(
        "postgresql+asyncpg://", "postgresql://"
    )


def _make_event(event_type: EventType, work_product_id: uuid.UUID, content: str) -> Event:
    return Event(
        id=str(uuid.uuid4()),
        type=event_type,
        timestamp=datetime.now(UTC).isoformat(),
        source="test-event-flow",
        data={
            "content": content,
            "work_product_type": "design_decision",
            "work_product_id": work_product_id,
        },
    )


@pytest.fixture
async def service(tmp_path: Path) -> AsyncIterator[object]:
    """One LightRAG service per test, namespaced to avoid collisions."""
    suffix = uuid.uuid4().hex[:8]
    svc = create_knowledge_service(
        "lightrag",
        working_dir=str(tmp_path / f"lightrag-{suffix}"),
        postgres_dsn=_dsn(),
        namespace_prefix=f"lightrag_evt_{suffix}",
    )
    await svc.initialize()  # type: ignore[attr-defined]
    try:
        yield svc
    finally:
        await svc.close()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Subscription wiring
# ---------------------------------------------------------------------------


class TestSubscription:
    async def test_default_bus_subscribes_consumer_when_service_provided(
        self, service: object
    ) -> None:
        bus = create_default_bus(workflow_engine=None, knowledge_service=service)  # type: ignore[arg-type]
        consumer_ids = [s.subscriber_id for s in bus._subscribers.values()]  # noqa: SLF001
        assert "knowledge_consumer" in consumer_ids

    async def test_default_bus_skips_consumer_without_service(self) -> None:
        bus = create_default_bus(workflow_engine=None, knowledge_service=None)
        consumer_ids = [s.subscriber_id for s in bus._subscribers.values()]  # noqa: SLF001
        assert "knowledge_consumer" not in consumer_ids


# ---------------------------------------------------------------------------
# End-to-end event flow
# ---------------------------------------------------------------------------


async def _count_chunks_for_wp(workspace: str, wp_id: uuid.UUID) -> int:
    """Direct PG count of chunks tagged with ``wp_id`` in ``workspace``.

    Bypasses the cosine-search threshold so the test asserts wiring (did
    the consumer call ``ingest``?), not retrieval ranking.
    """
    import asyncpg  # type: ignore[import-untyped]

    conn = await asyncpg.connect(_dsn())
    try:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM lightrag_vdb_chunks WHERE workspace = $1 AND file_path LIKE $2",
            workspace,
            f"%work_product://{wp_id}%",
        )
    finally:
        await conn.close()


class TestEventFlow:
    async def test_create_event_ingests_into_service(self, service: object) -> None:
        bus = EventBus()
        bus.subscribe(KnowledgeConsumer(service=service))  # type: ignore[arg-type]
        workspace = service._cfg.namespace_prefix  # type: ignore[attr-defined]

        wp_id = uuid.uuid4()
        content = (
            f"Design decision {wp_id.hex[:8]}. We choose titanium grade 5 for the "
            "SR-7 mounting bracket. The previous aluminium 6061 prototype failed "
            "thermal-cycle testing. Approved by mechanical lead on 2026-04-12."
        )
        await bus.publish(_make_event(EventType.WORK_PRODUCT_CREATED, wp_id, content))
        # First-call after fixture init occasionally needs a longer flush
        # window before the chunk is visible from a fresh asyncpg
        # connection. Poll up to 5 s before giving up.
        chunk_count = 0
        for _ in range(10):
            chunk_count = await _count_chunks_for_wp(workspace, wp_id)
            if chunk_count >= 1:
                break
            await asyncio.sleep(0.5)
        assert chunk_count >= 1, f"expected ≥1 chunk, got {chunk_count}"

        # And confirm the round-trip: search for unambiguous tokens.
        hits = await service.search("titanium grade 5 SR-7 mounting bracket", top_k=10)  # type: ignore[attr-defined]
        assert any(h.source_work_product_id == wp_id for h in hits), [
            (str(h.source_work_product_id), h.source_path) for h in hits
        ]

    async def test_update_event_replaces_prior_content(self, service: object) -> None:
        """Updating a work product must drop stale chunks before ingesting."""
        bus = EventBus()
        bus.subscribe(KnowledgeConsumer(service=service))  # type: ignore[arg-type]
        workspace = service._cfg.namespace_prefix  # type: ignore[attr-defined]

        wp_id = uuid.uuid4()
        old_content = (
            f"Document {wp_id.hex[:8]}. The aluminium 6061 prototype was the "
            "original baseline. It failed pull-out testing after 200 thermal "
            "cycles between -20 °C and 85 °C."
        )
        new_content = (
            f"Document {wp_id.hex[:8]}. Replaced with titanium grade 5 plus "
            "Helicoil thread inserts. Predicted thermal-cycle life now exceeds "
            "5000 cycles per the supplier datasheet."
        )

        await bus.publish(_make_event(EventType.WORK_PRODUCT_CREATED, wp_id, old_content))
        await asyncio.sleep(0.5)
        chunks_after_create = await _count_chunks_for_wp(workspace, wp_id)
        assert chunks_after_create >= 1

        await bus.publish(_make_event(EventType.WORK_PRODUCT_UPDATED, wp_id, new_content))
        await asyncio.sleep(0.5)

        # After update we must have chunks (the new content), but no stale
        # rows containing the old "aluminium 6061" sentence — the consumer
        # is required to delete_by_source before re-ingesting.
        import asyncpg  # type: ignore[import-untyped]

        conn = await asyncpg.connect(_dsn())
        try:
            stale = await conn.fetchval(
                "SELECT COUNT(*) FROM lightrag_vdb_chunks "
                "WHERE workspace = $1 AND file_path LIKE $2 "
                "  AND content LIKE '%aluminium 6061 prototype was the original%'",
                workspace,
                f"%work_product://{wp_id}%",
            )
            fresh = await conn.fetchval(
                "SELECT COUNT(*) FROM lightrag_vdb_chunks "
                "WHERE workspace = $1 AND file_path LIKE $2 "
                "  AND content LIKE '%Helicoil thread inserts%'",
                workspace,
                f"%work_product://{wp_id}%",
            )
        finally:
            await conn.close()
        assert stale == 0, f"stale chunks survived update: {stale}"
        assert fresh >= 1, f"fresh chunks missing after update: {fresh}"
