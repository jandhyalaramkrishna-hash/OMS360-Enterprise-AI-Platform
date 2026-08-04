# =============================================================================
# OMS-360 - VERIFY_E2E.ps1
# =============================================================================
# End-to-end synchronization verification: creates one real order and proves
# that the same order/status is visible, in agreement, across the REST API,
# MySQL, Kafka (producer + consumer), the audit trail, and the dashboard
# endpoints - the exact UI/API/Kafka/MySQL consistency requirement the
# Product Owner asked to validate.
#
# What this script CANNOT do: physically look at the browser. Step 0 and the
# final section print exactly what to look at and when - that is the one
# part of this checklist that only a human watching the screen can confirm.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\VERIFY_E2E.ps1
#
# Safe to re-run - each run creates a fresh order with a unique customer_id,
# so repeat runs never collide with a previous run's data.
# =============================================================================

$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"
$stamp = Get-Date -Format "yyyyMMddHHmmss"

function Section($title) {
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "=============================================================================" -ForegroundColor Cyan
}

# -----------------------------------------------------------------------
# STEP 0 - Human checkpoint: dashboard should already be open
# -----------------------------------------------------------------------
Section "STEP 0 - BEFORE YOU CONTINUE"
Write-Host "START_OMS360.bat should have already opened the Operations Dashboard"
Write-Host "in your browser at $base/dashboard/operations"
Write-Host "Arrange your browser and this PowerShell window so you can see both -"
Write-Host "you'll be asked to watch the dashboard update live in a few moments."
Write-Host ""
Read-Host "Press Enter once the dashboard is visible and ready to continue"

# -----------------------------------------------------------------------
# STEP 1 - Baseline: KPIs and health BEFORE creating the order
# -----------------------------------------------------------------------
Section "STEP 1 - BASELINE (before order creation)"
$healthBefore = Invoke-RestMethod -Uri "$base/health"
$kpisBefore = Invoke-RestMethod -Uri "$base/api/v1/dashboard/kpis"
Write-Host "kafka_producer status ..... $($healthBefore.dependencies.kafka_producer)"
Write-Host "total_orders (before) ..... $($kpisBefore.total_orders)"
Write-Host "total_revenue (before) .... $($kpisBefore.total_revenue)"

# -----------------------------------------------------------------------
# STEP 2 - Create the order (drives the same backend flow the UI would;
# the two dashboards are read-only monitoring views, so this is the
# supported way to place an order - via the API the UI itself calls
# indirectly, same as Swagger's "Try it out" on POST /api/v1/orders)
# -----------------------------------------------------------------------
Section "STEP 2 - CREATE ORDER"
$body = @{
    customer_id      = "CUST-VERIFY-$stamp"
    customer_name    = "E2E Verification $stamp"
    mobile           = "9876543210"
    payment_method   = "UPI"
    enterprise_id    = "ENT-99"
    items            = @(@{ item_id = "ITEM-BURGER"; quantity = 1 })
    delivery_address = @{
        door_no = "1"; street = "Verification Street"
        city = "Visakhapatnam"; state = "Andhra Pradesh"; pincode = "530001"
    }
} | ConvertTo-Json -Depth 5

$order = Invoke-RestMethod -Uri "$base/api/v1/orders" -Method Post -Body $body -ContentType "application/json"
$orderId = $order.order_id
Write-Host "Created order_id ........ $orderId"
Write-Host "transaction_id .......... $($order.transaction_id)"
Write-Host "order_status ............ $($order.order_status)"
Write-Host "payment_status ..........  $($order.payment_status)"
$order | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host ">>> LOOK AT YOUR BROWSER NOW - refresh the Operations Dashboard and" -ForegroundColor Yellow
Write-Host ">>> confirm '$($order.customer_name)' / order $orderId appears in the live feed." -ForegroundColor Yellow

# -----------------------------------------------------------------------
# STEP 3 - Confirm the API returns the same order
# -----------------------------------------------------------------------
Section "STEP 3 - GET ORDER BY ID (API agrees with itself)"
Invoke-RestMethod -Uri "$base/api/v1/orders/$orderId" | ConvertTo-Json -Depth 5

# -----------------------------------------------------------------------
# STEP 4 - Confirm MySQL rows: orders_master, order_items, kitchen_status,
# delivery_status (initial state), order_audit_trail (ORDER_CREATED /
# INVENTORY_RESERVED so far)
# -----------------------------------------------------------------------
Section "STEP 4 - MYSQL ROWS (immediately after creation)"
docker exec -i oms360_mysql mysql -uroot -proot123 -e "USE oms360_db; SELECT order_id, transaction_id, customer_name, grand_total, payment_status, order_status FROM orders_master WHERE order_id='$orderId'\G SELECT item_id, item_name, quantity, price FROM order_items WHERE order_id='$orderId'\G SELECT kitchen_id, station_id, cooking_status, chef_name FROM kitchen_status WHERE order_id='$orderId'\G SELECT delivery_id, status, delivery_person FROM delivery_status WHERE order_id='$orderId'\G SELECT event_type, created_at FROM order_audit_trail WHERE order_id='$orderId' ORDER BY created_at\G"

# -----------------------------------------------------------------------
# STEP 5 - Confirm the Kafka event was produced (not silently dropped to
# DLQ) and consumed
# -----------------------------------------------------------------------
Section "STEP 5 - KAFKA PRODUCE + CONSUME"
Start-Sleep -Seconds 3
$healthAfterCreate = Invoke-RestMethod -Uri "$base/health"
Write-Host "kafka_producer status (should now be UP) ..... $($healthAfterCreate.dependencies.kafka_producer)"

