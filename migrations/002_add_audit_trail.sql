-- ============================================================================
-- OMS-360 Version 1.0 - Migration 002: Order Audit Trail
-- ============================================================================
-- FLAGGED, NOT SILENT: this adds ONE new table that does not exist in
-- oms360_schema.sql (the master schema). You explicitly asked for an audit
-- trail feature in this round of requirements, so this migration is scoped
-- to exactly that - it does not touch or alter any existing table.
--
-- Apply with:  mysql -uroot -p oms360_db < migrations/002_add_audit_trail.sql
-- ============================================================================

USE oms360_db;

CREATE TABLE IF NOT EXISTS order_audit_trail (
    audit_id      BIGINT NOT NULL AUTO_INCREMENT,
    order_id      VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50) NOT NULL,
    event_type    VARCHAR(50) NOT NULL,   -- e.g. ORDER_CREATED, PAYMENT_SUCCESSFUL,
                                           -- INVENTORY_RESERVED, KITCHEN_STARTED,
                                           -- KITCHEN_COMPLETED, OUT_FOR_DELIVERY,
                                           -- DELIVERED, CANCELLED, ORDER_FAILED,
                                           -- DUPLICATE_REJECTED
    event_details TEXT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_order_id (order_id),
    CONSTRAINT fk_audit_order FOREIGN KEY (order_id)
        REFERENCES orders_master (order_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
