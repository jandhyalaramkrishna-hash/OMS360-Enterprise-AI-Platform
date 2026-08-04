"""
TransactionService - single responsibility: everything touching `transactions`.
"""

from sqlalchemy.orm import Session

from app import models
from app.core.enums import PaymentStatus


def create_transaction(db: Session, transaction_id: str, order_id: str,
                        payment_method: str, amount: float):
    db.add(models.Transaction(
        transaction_id=transaction_id,
        order_id=order_id,
        payment_method=payment_method,
        payment_status=PaymentStatus.PENDING.value,
        transaction_amount=amount,
    ))


def get_by_order_id(db: Session, order_id: str):
    return db.query(models.Transaction).filter(models.Transaction.order_id == order_id).first()


def mark_paid(db: Session, order_id: str):
    txn = get_by_order_id(db, order_id)
    if txn:
        txn.payment_status = PaymentStatus.PAID.value
        db.commit()


def mark_failed(db: Session, order_id: str):
    txn = get_by_order_id(db, order_id)
    if txn:
        txn.payment_status = PaymentStatus.FAILED.value
        db.commit()
