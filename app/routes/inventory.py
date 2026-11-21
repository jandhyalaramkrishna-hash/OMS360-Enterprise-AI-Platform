from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.exceptions import InventoryNotFoundException
from app.database import get_db
from app.services import inventory_service

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])


@router.get("", response_model=List[schemas.InventoryResponse], summary="List all inventory")
def get_all_inventory(db: Session = Depends(get_db)):
    return db.query(models.Inventory).order_by(models.Inventory.item_id).all()


@router.get("/low-stock", response_model=List[schemas.InventoryResponse],
            summary="Items below the low-stock threshold (remaining_stock 1-4 by default)",
            description="LOW_STOCK means 0 < remaining_stock < threshold. Threshold is read from "
                        "system_configuration.LOW_STOCK_THRESHOLD (falls back to 5 if not configured).")
def get_low_stock(db: Session = Depends(get_db)):
    return inventory_service.get_low_stock(db)


@router.get("/out-of-stock", response_model=List[schemas.InventoryResponse], summary="Items with zero stock")
def get_out_of_stock(db: Session = Depends(get_db)):
    return inventory_service.get_out_of_stock(db)


@router.get("/alerts", response_model=List[schemas.InventoryAlertResponse],
            summary="Recent inventory alerts",
            description="Backed by the inventory_alerts table - populated automatically "
                        "whenever an order reservation crosses the low-stock/out-of-stock threshold.")
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    return inventory_service.get_alerts(db, limit=limit)


@router.post("/alerts/dispatch-pending",
             summary="Send undelivered low-stock / out-of-stock alert emails",
             description="For every item that is currently LOW_STOCK/OUT_OF_STOCK, re-sends its "
                         "latest inventory_alerts email if notification_status is PENDING or FAILED "
                         "(e.g. alerts recorded while notifications were disabled or SMTP was "
                         "failing). Already-SENT alerts are never re-sent. Does not create alerts "
                         "or modify inventory rows. Returns a per-alert delivery summary.")
def dispatch_pending_alerts(db: Session = Depends(get_db)):
    return inventory_service.dispatch_open_alerts(db)


@router.get("/history", response_model=List[schemas.InventoryLedgerResponse],
            summary="Stock movement ledger",
            description="Every restock/reserve/release/adjustment, newest first. "
                        "Optionally filter to one item_id.")
def get_history(item_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    return inventory_service.get_ledger_history(db, item_id=item_id, limit=limit)


@router.get("/{item_id}", response_model=schemas.InventoryResponse, summary="Get a single inventory item")
def get_inventory_item(item_id: str, db: Session = Depends(get_db)):
    row = db.query(models.Inventory).filter(models.Inventory.item_id == item_id).first()
    if not row:
        raise InventoryNotFoundException(f"No inventory row for item_id={item_id}")
    return row


@router.post("/restock", response_model=schemas.InventoryResponse, status_code=200,
             summary="Restock an item",
             description="Increments remaining_stock and total_stock, writes an inventory_ledger "
                         "row (movement_type=RESTOCK), and clears OUT_OF_STOCK status if applicable.")
def restock_item(item_id: str, payload: schemas.RestockRequest, db: Session = Depends(get_db)):
    return inventory_service.restock(db, item_id, payload.quantity, reason=payload.reason)


@router.put("/{item_id}", response_model=schemas.InventoryResponse,
            summary="Update item price/status/stock/name/category/unit",
            description="Backs the Inventory Dashboard's \"Update Inventory\" dialog. "
                        "price/status/item_name/category/unit are simple field updates. `stock`, "
                        "if given, sets remaining_stock directly (an admin correction, not a "
                        "delta) and is still written to inventory_ledger "
                        "(movement_type=ADJUSTMENT), so every stock change - reservation, "
                        "restock, or manual correction - stays fully auditable.")
def update_item(item_id: str, payload: schemas.InventoryUpdateRequest, db: Session = Depends(get_db)):
    return inventory_service.update_item(
        db, item_id, price=payload.price, status=payload.status,
        item_name=payload.item_name, stock=payload.stock,
        category=payload.category, unit=payload.unit,
    )


@router.post("", response_model=schemas.InventoryResponse, status_code=201,
             summary="Add a new inventory item",
             description="Backs the Inventory Dashboard's \"Add New Item\" dialog. The Item "
                         "Number (item_id) is always server-generated (ITEM-NNNN) - it is not "
                         "accepted from the client. Writes matching rows to both `items` and "
                         "`inventory`, plus an inventory_ledger entry recording the item's "
                         "starting stock.")
def create_item(payload: schemas.InventoryCreateRequest, db: Session = Depends(get_db)):
    return inventory_service.create_item(
        db, item_name=payload.item_name, price=payload.price,
        total_stock=payload.total_stock, status=payload.status,
    )
