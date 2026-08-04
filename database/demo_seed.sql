-- ============================================================================
-- OMS-360 — demo_seed.sql
-- ============================================================================
-- Populates the DB with a known, demo-ready dataset: a few inventory items
-- and one order per business scenario (normal in-flight order, delivered
-- order, failed-payment order, cancelled order, low-stock item, an
-- out-of-stock item, one duplicate-order record, and one DLQ record) so
-- every dashboard card/table has something real to show without waiting
-- for live traffic.
--
-- IMPORTANT: run demo_reset.sql first (or run this against an already-empty
-- set of demo rows) — this file does not delete anything itself, it only
-- inserts. Re-running it twice will hit primary-key collisions by design,
-- so you know immediately if the DB wasn't reset first.
--
-- Every order/payment/order_status combination below is intentionally a
-- VALID one per the OMS-360 workflow:
--   PAID    -> RECEIVED / PREPARING / READY / OUT_FOR_DELIVERY / DELIVERED
--   FAILED  -> FAILED or CANCELLED only
--   PENDING -> RECEIVED only
-- This is deliberate: demo_seed.sql should never itself be the source of
-- an "invalid state combo" on the dashboard.
--
-- Usage:
--   mysql -u <user> -p oms360_db < demo_reset.sql
--   mysql -u <user> -p oms360_db < demo_seed.sql
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Inventory (also mirrored into `items`, which is structurally identical)
-- ---------------------------------------------------------------------------
INSERT INTO inventory (item_id, item_name, price, total_stock, remaining_stock, used_stock, status) VALUES
  ('ITEM-BURGER',  'Classic Beef Burger',   249.00, 200, 178, 22,  'ACTIVE'),
  ('ITEM-PIZZA',   'Margherita Pizza',      399.00, 150, 140, 10,  'ACTIVE'),
  ('ITEM-FRIES',   'Salted Fries',           99.00, 300,  12, 288, 'LOW_STOCK'),
  ('ITEM-COLA',    'Cola 500ml',             59.00, 400, 240, 160, 'ACTIVE'),
  ('ITEM-SALAD',   'Caesar Salad',          179.00, 100,   0, 100, 'OUT_OF_STOCK'),
  ('ITEM-COFFEE',  'Cold Brew Coffee',      149.00, 120,  95,  25, 'ACTIVE');

INSERT INTO items (item_id, item_name, price, total_stock, remaining_stock, used_stock, status) VALUES
  ('ITEM-BURGER',  'Classic Beef Burger',   249.00, 200, 178, 22,  'ACTIVE'),
  ('ITEM-PIZZA',   'Margherita Pizza',      399.00, 150, 140, 10,  'ACTIVE'),
  ('ITEM-FRIES',   'Salted Fries',           99.00, 300,  12, 288, 'LOW_STOCK'),
  ('ITEM-COLA',    'Cola 500ml',             59.00, 400, 240, 160, 'ACTIVE'),
  ('ITEM-SALAD',   'Caesar Salad',          179.00, 100,   0, 100, 'OUT_OF_STOCK'),
  ('ITEM-COFFEE',  'Cold Brew Coffee',      149.00, 120,  95,  25, 'ACTIVE');

-- ---------------------------------------------------------------------------
-- 2. Orders — one per scenario
-- ---------------------------------------------------------------------------

-- Scenario A: DEMO-ORD-001 — delivered, fully paid, happy path
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-001', 'DEMO-TXN-001', 'Ananya Rao', 'CUST-1001', '9876500001', '9876500001',
   697.00, 697.00, 'ONLINE', 'PAID', 'CLEAR',
   'DELIVERED', 'SUCCESS_FLOW', '12A', 'MG Road', 'Visakhapatnam', 'Andhra Pradesh', '530001',
   DATE_SUB(NOW(), INTERVAL 2 HOUR));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-001', 'ITEM-BURGER', 'Classic Beef Burger', 2, 249.00),
  ('DEMO-ORD-001', 'ITEM-COLA', 'Cola 500ml', 1, 59.00),
  ('DEMO-ORD-001', 'ITEM-FRIES', 'Salted Fries', 1, 99.00);

INSERT INTO kitchen_status (order_id, transaction_id, item_id, item_assignment, quantity, station_id, cooking_status, chef_name, started_at, updated_at) VALUES
  ('DEMO-ORD-001', 'DEMO-TXN-001', 'ITEM-BURGER', 'Classic Beef Burger', 2, 'STATION-1', 'READY', 'Chef Ravi', DATE_SUB(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 100 MINUTE));

INSERT INTO delivery_status (order_id, transaction_id, item_id, transit_payload, status, delivery_person) VALUES
  ('DEMO-ORD-001', 'DEMO-TXN-001', 'ITEM-BURGER', 'ROUTE-STD-01', 'DELIVERED', 'Delivery Partner - Suresh');

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-001', 'DEMO-ORD-001', 'ONLINE', 'PAID', 697.00, DATE_SUB(NOW(), INTERVAL 2 HOUR));

