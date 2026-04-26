"""Knowledge consumer — subscribes to event bus and indexes work_products.

Listens for ``WORK_PRODUCT_CREATED`` and ``WORK_PRODUCT_UPDATED`` events,
extracts textual content, and hands it to a ``KnowledgeService``
implementation (LightRAG by default — see ADR-008).

This module is the L1 ingestion event loop. Per MET-307 / ADR-008, it
depends only on the framework-agnostic ``KnowledgeService`` Protocol so
swapping out the L1 backend never touches the consumer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from digital_twin.knowledge.service import KnowledgeService
from digital_twin.knowledge.types import KnowledgeType
from observability.tracing import get_tracer
from orchestrator.event_bus.events import Event, EventType
from orchestrator.event_bus.subscribers import EventSubscriber

logger = structlog.get_logger(__name__)
tracer = get_tracer("digital_twin.knowledge.consumer")

# Maps work_product type strings to KnowledgeType for auto-classification.
_WORK_PRODUCT_TYPE_MAP: dict[str, KnowledgeType] = {
    "design_decision": KnowledgeType.DESIGN_DECISION,
    "component": KnowledgeType.COMPONENT,
    "constraint": KnowledgeType.CONSTRAINT,
    "failure_mode": KnowledgeType.FAILURE,
    "session": KnowledgeType.SESSION,
}


def _source_path_for(work_product_id: Any) -> str:
    """Stable virtual ``source_path`` used by the L1 dedup key.

    Work products live in the Twin graph, not on disk, but
    ``KnowledgeService`` keys ingest by ``source_path``. Using a
    ``work_product://<uuid>`` URI makes ``delete_by_source`` work for
    update events without inventing a new dedup signal.
    """
    if not work_product_id:
        return "work_product://unknown"
    return f"work_product://{work_product_id}"


class KnowledgeConsumer(EventSubscriber):
    """Event-bus subscriber that indexes work_product events into ``KnowledgeService``.

    On ``WORK_PRODUCT_CREATED`` it ingests the event payload.
    On ``WORK_PRODUCT_UPDATED`` it first deletes any prior chunks
    keyed by the same ``source_path`` (the ``work_product://<id>``
    URI) so re-indexing produces no orphan duplicates.
    """

    def __init__(self, service: KnowledgeService) -> None:
        self._service = service

    @property
    def subscriber_id(self) -> str:
        return "knowledge_consumer"

    @property
    def event_types(self) -> set[EventType] | None:
        return {EventType.WORK_PRODUCT_CREATED, EventType.WORK_PRODUCT_UPDATED}

    async def on_event(self, event: Event) -> None:
        """Ingest the event payload through ``KnowledgeService.ingest``."""
        with tracer.start_as_current_span("knowledge_consumer.on_event") as span:
            span.set_attribute("event.type", str(event.type))
            span.set_attribute("event.id", event.id)
            try:
                content = self._extract_content(event.data)
                if not content:
                    logger.debug(
                        "knowledge_consumer_skip",
                        event_id=event.id,
                        reason="no_content",
                    )
                    return

                knowledge_type = self._classify(event.data)
                source_id = event.data.get("work_product_id")
                source_path = _source_path_for(source_id)

                # On update, drop any prior chunks for this work_product
                # so search hits never return stale content.
                if event.type == EventType.WORK_PRODUCT_UPDATED:
                    try:
                        deleted = await self._service.delete_by_source(source_path)
                        if deleted:
                            logger.debug(
                                "knowledge_consumer_predelete",
                                source_path=source_path,
                                deleted=deleted,
                            )
                    except Exception as exc:  # pragma: no cover — best effort
                        logger.warning(
                            "knowledge_consumer_predelete_failed",
                            source_path=source_path,
                            error=str(exc),
                        )

                wp_uuid = self._coerce_uuid(source_id)
                result = await self._service.ingest(
                    content=content,
                    source_path=source_path,
                    knowledge_type=knowledge_type,
                    source_work_product_id=wp_uuid,
                    metadata={
                        "event_id": event.id,
                        "event_type": str(event.type),
                        "source": event.source,
                    },
                )
                logger.info(
                    "knowledge_consumer_indexed",
                    event_id=event.id,
                    knowledge_type=str(knowledge_type),
                    chunks=result.chunks_indexed,
                    source_path=source_path,
                )
            except Exception as exc:
                span.record_exception(exc)
                logger.error(
                    "knowledge_consumer_error",
                    event_id=event.id,
                    error=str(exc),
                )

    async def ingest_batch(self, items: list[dict[str, Any]]) -> int:
        """Batch-ingest a list of content dicts via the underlying service.

        Each item must have at least ``content``; ``knowledge_type``
        (string), ``source_work_product_id``, and ``metadata`` are
        optional. Returns the count of items that produced ≥ 1 chunk.
        """
        with tracer.start_as_current_span("knowledge_consumer.ingest_batch") as span:
            span.set_attribute("batch.size", len(items))
            ingested = 0
            for item in items:
                content = item.get("content", "")
                if not content:
                    continue
                kt_raw = item.get("knowledge_type", "session")
                try:
                    knowledge_type = KnowledgeType(kt_raw)
                except ValueError:
                    knowledge_type = KnowledgeType.SESSION
                wp_id = item.get("source_work_product_id")
                source_path = item.get("source_path") or _source_path_for(wp_id)
                result = await self._service.ingest(
                    content=content,
                    source_path=source_path,
                    knowledge_type=knowledge_type,
                    source_work_product_id=self._coerce_uuid(wp_id),
                    metadata=item.get("metadata") or {},
                )
                if result.chunks_indexed > 0:
                    ingested += 1
            span.set_attribute("batch.ingested", ingested)
            logger.info("knowledge_batch_ingested", count=ingested, total=len(items))
            return ingested

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        """Extract textual content from event data."""
        for key in ("content", "description", "name", "summary", "text"):
            val = data.get(key)
            if val and isinstance(val, str):
                return val
        props = data.get("properties", {})
        if props and isinstance(props, dict):
            parts = [f"{k}: {v}" for k, v in props.items() if isinstance(v, str)]
            if parts:
                return "; ".join(parts)
        return ""

    @staticmethod
    def _classify(data: dict[str, Any]) -> KnowledgeType:
        """Classify knowledge type from event data."""
        work_product_type = data.get("work_product_type", "")
        return _WORK_PRODUCT_TYPE_MAP.get(work_product_type, KnowledgeType.SESSION)

    @staticmethod
    def _coerce_uuid(value: Any) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None
