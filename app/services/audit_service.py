"""
Audit trail service. One function, used everywhere a state transition
happens: order_service.py (order creation, failure, duplicate rejection)
and messaging/consumer.py (kitchen/delivery progression).

Recording an audit event is best-effort and NEVER allowed to break the
calling flow - a failure to write an audit row must not fail an order.
"""

from sqlalchemy.orm import Session

from app import models
from app.core.enums import AuditEventType
from app.core.logging_config import get_logger

logger = get_logger("oms360.audit")

VALID_EVENT_TYPES = {e.value for e in AuditEventType}


def record_event(db: Session, order_id: str, transaction_id: str, event_type: str, details: str = None):
    if event_type not in VALID_EVENT_TYPES:
        logger.warning(f"Unrecognized audit event_type '{event_type}' for {order_id} - recording anyway.")
    try:
        db.add(models.OrderAuditTrail(
            order_id=order_id,
            transaction_id=transaction_id or "-",
            event_type=event_type,
            event_details=details,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(f"Failed to record audit event {event_type} for {order_id} (non-fatal, continuing)")