-- Scenario B: DEMO-ORD-002 — currently in the kitchen (PAID + PREPARING)
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-002', 'DEMO-TXN-002', 'Kiran Kumar', 'CUST-1002', '9876500002', '9876500002',
   399.00, 399.00, 'UPI', 'PAID', 'CLEAR',
   'PREPARING', 'SUCCESS_FLOW', '45', 'Beach Road', 'Visakhapatnam', 'Andhra Pradesh', '530002',
   DATE_SUB(NOW(), INTERVAL 8 MINUTE));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-002', 'ITEM-PIZZA', 'Margherita Pizza', 1, 399.00);

INSERT INTO kitchen_status (order_id, transaction_id, item_id, item_assignment, quantity, station_id, cooking_status, chef_name, started_at, updated_at) VALUES
  ('DEMO-ORD-002', 'DEMO-TXN-002', 'ITEM-PIZZA', 'Margherita Pizza', 1, 'STATION-AUTO', 'COOKING', 'Auto-Assigned Chef', DATE_SUB(NOW(), INTERVAL 8 MINUTE), NOW());

INSERT INTO delivery_status (order_id, transaction_id, item_id, transit_payload, status, delivery_person) VALUES
  ('DEMO-ORD-002', 'DEMO-TXN-002', 'ITEM-PIZZA', 'ROUTE-STD-01', 'PENDING', NULL);

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-002', 'DEMO-ORD-002', 'UPI', 'PAID', 399.00, DATE_SUB(NOW(), INTERVAL 8 MINUTE));

-- Scenario C: DEMO-ORD-003 — out for delivery (PAID + OUT_FOR_DELIVERY)
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-003', 'DEMO-TXN-003', 'Priya Sharma', 'CUST-1003', '9876500003', '9876500003',
   208.00, 208.00, 'CARD', 'PAID', 'CLEAR',
   'OUT_FOR_DELIVERY', 'SUCCESS_FLOW', '7', 'Dwaraka Nagar', 'Visakhapatnam', 'Andhra Pradesh', '530016',
   DATE_SUB(NOW(), INTERVAL 22 MINUTE));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-003', 'ITEM-COFFEE', 'Cold Brew Coffee', 1, 149.00),
  ('DEMO-ORD-003', 'ITEM-COLA', 'Cola 500ml', 1, 59.00);

INSERT INTO kitchen_status (order_id, transaction_id, item_id, item_assignment, quantity, station_id, cooking_status, chef_name, started_at, updated_at) VALUES
  ('DEMO-ORD-003', 'DEMO-TXN-003', 'ITEM-COFFEE', 'Cold Brew Coffee', 1, 'STATION-AUTO', 'READY', 'Auto-Assigned Chef', DATE_SUB(NOW(), INTERVAL 22 MINUTE), DATE_SUB(NOW(), INTERVAL 15 MINUTE));

INSERT INTO delivery_status (order_id, transaction_id, item_id, transit_payload, status, delivery_person) VALUES
  ('DEMO-ORD-003', 'DEMO-TXN-003', 'ITEM-COFFEE', 'ROUTE-STD-02', 'OUT_FOR_DELIVERY', 'Delivery Partner - Lakshmi');

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-003', 'DEMO-ORD-003', 'CARD', 'PAID', 208.00, DATE_SUB(NOW(), INTERVAL 22 MINUTE));

-- Scenario D: DEMO-ORD-004 — payment failed (FAILED + FAILED, valid combo)
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-004', 'DEMO-TXN-004', 'Rahul Verma', 'CUST-1004', '9876500004', '9876500004',
   249.00, 249.00, 'CARD', 'FAILED', 'CLEAR',
   'FAILED', 'FAILED_FLOW', '19', 'Siripuram', 'Visakhapatnam', 'Andhra Pradesh', '530003',
   DATE_SUB(NOW(), INTERVAL 40 MINUTE));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-004', 'ITEM-BURGER', 'Classic Beef Burger', 1, 249.00);

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-004', 'DEMO-ORD-004', 'CARD', 'FAILED', 249.00, DATE_SUB(NOW(), INTERVAL 40 MINUTE));

INSERT INTO failed_orders (order_id, transaction_id, reason, failed_at) VALUES
  ('DEMO-ORD-004', 'DEMO-TXN-004', 'Card declined by issuing bank', DATE_SUB(NOW(), INTERVAL 40 MINUTE));

