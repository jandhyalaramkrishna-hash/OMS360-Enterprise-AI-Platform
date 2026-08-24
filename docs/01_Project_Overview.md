# 01 — Project Overview

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**Last updated:** 2026-08-04 (documentation reorganization)

This is the entry point into the project's documentation. Start here, then
follow the numbered set in `docs/README.md`.

## 1. What This Project Is

360 Food Delivery Online Platform (OMS-360) is a comprehensive,
enterprise-grade, event-driven food ordering and delivery management
system designed to automate the complete order lifecycle — from customer
order placement to successful delivery. It integrates customers,
restaurants, kitchen operations, inventory management, payment processing,
delivery partners, and real-time operational dashboards into a single
centralized system, built on FastAPI, Apache Kafka, MySQL, Docker, and
REST APIs for scalable, reliable, asynchronous order processing.

The system emphasizes reliability through event-driven architecture,
transaction management, idempotent order processing, retry mechanisms,
dead-letter queue (DLQ) handling, structured logging, audit trails, health
monitoring, and operational dashboards. The architecture is designed to
support future enterprise enhancements such as AI-powered analytics,
predictive inventory, intelligent fraud detection, live GPS tracking,
geofencing, and real-time delivery optimization.

## 2. Three Lines of Work — Know Which Is Which

Every document in this set labels its content against one of three lines,
because they have very different build status. Confusing them is the
single most common way to misread this project's state:

| Line | Location | Status |
|---|---|---|
| **V1 — OMS-360 Business Platform** | `app/` | **Built, running code.** Spot-verified baseline. |
| **AI Enterprise Platform / AI Copilot** | `ai/` | **Built.** 393+ automated tests passing, mock-based throughout (no real vendor LLM). Development on this line closed at v1.0.0. |
| **V2 — AI Customer Support Chatbot** | `docs/business/`, `docs/architecture/*-01-...`, QA suite: `docs/07_Test_Plan.md` §8 / `docs/08_Test_Cases.md` / `docs/09_API_Test_Cases.md` §2 | **Documented only — zero lines of code.** Full BRD/architecture/QA suite exists; status "Documentation Complete, Pending Integration." |

## 3. Objectives (from the original project charter)

- Build an end-to-end online food ordering platform.
- Implement an event-driven architecture using Apache Kafka.
- Design scalable REST APIs using FastAPI.
- Manage customer orders through the complete lifecycle.
- Perform inventory validation and automatic stock updates.
- Simulate kitchen workflow and order preparation.
- Manage delivery assignment and order fulfillment.
- Maintain complete order traceability using audit logs.
- Implement retry mechanisms and Dead Letter Queue (DLQ) handling for failed Kafka events.
- Prevent duplicate order processing using idempotency.
- Provide structured logging and centralized exception handling.
- Expose Health and Metrics APIs for operational monitoring.
- Deliver real-time operational dashboards for business visibility.
- Containerize the application using Docker for simplified deployment.
- Build a modular architecture that can be extended with AI capabilities in future versions.

## 4. Enterprise Modules (V1 scope)

Customer Order Management, Restaurant Management, Menu Management,
Inventory Management, Kitchen Processing, Payment Processing, Kafka Event
Processing, Delivery Management, Notification Service, Health Monitoring,
Metrics Monitoring, Audit Trail, Retry & Dead Letter Queue (DLQ),
Operations Dashboard, API Documentation (Swagger/OpenAPI).

## 5. Tech Stack (as-built, V1)

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 (ORM) + Pydantic v2 + PyMySQL |
| Database | MySQL 8 (`oms360_db`) |
| Messaging | Apache Kafka via `confluent-kafka` |
| Dashboards | Static HTML + vanilla JS, 6s polling |
| Containerization | Docker Compose (`mysql`, `zookeeper`, `kafka`, `api`, `consumer`) |
| AI layer | `ai/` — Provider Framework, RAG, MCP, Multi-Agent, Evaluation, Enterprise Integration (mock-based) |
| Auth | None implemented — documented, known gap |

Full detail: `docs/03_SRS.md` §1.

## 6. Future Roadmap (Version 2)

After V1 is stabilized, the platform is planned to evolve with: AI-powered
Order Validation, AI Fraud Detection, Predictive Inventory Management, AI
Delivery ETA Prediction, AI Root Cause Analysis, Live GPS Delivery
Tracking, Geofencing, Route Optimization, AI Chat Assistant, Natural
Language to SQL, Predictive Business Analytics, and Intelligent Dashboard
Insights. See `docs/roadmap/PROJECT-ROADMAP.md`.

## 7. Where the Governance Record Lives

Project governance (roles, decisions, risks, change history, sprint
narrative, phased roadmap) is kept separately from this QA/SDLC
documentation set, in `docs/governance/`, `docs/roadmap/`, and
`docs/release/` — see `docs/04_SDLC.md` §9 for how the two sets relate.

## 8. How to Use This Documentation Set

Read `docs/README.md` for the full index. In short: `02`–`05` are
requirements and process (BRS/SRS/SDLC/STLC), `06`–`12` are the test
program (strategy through summary report), `13`–`14` are release-facing
(notes/user guide), `15`–`16` are operational (installation/QA
automation), and `17`–`19` are the tooling-specific setup guides
(Newman/Allure/Jenkins).
