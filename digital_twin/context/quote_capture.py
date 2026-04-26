"""Supplier quote capture + price history (MET-329).

Records the exact pricing/availability snapshot returned by every
distributor query (Digi-Key, Mouser, Nexar) so cost engineers and the
agent that picks alternates can answer "how has this part priced over
six months?" without re-hitting the API.

Two responsibilities, kept on the digital_twin side of the layer line:

1. **Capture** — accept a ``SupplierQuote`` from a caller (typically
   the supply-chain agent's risk scorer wrapping a
   ``DistributorAdapter`` call) and persist it as a time-series row.
   Optionally publishes a `KnowledgeType.COMPONENT` knowledge entry so
   "selected at $X on date Y" becomes searchable in the assembler.
2. **Price history** — answer ``price_history(mpn, supplier?, since?)``
   with the captured rows in chronological order. The supply-chain
   agent uses this to detect price spikes and flag NRND/EOL transitions
   without re-paying the API rate-limit cost.

Layer note: ``digital_twin/`` may not import from ``tool_registry`` /
``domain_agents`` per its CLAUDE.md, so this module never invokes a
distributor SDK directly. The caller in ``domain_agents/supply_chain``
wraps each adapter call and passes the captured payload here.

Pattern note: deliberately mirrors ``simulation_capture.py`` (MET-331)
— same in-memory recorder + similarity/lookup pattern, same sync
convenience wrapper, same knowledge-publish hook. A real backing store
(Postgres time-series) lands as a follow-up; the in-memory store is
enough for unit tests and gateway boot.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from digital_twin.knowledge.service import KnowledgeService
from digital_twin.knowledge.types import KnowledgeType
from observability.tracing import get_tracer

__all__ = [
    "PriceHistory",
    "QuoteCapture",
    "QuoteLifecycleStatus",
    "SupplierQuote",
]

logger = structlog.get_logger(__name__)
tracer = get_tracer("digital_twin.context.quote_capture")


class QuoteLifecycleStatus(BaseModel):
    """Lifecycle bucket — string-equivalent to
    ``tool_registry.tools.distributors.base.LifecycleStatus`` so values
    round-trip from the adapter without coupling the layers."""

    value: str = Field(default="UNKNOWN", description="ACTIVE / NRND / EOL / OBSOLETE / UNKNOWN")


class SupplierQuote(BaseModel):
    """One pricing/availability snapshot from a distributor.

    Models a single point on the price-history curve. Captures the full
    quote tier list so the agent can re-derive marginal cost at any
    quantity break without re-hitting the API.
    """

    id: UUID = Field(default_factory=uuid4)
    mpn: str = Field(..., min_length=1, description="Manufacturer Part Number")
    supplier: str = Field(..., min_length=1, description="`digikey`, `mouser`, `nexar`, ...")
    distributor_pn: str = Field(default="", description="Distributor-specific part number")
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    unit_price: float | None = Field(
        default=None,
        ge=0,
        description="Marginal unit price at the *quoted* qty (not necessarily MOQ)",
    )
    currency: str = Field(default="USD", description="ISO 4217")
    quote_quantity: int | None = Field(
        default=None,
        ge=1,
        description="Quantity the unit_price was quoted at",
    )
    pricing_tiers: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Full price-break ladder: each entry has at minimum "
            "``quantity`` and ``unit_price``. Round-trips the "
            "DistributorAdapter PricingBreak shape verbatim."
        ),
    )
    stock_qty: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    minimum_order_qty: int | None = Field(default=None, ge=1)
    lifecycle_status: str = Field(default="UNKNOWN")
    bom_item_id: UUID | None = Field(
        default=None,
        description="Optional link to the BOM line that triggered the query",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class PriceHistory(BaseModel):
    """Aggregate price-history view for one (mpn, supplier?) pair."""

    mpn: str
    supplier: str | None = Field(default=None, description="None = across all suppliers")
    quotes: list[SupplierQuote] = Field(default_factory=list)

    @property
    def first_seen_at(self) -> datetime | None:
        return self.quotes[0].captured_at if self.quotes else None

    @property
    def last_seen_at(self) -> datetime | None:
        return self.quotes[-1].captured_at if self.quotes else None

    @property
    def min_unit_price(self) -> float | None:
        prices = [q.unit_price for q in self.quotes if q.unit_price is not None]
        return min(prices) if prices else None

    @property
    def max_unit_price(self) -> float | None:
        prices = [q.unit_price for q in self.quotes if q.unit_price is not None]
        return max(prices) if prices else None

    def trend_pct(self) -> float | None:
        """Relative change between the first and most recent unit price.

        Returns ``None`` when fewer than two priced quotes exist.
        Positive means the price went up; ``0.10`` is a 10% increase.
        """
        priced = [q for q in self.quotes if q.unit_price]
        if len(priced) < 2:
            return None
        first = priced[0].unit_price or 0.0
        last = priced[-1].unit_price or 0.0
        if first == 0:
            return None
        return (last - first) / first


class QuoteCapture:
    """In-memory recorder + time-series lookup for ``SupplierQuote`` rows.

    Mirrors ``SimulationCapture`` (MET-331) — same construction, same
    optional ``KnowledgeService`` push, same sync convenience wrapper.
    A Postgres-backed time-series store is a single-class swap-out.
    """

    def __init__(self, knowledge_service: KnowledgeService | None = None) -> None:
        self._quotes: list[SupplierQuote] = []
        self._knowledge_service = knowledge_service

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    async def record_quote(self, quote: SupplierQuote) -> SupplierQuote:
        """Persist a quote; push a component-rationale entry when wired."""
        with tracer.start_as_current_span("quote.record_quote") as span:
            self._quotes.append(quote)
            span.set_attribute("quote.id", str(quote.id))
            span.set_attribute("quote.mpn", quote.mpn)
            span.set_attribute("quote.supplier", quote.supplier)
            if quote.unit_price is not None:
                span.set_attribute("quote.unit_price", quote.unit_price)

            if self._knowledge_service is not None:
                await self._publish_rationale(quote)

            logger.info(
                "quote_recorded",
                quote_id=str(quote.id),
                mpn=quote.mpn,
                supplier=quote.supplier,
                unit_price=quote.unit_price,
                stock_qty=quote.stock_qty,
                lifecycle=quote.lifecycle_status,
            )
            return quote

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def price_history(
        self,
        mpn: str,
        supplier: str | None = None,
        since: datetime | None = None,
    ) -> PriceHistory:
        """Return chronological history for one ``(mpn, supplier?)`` pair.

        ``since`` filters the lower bound (inclusive). Pass
        ``timedelta(days=180)`` worth of cutoff for the spec's "how
        has this part priced over 6 months?" query.
        """
        rows = [
            q
            for q in self._quotes
            if q.mpn == mpn
            and (supplier is None or q.supplier == supplier)
            and (since is None or q.captured_at >= since)
        ]
        rows.sort(key=lambda q: q.captured_at)
        return PriceHistory(mpn=mpn, supplier=supplier, quotes=rows)

    def all_quotes(self) -> list[SupplierQuote]:
        """Read-only snapshot of every captured quote."""
        return list(self._quotes)

    def quotes_for_bom_item(self, bom_item_id: UUID) -> list[SupplierQuote]:
        """Every quote captured against this BOM line, chronological."""
        rows = [q for q in self._quotes if q.bom_item_id == bom_item_id]
        rows.sort(key=lambda q: q.captured_at)
        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rationale_summary(quote: SupplierQuote) -> str:
        price_bit = (
            f" at ${quote.unit_price:.4f} {quote.currency}"
            if quote.unit_price is not None
            else " (no price)"
        )
        qty_bit = f" / qty {quote.quote_quantity}" if quote.quote_quantity else ""
        stock_bit = f", stock {quote.stock_qty}" if quote.stock_qty is not None else ""
        lifecycle_bit = (
            f", lifecycle {quote.lifecycle_status}"
            if quote.lifecycle_status and quote.lifecycle_status != "UNKNOWN"
            else ""
        )
        return (
            f"Quote for {quote.mpn} from {quote.supplier}"
            f"{price_bit}{qty_bit}{stock_bit}{lifecycle_bit} "
            f"on {quote.captured_at.date().isoformat()}"
        )

    async def _publish_rationale(self, quote: SupplierQuote) -> None:
        if self._knowledge_service is None:
            return
        try:
            await self._knowledge_service.ingest(
                content=self._rationale_summary(quote),
                source_path=f"supplier_quote://{quote.id}",
                knowledge_type=KnowledgeType.COMPONENT,
                source_work_product_id=quote.bom_item_id,
                metadata={
                    "quote_id": str(quote.id),
                    "mpn": quote.mpn,
                    "supplier": quote.supplier,
                    "distributor_pn": quote.distributor_pn,
                    "unit_price": quote.unit_price,
                    "currency": quote.currency,
                    "stock_qty": quote.stock_qty,
                    "lifecycle_status": quote.lifecycle_status,
                    "bom_item_id": str(quote.bom_item_id) if quote.bom_item_id else None,
                    "captured_at": quote.captured_at.isoformat(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.warning(
                "quote_knowledge_publish_failed",
                quote_id=str(quote.id),
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Sync convenience
    # ------------------------------------------------------------------

    def record_quote_sync(self, quote: SupplierQuote) -> SupplierQuote:
        """Blocking wrapper for non-async callers (CLI, scripts)."""
        return asyncio.run(self.record_quote(quote))


# ---------------------------------------------------------------------------
# Module helpers — compose a SupplierQuote from a DistributorAdapter response
# ---------------------------------------------------------------------------


def quote_from_adapter_payload(
    *,
    mpn: str,
    supplier: str,
    pricing: Iterable[Any],
    availability: Any | None = None,
    distributor_pn: str = "",
    quote_quantity: int | None = None,
    bom_item_id: UUID | None = None,
    lifecycle_status: str = "UNKNOWN",
    metadata: dict[str, Any] | None = None,
) -> SupplierQuote:
    """Convenience composer for callers that hold a list of
    ``DistributorAdapter.PricingBreak`` and an ``AvailabilityInfo``.

    Lives here (not in ``tool_registry``) so the adapter layer never
    needs to know the storage shape; supply-chain code constructs the
    ``SupplierQuote`` and hands it to ``QuoteCapture.record_quote``.
    """
    tiers: list[dict[str, Any]] = []
    selected_unit_price: float | None = None
    for pb in pricing:
        qty = getattr(pb, "quantity", None)
        unit_price = getattr(pb, "unit_price", None)
        if qty is None or unit_price is None:
            continue
        tier = {
            "quantity": int(qty),
            "unit_price": float(unit_price),
            "currency": getattr(pb, "currency", "USD"),
        }
        tiers.append(tier)
        # Pick the tier whose qty is ≤ requested quote_quantity, else
        # the cheapest-per-unit tier (highest qty break).
        if quote_quantity is not None and qty <= quote_quantity:
            selected_unit_price = float(unit_price)
    if selected_unit_price is None and tiers:
        selected_unit_price = max(tiers, key=lambda t: t["quantity"])["unit_price"]

    stock_qty = getattr(availability, "stock_qty", None) if availability else None
    lead_time = getattr(availability, "lead_time_days", None) if availability else None
    moq = getattr(availability, "minimum_order_qty", None) if availability else None

    return SupplierQuote(
        mpn=mpn,
        supplier=supplier,
        distributor_pn=distributor_pn,
        unit_price=selected_unit_price,
        quote_quantity=quote_quantity,
        pricing_tiers=tiers,
        stock_qty=stock_qty,
        lead_time_days=lead_time,
        minimum_order_qty=moq,
        lifecycle_status=lifecycle_status,
        bom_item_id=bom_item_id,
        metadata=dict(metadata or {}),
    )


def cutoff_since(days: int) -> datetime:
    """Helper for callers asking "last N days" — returns
    ``datetime.now(UTC) - days``."""
    return datetime.now(UTC) - timedelta(days=days)
