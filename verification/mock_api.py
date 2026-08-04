"""
Throwaway mock JSON server, used ONLY to render/screenshot the two
dashboard HTML files for visual verification in this offline sandbox
(no MySQL/FastAPI available here - see conversation notes).
This file is NOT part of the delivered OMS-360 project.
"""
import json
import random
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

random.seed(42)

CUSTOMERS = ["Anil Kumar","Priya Sharma","Rahul Verma","Sneha Iyer","Vikram Singh","Divya Nair","Arjun Rao","Kavya Reddy"]
ITEMS = ["Millet Dosa","Paneer Tikka","Veg Biryani","Filter Coffee","Masala Chai","Chicken Curry","Naan","Gulab Jamun"]
CHEFS = ["Auto-Assigned Chef","Chef Ramesh","Chef Lakshmi","Chef Suresh"]
RIDERS = ["Auto-Assigned Rider","Rider Manoj","Rider Deepak","Rider Farhan"]

def now_iso(offset_sec=0):
    return (datetime.datetime.utcnow() - datetime.timedelta(seconds=offset_sec)).isoformat()

def gen_live_orders():
    statuses = ["RECEIVED","PREPARING","READY","OUT_FOR_DELIVERY","DELIVERED","CANCELLED"]
    pay = ["PAID","PENDING","FAILED"]
    out = []
    for i in range(18):
        n_items = random.randint(1,3)
        items = [{"item_name": random.choice(ITEMS), "quantity": random.randint(1,4)} for _ in range(n_items)]
        out.append({
            "order_id": f"ORD-{1000+i}ABCD",
            "customer_id": f"CUST-{200+i}",
            "customer_name": random.choice(CUSTOMERS),
            "items": items,
            "total_quantity": sum(x["quantity"] for x in items),
            "total_amount": round(random.uniform(150, 1800), 2),
            "payment_status": random.choice(pay),
            "order_time": now_iso(i*180),
            "current_status": random.choice(statuses),
        })
    return out

def gen_kitchen():
    out = []
    for i in range(9):
        cooking = random.choice(["QUEUED","COOKING","READY"])
        out.append({
            "order_id": f"ORD-{1000+i}ABCD",
            "chef": random.choice(CHEFS),
            "customer": random.choice(CUSTOMERS),
            "item": random.choice(ITEMS),
            "quantity": random.randint(1,3),
            "station_id": f"STATION-{i%4+1}",
            "is_preparing": cooking == "COOKING",
            "is_ready": cooking == "READY",
            "cooking_status": cooking,
            "time_taken_seconds": random.randint(20, 600),
        })
    return out

def gen_delivery():
    out = []
    for i in range(8):
        status = random.choice(["PENDING","OUT_FOR_DELIVERY","DELIVERED"])
        gen = status in ("OUT_FOR_DELIVERY","DELIVERED")
        ver = status == "DELIVERED"
        out.append({
            "order_id": f"ORD-{2000+i}XYZ",
            "delivery_partner": random.choice(RIDERS),
            "customer": random.choice(CUSTOMERS),
            "status": status,
            "transit_note": "Packed and handed off for delivery" if status != "PENDING" else "Awaiting kitchen completion",
            "otp_generated": gen,
            "otp_verified": ver,
            "otp_code": f"{random.randint(1000,9999)}" if gen else None,
            "route_progress": {"PENDING":0.0,"OUT_FOR_DELIVERY":0.55,"DELIVERED":1.0}[status],
        })
    return out

def gen_alerts():
    types = [("LOW_STOCK","MEDIUM","Paneer (ITM-004): 8 left, threshold 10"),
             ("OUT_OF_STOCK","HIGH","Chicken Curry Base (ITM-011): 0 left, threshold 10"),
             ("ORDER_FAILED","HIGH","Order ORD-1042ABCD failed: insufficient stock"),
             ("DUPLICATE_ORDER","LOW","Duplicate request rejected (marker DUP-99A1B2)")]
    out = []
    for i in range(12):
        t, sev, msg = random.choice(types)
        out.append({"type": t, "severity": sev, "message": msg, "occurred_at": now_iso(i*240)})
    return out

