Sample request payloads for practicing against the OMS360 API (see
../docs/API_GUIDE.md and ../docs/TEST_CASES.md).

  create_order_request.json                  - a valid order (ORD-01)
  create_order_request_invalid_mobile.json    - triggers a 422 validation
                                                 error on purpose (ORD-NEG-01)
  restock_request.json                        - body for POST
                                                 /api/v1/inventory/restock

Paste these directly into the "Request body" box in Swagger (/docs), or
use them with curl/Postman against the running app's local address shown
in the status window.

OMS360 Enterprise AI Platform - Developed by ZelQA Technologies
