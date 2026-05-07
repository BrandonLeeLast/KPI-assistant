"""
Build-time secrets baked into the EXE via PyInstaller --collect-data.
In dev, reads from environment variable KPI_WORKER_TOKEN.
In production EXE, the token is written to _token.txt at build time by CI.
"""

import os
import sys


# The default KPI Worker endpoint
KPI_WORKER_URL = "https://kpi-assistant-ai.brandonl-9ff.workers.dev"


def get_worker_token() -> str:
    """
    Returns the auth token for the KPI Worker.
    Priority:
      1. Compiled _token.txt (PyInstaller bundle)
      2. KPI_WORKER_TOKEN environment variable (dev/CI)
      3. Empty string (worker should reject if token required)
    """
    # Check PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        token_path = os.path.join(sys._MEIPASS, "_token.txt")
        try:
            with open(token_path, "r") as f:
                return f.read().strip()
        except Exception:
            pass

    # Check alongside EXE (dev builds)
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    token_path = os.path.join(exe_dir, "_token.txt")
    try:
        with open(token_path, "r") as f:
            return f.read().strip()
    except Exception:
        pass

    # Fall back to environment variable
    return os.environ.get("KPI_WORKER_TOKEN", "")


WORKER_TOKEN = get_worker_token()
