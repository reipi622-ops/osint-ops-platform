---
name: Python on Nix
description: How to run pip and uvicorn correctly in the Replit Nix environment
---

# Python on Nix — runtime setup

## The rule
In this Nix environment, `pip` and `uvicorn` are not on PATH. Always use:
- `python3 -m pip install -r requirements.txt --quiet --break-system-packages`
- `python3 -m uvicorn main:app ...`

**Why:** Nix enforces PEP 668, which blocks bare `pip install` from modifying system packages. The `--break-system-packages` flag or `--user` flag is required. Bare `uvicorn` is never on PATH; invoke via the Python module system.

**How to apply:** Any `run.sh` for a Python FastAPI service must use these forms. Pre-installing deps via `bash` before the workflow starts speeds up the first launch significantly.
