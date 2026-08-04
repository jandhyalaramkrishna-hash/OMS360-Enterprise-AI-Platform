# OMS360 Enterprise AI Platform — Student Guide

**Developed by ZelQA Technologies**
Student Practice Edition · Version 1.0.0

This guide walks you through everything you need to practice QA and API
testing against a real, running instance of the OMS360 Enterprise AI
Platform — no installation of Docker, MySQL, Kafka, or Python required.

---

## 1. What you received

You should have exactly one file plus this documentation folder:

```
Student_Practice_Kit/
├── OMS360 Enterprise AI Platform.exe   ← double-click this to start
├── README.txt                          ← quick-start summary
├── docs/
│   ├── STUDENT_GUIDE.md                ← this file
│   ├── API_GUIDE.md                    ← REST API reference
│   ├── TEST_CASES.md                   ← starter QA test case suite
│   └── DEFECT_REPORT_TEMPLATE.md       ← fill this in if you find a bug
└── sample-data/                        ← ready-to-use request payloads
```

You should **not** have received `OMS360 License Generator.exe` — that tool
stays with your instructor / ZelQA Technologies staff. If you have it,
delete it; it isn't meant for students and won't be useful to you.

## 2. Getting your license key

Your instructor generates a key for you using the internal License
Generator. Ask them for your key before you start — you cannot activate
without one. Keys look like `ZELQA-OMS360-...` and are long (100+
characters); that's expected — they carry a real cryptographic signature,
not just a short serial number. Copy the whole thing exactly.

## 3. Starting the application

1. Double-click `OMS360 Enterprise AI Platform.exe`.
2. A branded splash window appears immediately, telling you what's
   happening at each step.
3. **First launch only:** an Activation window asks for your License Key.
   Paste it in exactly as given (extra spaces or line breaks are fine —
   they're stripped automatically) and click **Activate**.
4. The splash reappears while the app sets up its own local database —
   this is one-time and can take a minute or two the very first time you
   run it; every launch after that is much faster.
5. Your browser opens automatically to the interactive API docs (Swagger)
   and the Operations Dashboard.
6. A small **status window** stays open the whole time the app is
   running. It shows:
   - Local address (where the app is running)
   - Licensed Student: your name
   - Evaluation Period: 7 days
   - Days Remaining
7. To stop the application, click **Stop & Exit** in the status window
   (or just close it). This also stops the local database cleanly.

You will **not** be asked for your license key again on later launches —
only if your 7-day evaluation period has ended.

## 4. What you can do

- Browse and try every REST endpoint live from Swagger (`/docs`) — see
  `API_GUIDE.md` for a guided tour.
- Watch the Operations Dashboard update as you create orders.
- Check `GET /health` and `GET /metrics` to see the platform's own
  observability endpoints.
- Explore the AI platform endpoints under `/api/v1/ai/...`, including
  `GET /api/v1/ai/platform/health`.
- Practice writing test cases against a real API and filing defect
  reports — see `TEST_CASES.md` and `DEFECT_REPORT_TEMPLATE.md`.

## 5. What's different from the full production deployment

This Student Practice Edition is a genuine, fully-functional copy of the
OMS360 API and dashboards — nothing about the business logic is different
or simplified. Two things are intentionally not included:

- **No Kafka.** The full production deployment uses Apache Kafka to
  automatically move an order through kitchen → payment → delivery in the
  background. That background process doesn't run here (there's no
  message broker bundled in this lightweight edition), so an order you
  create will stay at status `RECEIVED` instead of progressing on its own.
  Everything else — order creation, validation, inventory updates, audit
  trail, dashboards — works exactly as it does in production. If you want
  to see order status change, you're welcome to do it directly via the
  API for practice purposes; that's expected in a QA sandbox.
- **No shared/remote database.** Your data lives only on your own machine
  and isn't shared with other students or your instructor. Each student
  gets an independent, private sandbox.

## 6. Evaluation period and what happens after

Your license is valid for exactly **7 days**, counted from the moment you
first successfully activate it — not from when your instructor generated
it. After 7 days, the app will show:

> Evaluation Expired.
> Please contact ZelQA Technologies.

...and close. Contact your instructor if you need continued access.

## 7. Troubleshooting

| Symptom | What to try |
|---|---|
| "License key is invalid" | Re-copy the key from your instructor — make sure you copied the entire string, including the `ZELQA-OMS360-` prefix. |
| Splash window seems stuck on first launch | The very first launch sets up a local database and can take a minute or two — this is normal. Later launches are fast. |
| Browser didn't open automatically | Check the status window for "Local address" and open that URL manually, adding `/docs` for Swagger. |
| "Evaluation Expired" appears sooner than expected | The 7-day clock starts at your *first* activation, not at install or download time. |

If something still doesn't work, note exactly what you did and what you
saw (see `DEFECT_REPORT_TEMPLATE.md`) and contact your instructor.

---
OMS360 Enterprise AI Platform — Developed by ZelQA Technologies