-- Scenario E: DEMO-ORD-005 — cancelled after payment failure (FAILED + CANCELLED, valid combo)
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-005', 'DEMO-TXN-005', 'Sneha Iyer', 'CUST-1005', '9876500005', '9876500005',
   428.00, 428.00, 'UPI', 'FAILED', 'CLEAR',
   'CANCELLED', 'FAILED_FLOW', '3', 'Gajuwaka', 'Visakhapatnam', 'Andhra Pradesh', '530026',
   DATE_SUB(NOW(), INTERVAL 3 HOUR));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-005', 'ITEM-PIZZA', 'Margherita Pizza', 1, 399.00),
  ('DEMO-ORD-005', 'ITEM-COLA', 'Cola 500ml', 1, 29.00);

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-005', 'DEMO-ORD-005', 'UPI', 'FAILED', 428.00, DATE_SUB(NOW(), INTERVAL 3 HOUR));

INSERT INTO failed_orders (order_id, transaction_id, reason, failed_at) VALUES
  ('DEMO-ORD-005', 'DEMO-TXN-005', 'UPI timeout, order cancelled by customer (demo data)', DATE_SUB(NOW(), INTERVAL 3 HOUR));

-- Scenario F: DEMO-ORD-006 — just received, payment still pending (PENDING + RECEIVED, valid combo)
INSERT INTO orders_master
  (order_id, transaction_id, customer_name, customer_id, mobile, mobile_number,
   grand_total, total_amount, payment_method, payment_status, fraud_status,
   order_status, live_window_track, door_no, street, city, state, pincode, created_at)
VALUES
  ('DEMO-ORD-006', 'DEMO-TXN-006', 'Manoj Das', 'CUST-1006', '9876500006', '9876500006',
   99.00, 99.00, 'COD', 'PENDING', 'CLEAR',
   'RECEIVED', 'SUCCESS_FLOW', '88', 'Pendurthi', 'Visakhapatnam', 'Andhra Pradesh', '530051',
   DATE_SUB(NOW(), INTERVAL 1 MINUTE));

INSERT INTO order_items (order_id, item_id, item_name, quantity, price) VALUES
  ('DEMO-ORD-006', 'ITEM-FRIES', 'Salted Fries', 1, 99.00);

INSERT INTO kitchen_status (order_id, transaction_id, item_id, item_assignment, quantity, station_id, cooking_status, chef_name, started_at, updated_at) VALUES
  ('DEMO-ORD-006', 'DEMO-TXN-006', 'ITEM-FRIES', 'Salted Fries', 1, 'UNASSIGNED', 'QUEUED', 'UNASSIGNED', DATE_SUB(NOW(), INTERVAL 1 MINUTE), NOW());

INSERT INTO delivery_status (order_id, transaction_id, item_id, transit_payload, status, delivery_person) VALUES
  ('DEMO-ORD-006', 'DEMO-TXN-006', 'ITEM-FRIES', 'ROUTE-STD-01', 'PENDING', NULL);

INSERT INTO transactions (transaction_id, order_id, payment_method, payment_status, transaction_amount, transaction_time) VALUES
  ('DEMO-TXN-006', 'DEMO-ORD-006', 'COD', 'PENDING', 99.00, DATE_SUB(NOW(), INTERVAL 1 MINUTE));

-- ---------------------------------------------------------------------------
-- 3. Duplicate order marker (for the Duplicate Orders card on Dashboard 2)
-- ---------------------------------------------------------------------------
INSERT INTO duplicate_orders (order_id, transaction_id, detected_at) VALUES
  ('DUP-DEMO0001', 'DEMO-TXN-002', DATE_SUB(NOW(), INTERVAL 7 MINUTE));

-- ---------------------------------------------------------------------------
-- 4. DLQ entry (for the Dead Letter Queue card on Dashboard 2)
-- ---------------------------------------------------------------------------
INSERT INTO dlq_orders (order_id, transaction_id, payload, moved_at) VALUES
  ('DEMO-ORD-999', 'DEMO-TXN-999',
   '{"order_id":"DEMO-ORD-999","reason":"kafka consumer retry limit exceeded (demo data)"}',
   DATE_SUB(NOW(), INTERVAL 1 HOUR));

-- ---------------------------------------------------------------------------
-- 5. Inventory alert (for the low-stock card — matches ITEM-FRIES above)
-- ---------------------------------------------------------------------------
INSERT INTO inventory_alerts (item_id, item_name, remaining_stock, threshold_value, alert_type, notification_type, notification_status, recipient_email, created_at) VALUES
  ('ITEM-FRIES', 'Salted Fries', 12, 20, 'LOW_STOCK', 'EMAIL', 'SENT', 'ops@oms360.demo', DATE_SUB(NOW(), INTERVAL 30 MINUTE));

-- ============================================================================
-- Done. 6 orders (1 delivered, 1 preparing, 1 out-for-delivery, 1 failed,
-- 1 cancelled, 1 pending-payment), 1 duplicate marker, 1 DLQ entry, 1 low
-- stock item, 1 out-of-stock item, 1 inventory alert.
-- All payment_status/order_status pairs above are valid per the workflow
-- enforced in app/routes/dashboard.py's _check_state_validity().
-- ============================================================================
