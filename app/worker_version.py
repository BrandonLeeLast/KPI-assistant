"""
Worker version checking — detects when deployed worker is outdated.
"""
import urllib.request
import json

# Update this when releasing new worker template versions
LATEST_WORKER_VERSION = "1.0.0"


def check_worker_version(worker_url: str) -> tuple[bool, str, str]:
    """
    Check deployed worker version against latest.

    Returns: (is_outdated, deployed_version, latest_version)
    """
    if not worker_url or not worker_url.startswith("http"):
        return False, "", LATEST_WORKER_VERSION

    try:
        req = urllib.request.Request(
            f"{worker_url.rstrip('/')}/version",
            headers={"User-Agent": "KPI-Assistant/1.0 (Windows)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            deployed_version = data.get("version", "0.0.0")

            # Simple version comparison (assumes semver x.y.z format)
            deployed_parts = [int(x) for x in deployed_version.split(".")]
            latest_parts = [int(x) for x in LATEST_WORKER_VERSION.split(".")]

            is_outdated = deployed_parts < latest_parts
            return is_outdated, deployed_version, LATEST_WORKER_VERSION
    except Exception:
        # Can't determine version — assume up to date to avoid false alarms
        return False, "unknown", LATEST_WORKER_VERSION
