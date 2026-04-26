"""Shared knowledge-layer types.

Re-exports ``KnowledgeType`` so the public interface in ``service.py`` does
not depend on the legacy ``store.py`` module, which is on a deprecation
path. New callers should import ``KnowledgeType`` from here.
"""

from digital_twin.knowledge.store import KnowledgeType

__all__ = ["KnowledgeType"]
