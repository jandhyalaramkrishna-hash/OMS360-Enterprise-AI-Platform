"""launcher/ - OMS360 Enterprise AI Platform Student Practice Edition.

Builds into OMS360 Enterprise AI Platform.exe - the only file a student
receives. Composes, at the process level only, three things that are each
kept untouched:

  1. licensing/  - the license gate (see licensing/__init__.py)
  2. app.main:app - the real, unmodified OMS360 FastAPI application
  3. a bundled, embedded MySQL-compatible database engine, auto-provisioned
     on first run (db_provisioner.py) - see that module's docstring for
     exactly what it does and why

Nothing in this package imports FROM app/ or ai/ except db_provisioner.py's
one job of setting environment variables app/config.py already reads, and
main.py's one `from app.main import app` - it never edits, monkeypatches,
or duplicates any business logic.
"""
