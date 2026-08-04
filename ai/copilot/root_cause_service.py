"""
AI Copilot - AI Root Cause Analysis Service
OMS-360 Enterprise Food Delivery Platform

RootCauseAnalysisService answers "why are orders failing / why are
duplicates happening" from real data, never from LLM guesswork. Both
analyses run a real, parameterized SQLAlchemy query against
failed_orders / duplicate_orders (grouping/counting/ordering only -
no MySQL-specific SQL, so this runs identically against the SQLite
`copilot_db` test fixture), and the grouped counts/reasons/examples that
come back are the single source of truth for everything downstream.

An LLM, if a real provider is configured (via the SAME shared
AIProviderManager every other AI Copilot service uses), is used ONLY to
write more fluent explanation/investigation-steps prose ON TOP OF those
exact, already-computed facts - the prompt hands it the literal grouped
counts and reasons and instructs it not to invent a cause, a count, or a
table that isn't given. If no provider is configured, or the provider
call fails for any reason, a clear deterministic template (with simple
keyword-pattern-matched investigation steps per common reason, e.g.
"payment"/"inventory"/"timeout") is used instead - this is the default
mode, not a degraded one, matching the same discipline
BusinessQAService.get_explanation_async() already applies.

Zero failed orders / zero duplicate orders is a valid, non-error
outcome (not everything has gone wrong - that's good news), so neither
analyze_failed_orders() nor analyze_duplicate_orders() ever raises for
"no data found."
"""

from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger

from ai.copilot.provider_manager import AIProviderManager
from app import models

logger = get_logger("ai.copilot.root_cause")

_MAX_REASON_GROUPS = 10
_MAX_EXAMPLES_PER_GROUP = 3

# Simple, explainable keyword -> generic investigation steps mapping.
# Deliberately not exhaustive - falls back to _GENERIC_STEPS for anything
# unmatched, rather than pretending to know a cause it can't identify.
_REASON_KEYWORD_STEPS = (
    ("payment", [
        "Check app/services/payment_service.py logs around the failure timestamps for gateway/timeout errors.",
        "Verify the affected orders' payment_status and transaction rows in the transactions table.",
        "Confirm no payment provider outage overlapped with the failure window.",
    ]),
    ("inventory", [
        "Check app/services/inventory_service.py logs for InventoryLockException / insufficient-stock errors.",
        "Cross-reference the affected item_id(s) against current inventory.remaining_stock and inventory_alerts.",
        "Confirm no concurrent order burst caused a stock race condition during reservation.",
    ]),
    ("stock", [
        "Check app/services/inventory_service.py logs for InventoryLockException / insufficient-stock errors.",
        "Cross-reference the affected item_id(s) against current inventory.remaining_stock and inventory_alerts.",
    ]),
    ("timeout", [
        "Check Kafka broker/consumer health (GET /health) around the failure timestamps.",
        "Review app/messaging/consumer.py and app/messaging/producer.py logs for retry/DLQ activity in that window.",
        "Confirm no downstream service (kitchen/delivery) was slow or unavailable at the time.",
    ]),
    ("kafka", [
        "Check Kafka broker/consumer health (GET /health) around the failure timestamps.",
        "Review app/messaging/consumer.py and app/messaging/producer.py logs for retry/DLQ activity in that window.",
    ]),
    ("duplicate", [
        "Verify the idempotency key/transaction_id used by the client for these requests.",
        "Check whether the client retried a request before receiving the original response.",
    ]),
    ("validation", [
        "Check app/routes/orders.py request validation logs for malformed payloads around the failure timestamps.",
        "Confirm the client is sending all required fields with valid values.",
    ]),
)

_GENERIC_STEPS = [
    "Review the structured application logs (app/core/logging_config.py) around each failure's timestamp.",
    "Check GET /health and GET /metrics for any correlated system-level degradation at the same time.",
    "Inspect the order_audit_trail rows for the affected order_id(s) to reconstruct the exact sequence of events.",
]


@dataclass(frozen=True)
class ReasonGroup:
    reason: str
    count: int
    most_recent_order_id: Optional[str]
    most_recent_transaction_id: Optional[str]
    most_recent_at: Optional[str]


