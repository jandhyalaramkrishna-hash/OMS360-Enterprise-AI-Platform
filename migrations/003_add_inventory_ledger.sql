-- ============================================================================
-- OMS-360 Version 1.1 - Migration 003: Inventory Ledger + Indexes
-- ============================================================================
-- FLAGGED, NOT SILENT: adds ONE new table (inventory_ledger) for stock
-- movement history (V1.1 Requirement #5), plus a few indexes that support
-- the new inventory/dashboard query patterns without altering any existing
-- table's columns.
--
-- Apply with:  mysql -uroot -p oms360_db < migrations/003_add_inventory_ledger.sql
-- ============================================================================

USE oms360_db;

CREATE TABLE IF NOT EXISTS inventory_ledger (
    ledger_id             BIGINT NOT NULL AUTO_INCREMENT,
    item_id               VARCHAR(50) NOT NULL,
    movement_type         VARCHAR(20) NOT NULL,   -- RESTOCK | RESERVE | RELEASE | ADJUSTMENT
    quantity_change       INT NOT NULL,            -- positive for restock, negative for reserve
    remaining_stock_after INT NOT NULL,
    reference_order_id    VARCHAR(50) NULL,
    reason                VARCHAR(255) NULL,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ledger_id),
    KEY idx_ledger_item_id (item_id),
    KEY idx_ledger_reference_order (reference_order_id),
    KEY idx_ledger_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Supporting indexes for the new query patterns (low-stock lookups,
-- dashboard analytics by date, audit trail lookups by order). These are
-- pure indexes - no column or table changes to existing tables.
-- NOTE: MySQL doesn't support "CREATE INDEX IF NOT EXISTS" before 8.0 in
-- all distros consistently for this exact syntax on existing indexes;
-- if any of these already exist in your DB and this errors, just remove
-- that one line - it's not required for the app to function.
CREATE INDEX idx_inventory_remaining_stock ON inventory (remaining_stock);
CREATE INDEX idx_orders_master_created_at ON orders_master (created_at);
CREATE INDEX idx_orders_master_order_status ON orders_master (order_status);
CREATE INDEX idx_kitchen_status_cooking_status ON kitchen_status (cooking_status);
CREATE INDEX idx_delivery_status_status ON delivery_status (status);
