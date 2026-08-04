"""
shared_ui/ - small, dependency-light Tkinter UI pieces used by BOTH
OMS360 Enterprise AI Platform.exe (launcher/) and OMS360 License
Generator.exe (generator/).

This package exists so the two executables don't have to depend on each
other to share a couple of dialogs: launcher/ pulls in db_provisioner,
uvicorn, and the whole app.main import chain, none of which the Generator
should ever need to bundle. Anything placed here must stay limited to
tkinter + licensing.keys (branding constants) - no provisioning, no
networking, no app.* imports - so that importing it from generator/main.py
never drags in launcher-only weight.
"""