@dataclass(frozen=True)
class RootCauseResult:
    total_count: int
    top_reasons: tuple  # tuple[ReasonGroup, ...] for failed orders; empty for duplicates
    examples: tuple  # tuple[dict, ...] - raw example rows, for duplicates (correlated back to orders_master/failed_orders)
    explanation_text: str
    investigation_steps: List[str] = field(default_factory=list)
    ai_generated: bool = False


def _steps_for_reason(reason: str) -> List[str]:
    normalized = (reason or "").lower()
    for keyword, steps in _REASON_KEYWORD_STEPS:
        if keyword in normalized:
            return list(steps)
    return list(_GENERIC_STEPS)


class RootCauseAnalysisService:
    """Construct via ai.dependencies.get_root_cause_service(), not
    directly."""

    def __init__(self, provider_manager: AIProviderManager):
        self._provider_manager = provider_manager

    async def analyze_failed_orders(self, db: Session) -> RootCauseResult:
        total = db.query(func.count(models.FailedOrder.order_id)).scalar() or 0
        if total == 0:
            return RootCauseResult(
                total_count=0,
                top_reasons=(),
                examples=(),
                explanation_text="No failed orders found - nothing to investigate.",
                investigation_steps=[],
                ai_generated=False,
            )

        grouped = (
            db.query(
                models.FailedOrder.reason,
                func.count(models.FailedOrder.order_id).label("cnt"),
            )
            .group_by(models.FailedOrder.reason)
            .order_by(func.count(models.FailedOrder.order_id).desc())
            .limit(_MAX_REASON_GROUPS)
            .all()
        )

        reason_groups = []
        for reason, count in grouped:
            reason_label = reason or "(no reason recorded)"
            most_recent = (
                db.query(models.FailedOrder)
                .filter(models.FailedOrder.reason == reason)
                .order_by(models.FailedOrder.failed_at.desc())
                .first()
            )
            reason_groups.append(ReasonGroup(
                reason=reason_label,
                count=int(count),
                most_recent_order_id=most_recent.order_id if most_recent else None,
                most_recent_transaction_id=most_recent.transaction_id if most_recent else None,
                most_recent_at=str(most_recent.failed_at) if most_recent and most_recent.failed_at else None,
            ))

        deterministic_text, deterministic_steps = self._build_failed_orders_deterministic(total, reason_groups)

        selection = self._provider_manager.get_active_provider()
        explanation_text = deterministic_text
        investigation_steps = deterministic_steps
        ai_generated = False
        if selection.provider is not None:
            try:
                ai_text, ai_steps = await self._explain_failed_orders_with_ai(
                    selection.provider, total, reason_groups, deterministic_steps
                )
                if ai_text:
                    explanation_text = ai_text
                    investigation_steps = ai_steps or deterministic_steps
                    ai_generated = True
            except Exception:
                logger.warning("AI Copilot root cause: failed-orders AI explanation failed, using deterministic template")

        return RootCauseResult(
            total_count=total,
            top_reasons=tuple(reason_groups),
            examples=(),
            explanation_text=explanation_text,
            investigation_steps=investigation_steps,
            ai_generated=ai_generated,
        )

    def _build_failed_orders_deterministic(self, total: int, reason_groups: List[ReasonGroup]):
        top = reason_groups[0]
        text = (
            f"{total} failed order{'' if total == 1 else 's'} recorded. "
            f"The most common failure reason is '{top.reason}' ({top.count} occurrence"
            f"{'' if top.count == 1 else 's'})."
        )
        if len(reason_groups) > 1:
            others = ", ".join(f"'{g.reason}' ({g.count})" for g in reason_groups[1:])
            text += f" Other reasons: {others}."
        steps = _steps_for_reason(top.reason)
        return text, steps

    async def _explain_failed_orders_with_ai(self, provider, total: int, reason_groups: List[ReasonGroup], deterministic_steps: List[str]):
        facts_lines = "\n".join(
            f"- '{g.reason}': {g.count} occurrence(s), most recent order_id={g.most_recent_order_id}"
            for g in reason_groups
        )
        prompt = (
            "You are writing a root-cause analysis summary for an internal "
            "operations dashboard. Use ONLY the real, already-computed facts "
            "below - do not invent any failure reason, count, table, or "
            "system behavior that isn't stated here. Write a short "
            "explanation paragraph, then a short bulleted list of suggested "
            "investigation steps.\n\n"
            f"Total failed orders: {total}\n"
            f"Failure reasons (grouped, most common first):\n{facts_lines}\n\n"
            "Baseline suggested investigation steps you may refine but not "
            f"contradict: {deterministic_steps}\n"
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        content = content.strip()
        if not content:
            return "", []
        return content, deterministic_steps

    async def analyze_duplicate_orders(self, db: Session) -> RootCauseResult:
        total = db.query(func.count(models.DuplicateOrder.order_id)).scalar() or 0
        if total == 0:
            return RootCauseResult(
                total_count=0,
                top_reasons=(),
                examples=(),
                explanation_text="No duplicate order requests found - nothing to investigate.",
                investigation_steps=[],
                ai_generated=False,
            )

        duplicate_rows = (
            db.query(models.DuplicateOrder)
            .order_by(models.DuplicateOrder.detected_at.desc())
            .limit(_MAX_EXAMPLES_PER_GROUP * 3)
            .all()
        )

        examples = []
        for row in duplicate_rows:
            original_order = (
                db.query(models.OrdersMaster)
                .filter(models.OrdersMaster.transaction_id == row.transaction_id)
                .first()
            )
            original_failed = (
                db.query(models.FailedOrder)
                .filter(models.FailedOrder.transaction_id == row.transaction_id)
                .first()
            )
            if original_order is not None:
                outcome = f"original order {original_order.order_id} exists with status {original_order.order_status}"
            elif original_failed is not None:
                outcome = f"original order {original_failed.order_id} is recorded as failed ({original_failed.reason})"
            else:
                outcome = "no matching original order found for this transaction_id"

            examples.append({
                "order_id": row.order_id,
                "transaction_id": row.transaction_id,
                "detected_at": str(row.detected_at) if row.detected_at else None,
                "outcome": outcome,
            })

        deterministic_text, deterministic_steps = self._build_duplicate_orders_deterministic(total, examples)

        selection = self._provider_manager.get_active_provider()
        explanation_text = deterministic_text
        investigation_steps = deterministic_steps
        ai_generated = False
        if selection.provider is not None:
            try:
                ai_text, ai_steps = await self._explain_duplicate_orders_with_ai(
                    selection.provider, total, examples, deterministic_steps
                )
                if ai_text:
                    explanation_text = ai_text
                    investigation_steps = ai_steps or deterministic_steps
                    ai_generated = True
            except Exception:
                logger.warning("AI Copilot root cause: duplicate-orders AI explanation failed, using deterministic template")

        return RootCauseResult(
            total_count=total,
            top_reasons=(),
            examples=tuple(examples),
            explanation_text=explanation_text,
            investigation_steps=investigation_steps,
            ai_generated=ai_generated,
        )

    def _build_duplicate_orders_deterministic(self, total: int, examples: List[dict]):
        text = (
            f"{total} duplicate order request{'' if total == 1 else 's'} rejected "
            f"(same idempotency key/transaction_id received again within the TTL window)."
        )
        if examples:
            first = examples[0]
            text += f" Most recent: transaction_id={first['transaction_id']} - {first['outcome']}."
        steps = _steps_for_reason("duplicate")
        return text, steps

    async def _explain_duplicate_orders_with_ai(self, provider, total: int, examples: List[dict], deterministic_steps: List[str]):
        facts_lines = "\n".join(
            f"- transaction_id={e['transaction_id']}, detected_at={e['detected_at']}: {e['outcome']}"
            for e in examples
        )
        prompt = (
            "You are writing a root-cause analysis summary for an internal "
            "operations dashboard about duplicate order requests. Use ONLY "
            "the real, already-computed facts below - do not invent any "
            "count, transaction, or system behavior that isn't stated "
            "here. Write a short explanation paragraph, then a short "
            "bulleted list of suggested investigation steps.\n\n"
            f"Total duplicate order requests: {total}\n"
            f"Examples (most recent first):\n{facts_lines}\n\n"
            "Baseline suggested investigation steps you may refine but not "
            f"contradict: {deterministic_steps}\n"
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        content = content.strip()
        if not content:
            return "", []
        return content, deterministic_steps
