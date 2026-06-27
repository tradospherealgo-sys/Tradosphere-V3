"""
Root entrypoint shim.

Render's Python autodetect defaults to `gunicorn app:app`. Rather than rely on
a custom Start Command, this module re-exports the Flask `app` so that both
`gunicorn app:app` and `gunicorn wsgi:app` work identically.

The backend modules import their siblings with bare names
(e.g. `from auth_manager_v3_1 import ...`), so the `backend/` directory must be
on sys.path before importing the server module.
"""

import os
import sys

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from tradosphere_saas_server_v3_1 import app  # noqa: E402,F401

if __name__ == "__main__":
    app.run()
