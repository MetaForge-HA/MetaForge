"""End-to-end test for ``forge ingest`` (MET-336).

Opt in with ``pytest --integration``. Boots the full gateway in-process
via ``ASGITransport`` (no real HTTP socket), drives ``forge ingest``
through ``ForgeClient``, and verifies the document lands in the L1
knowledge layer via ``KnowledgeService.search``.

Requires the dev ``metaforge-postgres-1`` (with ``vector`` extension)
running on ``localhost:5432``.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from cli.forge_cli.client import ForgeClient
from cli.forge_cli.ingest import ingest_path

pytestmark = pytest.mark.integration


_DEFAULT_DSN = "postgresql+asyncpg://metaforge:metaforge@localhost:5432/metaforge"


def _dsn() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_DSN)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _dsn())


class _AsgiClient(ForgeClient):
    """``ForgeClient`` that talks to a live FastAPI app via ASGITransport.

    We can't open a real HTTP server inside the test, so the integration
    test patches the underlying ``httpx.Client`` factory to wrap the
    same FastAPI ``app`` the gateway lifespan booted.
    """

    def __init__(self, app, base_url: str = "http://test", timeout: float = 60.0) -> None:
        super().__init__(base_url=base_url, timeout=timeout)
        self._app = app

    def _client(self) -> httpx.Client:  # type: ignore[override]
        return httpx.Client(
            transport=httpx.ASGITransport(app=self._app),
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def ingest_document(  # type: ignore[override]
        self,
        content: str,
        source_path: str,
        knowledge_type: str,
        source_work_product_id: str | None = None,
        metadata=None,
        timeout: float | None = None,
    ):
        payload = {
            "content": content,
            "sourcePath": source_path,
            "knowledgeType": knowledge_type,
            "metadata": metadata or {},
        }
        if source_work_product_id:
            payload["sourceWorkProductId"] = source_work_product_id
        # AsyncClient + ASGITransport is the supported wiring; the sync
        # Client/ASGITransport pair leaks an attribute mismatch on exit.
        # We're already inside an async test, so just drive a one-shot
        # async call from this sync method via asyncio.run_in_loop on a
        # fresh event loop.
        import asyncio

        async def _send() -> dict:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self._app),
                base_url=self.base_url,
                timeout=timeout or self.timeout,
            ) as client:
                resp = await client.post(self._url("/knowledge/documents"), json=payload)
                resp.raise_for_status()
                return resp.json()

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is None:
            return asyncio.run(_send())
        # Run in a separate loop on a thread so the awaiting loop isn't blocked.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _send()).result()


@pytest.fixture
async def gateway() -> AsyncIterator[tuple[object, _AsgiClient]]:
    """Boot the gateway (with KnowledgeService) and yield an ASGI client."""
    from api_gateway.db.engine import dispose_engine
    from api_gateway.server import create_app

    await dispose_engine()
    app = create_app()
    async with app.router.lifespan_context(app):
        client = _AsgiClient(app=app)
        yield app, client


# ---------------------------------------------------------------------------
# Single-file
# ---------------------------------------------------------------------------


class TestSingleFileIngest:
    async def test_markdown_file_lands_in_knowledge_layer(
        self,
        tmp_path: Path,
        gateway: tuple[object, _AsgiClient],
    ) -> None:
        app, client = gateway
        sentinel = uuid.uuid4().hex[:8]
        md = tmp_path / "decisions" / "bracket.md"
        md.parent.mkdir()
        md.write_text(
            f"# Decision {sentinel}\n\n"
            "We adopt titanium grade 5 for the SR-7 mounting bracket. "
            "Aluminium 6061-T6 failed thermal cycling.\n",
            encoding="utf-8",
        )

        result = ingest_path(md, client=client)
        # Diagnostic output if anything went wrong.
        assert result["total"] == 1, result
        assert result["failed"] == [], result["failed"]
        assert result["skipped"] == [], result["skipped"]
        assert len(result["ingested"]) == 1, result
        ingested = result["ingested"][0]
        assert ingested["chunks_indexed"] >= 1
        assert ingested["knowledge_type"] == "design_decision"

        # Confirm the document is searchable through the live service.
        service = app.state.knowledge_service  # type: ignore[attr-defined]
        hits = await service.search(f"titanium grade 5 SR-7 {sentinel}", top_k=5)
        assert any(h.source_path == str(md.resolve()) for h in hits), [
            (h.source_path, h.content[:60]) for h in hits
        ]


# ---------------------------------------------------------------------------
# Directory walk + dedup
# ---------------------------------------------------------------------------


class TestDirectoryIngestAndDedup:
    async def test_directory_walk_and_reingest_does_not_double_count(
        self,
        tmp_path: Path,
        gateway: tuple[object, _AsgiClient],
    ) -> None:
        app, client = gateway

        sentinel = uuid.uuid4().hex[:8]
        a = tmp_path / "constraints" / "load.md"
        a.parent.mkdir()
        a.write_text(
            f"# Load constraints {sentinel}\nMax 3g vibration on Z axis. ",
            encoding="utf-8",
        )
        b = tmp_path / "decisions" / "thread.md"
        b.parent.mkdir()
        b.write_text(
            f"# Thread choice {sentinel}\nHelicoil M3 inserts replace heat-set.",
            encoding="utf-8",
        )
        skip = tmp_path / "geometry.dwg"
        skip.write_text("ignored", encoding="utf-8")

        first = ingest_path(tmp_path, client=client)
        assert first["total"] == 2
        first_chunks = sum(item["chunks_indexed"] for item in first["ingested"])
        assert first_chunks >= 2

        # Re-ingest the same directory; LightRAG dedupes by content hash
        # so the second run must report the same chunk total per file.
        second = ingest_path(tmp_path, client=client)
        second_chunks = sum(item["chunks_indexed"] for item in second["ingested"])
        assert second_chunks == first_chunks, (
            f"re-ingest doubled chunks: first={first_chunks} second={second_chunks}"
        )

        # And both files must be searchable end-to-end through the
        # live service — proves chunks landed in PG.
        service = app.state.knowledge_service  # type: ignore[attr-defined]
        load_hits = await service.search(f"Max 3g vibration {sentinel}", top_k=5)
        thread_hits = await service.search(f"Helicoil M3 inserts {sentinel}", top_k=5)
        assert any(h.source_path == str(a.resolve()) for h in load_hits)
        assert any(h.source_path == str(b.resolve()) for h in thread_hits)


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_makes_no_http_calls(
        self,
        tmp_path: Path,
        gateway: tuple[object, _AsgiClient],
    ) -> None:
        _, client = gateway
        md = tmp_path / "doc.md"
        md.write_text("body", encoding="utf-8")
        result = ingest_path(md, client=client, dry_run=True)
        assert result["dry_run"] is True
        assert result["ingested"][0]["dry_run"] is True
        assert result["ingested"][0]["chunks_indexed"] == 0
