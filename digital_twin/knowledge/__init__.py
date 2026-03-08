"""Knowledge Layer — semantic search and retrieval over design knowledge.

Provides embedding-based storage and retrieval of design decisions,
component datasheets, failure modes, constraints, and session insights.
"""

from digital_twin.knowledge.consumer import KnowledgeConsumer
from digital_twin.knowledge.embedding_service import (
    EmbeddingService,
    LocalEmbeddingService,
    OpenAIEmbeddingService,
    create_embedding_service,
)
from digital_twin.knowledge.store import (
    InMemoryKnowledgeStore,
    KnowledgeEntry,
    KnowledgeStore,
    KnowledgeType,
    PgVectorKnowledgeStore,
)

__all__ = [
    "EmbeddingService",
    "InMemoryKnowledgeStore",
    "KnowledgeConsumer",
    "KnowledgeEntry",
    "KnowledgeStore",
    "KnowledgeType",
    "LocalEmbeddingService",
    "OpenAIEmbeddingService",
    "PgVectorKnowledgeStore",
    "create_embedding_service",
]
