"""
WSGI entry point for Render / Railway / gunicorn.

The backend modules import their siblings with bare names
(e.g. `from auth_manager_v3_1 import ...`), so the `backend/` directory
must be on sys.path. We add it here, then import the Flask `app`.

Run with:  gunicorn wsgi:app
"""

import os
import sys

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from tradosphere_saas_server_v3_1 import app  # noqa: E402

if __name__ == "__main__":
    app.run()