def gen_kpis():
    return {
        "total_orders": 482, "total_customers": 231, "total_sales": 401,
        "total_revenue": 318540.0, "average_order_value": 794.5,
        "pending_orders": 14, "preparing_orders": 9, "ready_orders": 6,
        "out_for_delivery_orders": 11, "delivered_orders": 430, "cancelled_orders": 12,
    }

def gen_health():
    return {"status": "WARNING", "dependencies": {
        "application":"UP","database":"UP (4.2ms)","kafka_broker":"WARNING","kafka_producer":"UP",
        "disk":"OK (42% used)","memory":"OK (61% used)","cpu":"OK (23% used)","docker":"CONTAINERIZED"}}

def gen_monitoring():
    return {
        "generated_at": now_iso(),
        "application_health": {"status":"UP","environment":"production","build_version":"1.1.0-final"},
        "database": {"status":"UP","response_time_ms":4.2,"pool":{"size":10,"checked_in":8,"checked_out":2,"overflow":0}},
        "kafka": {"broker_reachable": True, "total_topics_visible": 14, "our_topics_present": {"order.created": True,"payment.completed": True}, "status":"UP"},
        "kafka_producer_status": "UP",
        "docker_status": "CONTAINERIZED",
        "dlq": {"total_dlq_messages": 3, "most_recent":[{"order_id":"ORD-9981ZZZ","transaction_id":"TXN-AA11","moved_at": now_iso(600)}]},
        "duplicate_orders": {"total": 7, "recent":[{"order_id":f"DUP-{i}","transaction_id":f"KEY-{i}","detected_at": now_iso(i*300)} for i in range(5)]},
        "failed_orders": {"total": 5, "recent":[{"order_id":f"ORD-F{i}","transaction_id":f"TXN-F{i}","reason":"Insufficient stock for ITM-00"+str(i), "failed_at": now_iso(i*400)} for i in range(4)]},
        "retry_queue": {"kafka_publish_retry_total": 6, "kafka_consume_retry_total": 2},
        "inventory_summary": {"total_items": 42, "low_stock_count": 5, "out_of_stock_count": 1, "total_stock_value": 812400.0},
        "kafka_summary": {"broker_reachable": True, "our_topics_present": {}, "publish_success_total": 940, "publish_retry_total": 6, "publish_dlq_total": 3, "consume_success_total": 918, "consume_retry_total": 2, "consume_dlq_total": 1, "processing_time_ms": {"count": 918, "avg_ms": 12.4, "max_ms": 88.1}},
        "api_summary": {"total_requests": 5820, "requests_4xx": 44, "requests_5xx": 3, "endpoints": {
            "GET /api/v1/orders": {"count": 1200, "avg_ms": 18.4, "max_ms": 120.0},
            "POST /api/v1/orders": {"count": 480, "avg_ms": 42.1, "max_ms": 210.0},
            "GET /api/v1/inventory": {"count": 900, "avg_ms": 9.2, "max_ms": 55.0},
            "GET /health": {"count": 2100, "avg_ms": 5.1, "max_ms": 30.0},
            "GET /api/v1/dashboard/kpis": {"count": 640, "avg_ms": 11.0, "max_ms": 40.0},
        }},
        "performance": {"cpu": {"status":"OK","percent_used": 23.4}, "memory": {"status":"OK","percent_used": 61.2}, "disk": {"status":"OK","percent_used": 42.0}},
        "recent_alerts": gen_alerts()[:8],
    }

ROUTES = {
    "/api/v1/dashboard/kpis": gen_kpis,
    "/api/v1/dashboard/live-orders": gen_live_orders,
    "/api/v1/dashboard/kitchen-ops": gen_kitchen,
    "/api/v1/dashboard/delivery-ops": gen_delivery,
    "/api/v1/dashboard/alerts": gen_alerts,
    "/api/v1/dashboard/monitoring": gen_monitoring,
    "/health": gen_health,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ROUTES:
            data = json.dumps(ROUTES[path]()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif path.startswith("/dashboard/"):
            fname = "operations_dashboard.html" if "operations" in path else "monitoring_dashboard.html"
            with open(f"/home/claude/oms360/oms360_project/app/static/{fname}", "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8811), Handler).serve_forever()