$metrics = Invoke-RestMethod -Uri "$base/metrics"
Write-Host "kafka_publish_success_total ................... $($metrics.counters.kafka_publish_success_total)"
Write-Host "kafka_publish_dlq_total ........................ $($metrics.counters.kafka_publish_dlq_total)"
Write-Host "kafka_consume_success_total .................... $($metrics.counters.kafka_consume_success_total)"

Write-Host "`nConsumer log lines mentioning this order (proves it was consumed):"
docker logs oms360_consumer --tail 200 | Select-String $orderId

Write-Host "`nConfirming no DLQ row was written for this order (proves the publish succeeded, not failed-over):"
docker exec -i oms360_mysql mysql -uroot -proot123 -e "USE oms360_db; SELECT COUNT(*) AS dlq_rows_for_this_order FROM dlq_orders WHERE order_id='$orderId';"

# -----------------------------------------------------------------------
# STEP 6 - Wait for the consumer's simulated kitchen stage
# (settings.SIM_COOKING_SECONDS, default 8s) then confirm kitchen_status
# advanced to COOKING/READY and order_status/audit trail moved with it
# -----------------------------------------------------------------------
Section "STEP 6 - WAITING FOR KITCHEN STAGE (~10s)"
Start-Sleep -Seconds 10
docker exec -i oms360_mysql mysql -uroot -proot123 -e "USE oms360_db; SELECT order_status, payment_status FROM orders_master WHERE order_id='$orderId'\G SELECT cooking_status, chef_name FROM kitchen_status WHERE order_id='$orderId'\G SELECT event_type, created_at FROM order_audit_trail WHERE order_id='$orderId' ORDER BY created_at\G"

Write-Host "`nDashboard kitchen-ops feed (should show this order if still cooking, or have moved past it if already READY):"
(Invoke-RestMethod -Uri "$base/api/v1/dashboard/kitchen-ops?limit=10") | Where-Object { $_.order_id -eq $orderId } | ConvertTo-Json -Depth 5

Write-Host "`n>>> LOOK AT YOUR BROWSER - refresh the dashboard and confirm this order's" -ForegroundColor Yellow
Write-Host ">>> kitchen tile shows COOKING or READY, not still PENDING." -ForegroundColor Yellow

# -----------------------------------------------------------------------
# STEP 7 - Wait for the consumer's simulated delivery stage
# (settings.SIM_DELIVERY_SECONDS, default 12s) then confirm the full
# lifecycle completed: order_status=DELIVERED, delivery_status=DELIVERED,
# full audit trail present
# -----------------------------------------------------------------------
Section "STEP 7 - WAITING FOR DELIVERY STAGE (~15s)"
Start-Sleep -Seconds 15
docker exec -i oms360_mysql mysql -uroot -proot123 -e "USE oms360_db; SELECT order_status FROM orders_master WHERE order_id='$orderId'\G SELECT status, delivery_person FROM delivery_status WHERE order_id='$orderId'\G SELECT event_type, created_at FROM order_audit_trail WHERE order_id='$orderId' ORDER BY created_at\G"

Write-Host "`nDashboard delivery-ops feed for this order:"
(Invoke-RestMethod -Uri "$base/api/v1/dashboard/delivery-ops?limit=10") | Where-Object { $_.order_id -eq $orderId } | ConvertTo-Json -Depth 5

# -----------------------------------------------------------------------
# STEP 8 - Confirm dashboards/reports/analytics reflect this order
# -----------------------------------------------------------------------
Section "STEP 8 - DASHBOARDS, REPORTS, ANALYTICS AGREE"
Write-Host "live-orders feed (this order should appear):"
(Invoke-RestMethod -Uri "$base/api/v1/dashboard/live-orders?limit=10") | Where-Object { $_.order_id -eq $orderId } | ConvertTo-Json -Depth 5

$kpisAfter = Invoke-RestMethod -Uri "$base/api/v1/dashboard/kpis"
Write-Host "`ntotal_orders  before -> after ..... $($kpisBefore.total_orders) -> $($kpisAfter.total_orders)"
Write-Host "total_revenue before -> after ..... $($kpisBefore.total_revenue) -> $($kpisAfter.total_revenue)"

Write-Host "`nAnalytics summary (today_revenue/top_selling_items should include this order):"
Invoke-RestMethod -Uri "$base/api/v1/dashboard/analytics" | ConvertTo-Json -Depth 5

# -----------------------------------------------------------------------
# STEP 9 - Final human checkpoint
# -----------------------------------------------------------------------
Section "STEP 9 - FINAL VISUAL CHECK (only you can do this one)"
Write-Host ">>> Refresh the Operations Dashboard in your browser one more time." -ForegroundColor Yellow
Write-Host ">>> Confirm order $orderId shows status DELIVERED (or its current stage" -ForegroundColor Yellow
Write-Host ">>> if it hasn't reached DELIVERED yet - wait a few more seconds and refresh" -ForegroundColor Yellow
Write-Host ">>> again) and that it matches everything printed above." -ForegroundColor Yellow

Write-Host ""
Write-Host "=============================================================================" -ForegroundColor Green
Write-Host "  DONE. order_id = $orderId - paste this entire output back for review." -ForegroundColor Green
Write-Host "=============================================================================" -ForegroundColor Green
