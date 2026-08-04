"""
AI Service Layer - RAG - Document Loader (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

DocumentLoaderBase is the seam between "documents live somewhere" and the
KnowledgeBase, which only knows how to store/look them up. This sprint
ships exactly one implementation, MockDocumentLoader, which returns a
small, fixed set of built-in food-delivery FAQ/help documents entirely
in-process - no filesystem read, no network call, no database. A future
sprint could add a real loader (files, a CMS, a database table) behind
this same interface without touching KnowledgeBase, DocumentParser, or
anything downstream.
"""

from abc import ABC, abstractmethod

from app.core.logging_config import get_logger

from ai.rag.documents import KnowledgeBaseDocument

logger = get_logger("ai.rag.document_loader")


class DocumentLoaderBase(ABC):
    """Abstract source of KnowledgeBaseDocument objects. Single
    Responsibility: produce documents - nothing here stores, parses,
    chunks, or retrieves them."""

    @abstractmethod
    def load(self) -> list:
        """Return a list of KnowledgeBaseDocument. May be called more than
        once; implementations should be safe to call repeatedly (e.g. for
        a KnowledgeBase.clear() + reload flow) even if not required this
        sprint."""
        raise NotImplementedError


class MockDocumentLoader(DocumentLoaderBase):
    """Returns a fixed set of built-in mock FAQ/help documents relevant to
    the food-delivery domain. Deterministic and side-effect-free - the
    same six documents every call, no filesystem or network access. This
    is the only document source in Sprint 5, per the "mock documents and
    mock retrieval only" instruction."""

    _MOCK_DOCUMENTS = (
        KnowledgeBaseDocument(
            doc_id="faq-refund-policy",
            title="Refund Policy",
            content=(
                "If your order arrives damaged, incomplete, or significantly late, you may "
                "request a refund within 48 hours of delivery. Refunds for missing items are "
                "processed automatically once the restaurant confirms the shortage. Refunds for "
                "quality issues require a photo of the item. Approved refunds are returned to "
                "the original payment method within 5-7 business days. Refunds are not available "
                "for orders that were successfully delivered and match what was ordered."
            ),
            source="help-center/refunds",
            metadata={"category": "billing"},
        ),
        KnowledgeBaseDocument(
            doc_id="faq-order-tracking",
            title="Order Tracking",
            content=(
                "You can track your order from the moment it is placed until it is delivered. "
                "Order status moves through the stages Placed, Confirmed, Preparing, Ready for "
                "Pickup, Out for Delivery, and Delivered. Each stage change sends a notification. "
                "If your order status has not changed for more than 20 minutes during preparation, "
                "or more than 15 minutes during delivery, contact support so we can check with the "
                "restaurant or delivery partner directly."
            ),
            source="help-center/order-tracking",
            metadata={"category": "orders"},
        ),
        KnowledgeBaseDocument(
            doc_id="faq-delivery-windows",
            title="Delivery Windows",
            content=(
                "Estimated delivery windows are shown at checkout and are based on restaurant "
                "preparation time plus current delivery partner availability in your area. "
                "Delivery windows are estimates, not guarantees, and can shift due to weather, "
                "traffic, or high order volume during peak hours. Scheduled orders can be placed "
                "up to 7 days in advance and will be prepared to arrive within a 15-minute window "
                "of the requested time."
            ),
            source="help-center/delivery-windows",
            metadata={"category": "delivery"},
        ),
        KnowledgeBaseDocument(
            doc_id="faq-restaurant-hours",
            title="Restaurant Hours",
            content=(
                "Each restaurant sets its own operating hours, shown on its menu page. Orders "
                "can only be placed while a restaurant is marked open. A restaurant that is "
                "temporarily closed (for example, due to a kitchen backlog) will show as "
                "unavailable until it reopens, even during its normal listed hours. Holiday hours, "
                "when different from regular hours, are shown as a banner on the restaurant page."
            ),
            source="help-center/restaurant-hours",
            metadata={"category": "restaurants"},
        ),
        KnowledgeBaseDocument(
            doc_id="faq-payment-issues",
            title="Payment Issues",
            content=(
                "If a payment fails at checkout, the most common causes are an expired card, "
                "insufficient funds, or a bank decline for an unrecognized merchant. No charge is "
                "made to your account for a failed payment attempt. If you were charged but did "
                "not receive an order confirmation, the charge is a temporary authorization hold "
                "that will be released automatically within 3-5 business days. Saved payment "
                "methods can be managed from the Payment Methods section of your account."
            ),
            source="help-center/payment-issues",
            metadata={"category": "billing"},
        ),
        KnowledgeBaseDocument(
            doc_id="faq-order-cancellation",
            title="Order Cancellation",
            content=(
                "Orders can be cancelled free of charge while they are still in the Placed "
                "status. Once a restaurant confirms an order and begins preparing it, "
                "cancellation may no longer be possible, or may involve a partial charge to "
                "cover food and preparation costs already incurred. To cancel an order, use the "
                "Cancel Order option on the order details page, or contact support if that option "
                "is no longer available."
            ),
            source="help-center/order-cancellation",
            metadata={"category": "orders"},
        ),
    )

    def load(self) -> list:
        documents = list(self._MOCK_DOCUMENTS)
        logger.info("MockDocumentLoader loaded documents", extra={"ctx_document_count": len(documents)})
        return documents
