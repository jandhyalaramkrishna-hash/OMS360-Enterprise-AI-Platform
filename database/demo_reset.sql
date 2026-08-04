-- ============================================================================
-- OMS-360 — demo_reset.sql
-- ============================================================================
-- Wipes all transactional/demo data back to an empty-but-schema-intact
-- state, so you can re-run demo_seed.sql and get the exact same known
-- dataset before a demo or interview.
--
-- Does NOT drop or alter any table (unlike re-running oms360_schema.sql,
-- which would DROP TABLE first). Safe to run repeatedly.
--
-- Order matters: children before parents, to respect FOREIGN KEY
-- constraints (order_items / kitchen_status / delivery_status all cascade
-- from orders_master, but we truncate explicitly anyway for clarity and
-- speed).
--
-- Usage:
--   mysql -u <user> -p oms360_db < demo_reset.sql
--   mysql -u <user> -p oms360_db < demo_seed.sql
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE order_items;
TRUNCATE TABLE kitchen_status;
TRUNCATE TABLE delivery_status;
TRUNCATE TABLE order_audit_trail;
TRUNCATE TABLE transactions;
TRUNCATE TABLE failed_orders;
TRUNCATE TABLE duplicate_orders;
TRUNCATE TABLE dlq_orders;
TRUNCATE TABLE inventory_alerts;
TRUNCATE TABLE inventory_ledger;
TRUNCATE TABLE orders_master;

-- Inventory/items are reset too, so demo_seed.sql's stock numbers are exact
-- every time (rather than accumulating used_stock across repeated demos).
TRUNCATE TABLE inventory;
TRUNCATE TABLE items;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- Done. Every table above is now empty. Run demo_seed.sql next.
-- ============================================================================
