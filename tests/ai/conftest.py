"""
Shared fixtures for tests/ai/ — currently only used by the AI Copilot
test modules (test_copilot_business_qa_service.py,
test_copilot_business_insights_service.py).

Every other existing tests/ai/*.py file needs no real database (Sprints
1-9 never touch app.models). AI Copilot's Business Q&A/Business Insights
services do run real SQLAlchemy queries against app.models, so these
tests need a real, working database - just not necessarily the project's
production MySQL instance, which this sandbox environment does not have
a live connection to (see tests/test_orders.py,
tests/test_sql_validation.py, which already skip/fail without one).

An in-memory SQLite database, built directly from the same
app.database.Base metadata, exercises the exact same SQLAlchemy Core
query shapes (ai/copilot/intents.py's handlers use plain
func.count()/filter() - no MySQL-specific SQL) without requiring a live
MySQL server, so these tests can run anywhere. StaticPool is required
because SQLite's :memory: database is otherwise per-connection - without
it, each new Session would see an empty, freshly-created database.
"""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.core.enums import InventoryStatus, OrderStatus, PaymentStatus
from app.database import Base


@pytest.fixture()
def copilot_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def seed_baseline(db):
    """Two orders (one RECEIVED/pending, one PAID), one LOW_STOCK and one
    OUT_OF_STOCK inventory item - a small, realistic baseline shared by
    the Business Q&A and Business Insights tests, mirroring what the
    original manual shadow-repo verification used."""
    db.add_all([
        models.Inventory(
            item_id="ITEM-BURGER", item_name="Burger", price=199.0,
            total_stock=10, remaining_stock=2, used_stock=8,
            status=InventoryStatus.LOW_STOCK.value,
        ),
        models.Inventory(
            item_id="ITEM-FRIES", item_name="Fries", price=99.0,
            total_stock=10, remaining_stock=0, used_stock=10,
            status=InventoryStatus.OUT_OF_STOCK.value,
        ),
    ])
    db.add_all([
        models.OrdersMaster(
            order_id="ORD-1", transaction_id="TXN-1", customer_name="Alice", customer_id="CUST-1",
            mobile="9999999999", grand_total=298.0, total_amount=298.0,
            payment_status=PaymentStatus.PAID.value, order_status=OrderStatus.RECEIVED.value,
            created_at=dt.datetime.utcnow(),
        ),
        models.OrdersMaster(
            order_id="ORD-2", transaction_id="TXN-2", customer_name="Bob", customer_id="CUST-2",
            mobile="8888888888", grand_total=99.0, total_amount=99.0,
            payment_status=PaymentStatus.PENDING.value, order_status=OrderStatus.RECEIVED.value,
            created_at=dt.datetime.utcnow(),
        ),
    ])
    db.commit()
    db.add_all([
        models.OrderItem(order_id="ORD-1", item_id="ITEM-BURGER", item_name="Burger", quantity=1, price=199.0),
        models.OrderItem(order_id="ORD-2", item_id="ITEM-FRIES", item_name="Fries", quantity=1, price=99.0),
    ])
    db.commit()
