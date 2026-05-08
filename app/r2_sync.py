"""
Cloudflare R2 sync — uploads/downloads KPI evidence files via the deployed worker.

All R2 access is proxied through the user's worker (no separate API keys needed).
Worker endpoints used:
  POST /evidence/upload   { key, data (base64), mime }
  GET  /evidence/list     → { files: [{key, size, modified}] }
  GET  /evidence/download?key=<key>
"""

import os
import base64
import json
import urllib.request
import urllib.error
import urllib.parse


def _worker_url(raw_url: str) -> str:
    """Strip auth token if present and normalise trailing slash."""
    url = raw_url.split("|")[0].strip().rstrip("/")
    return url


def upload_file(worker_url: str, local_path: str, r2_key: str) -> bool:
    """Upload a single local file to R2. Returns True on success."""
    url = _worker_url(worker_url)
    if not url:
        return False
    try:
        with open(local_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        mime = "image/png" if local_path.lower().endswith(".png") else \
               "image/jpeg" if local_path.lower().endswith((".jpg", ".jpeg")) else \
               "text/plain"
        payload = json.dumps({"key": r2_key, "data": data, "mime": mime}).encode()
        req = urllib.request.Request(
            f"{url}/evidence/upload",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "KPEye/1.0 (Windows)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception:
        return False


def list_files(worker_url: str) -> list[dict]:
    """List all files in R2. Returns list of {key, size, modified}."""
    url = _worker_url(worker_url)
    if not url:
        return []
    try:
        req = urllib.request.Request(
            f"{url}/evidence/list",
            headers={"User-Agent": "KPEye/1.0 (Windows)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("files", [])
    except Exception:
        return []


def download_file(worker_url: str, r2_key: str, dest_path: str) -> bool:
    """Download a single file from R2 to dest_path. Returns True on success."""
    url = _worker_url(worker_url)
    if not url:
        return False
    try:
        encoded_key = urllib.parse.quote(r2_key, safe="")
        req = urllib.request.Request(
            f"{url}/evidence/download?key={encoded_key}",
            headers={"User-Agent": "KPEye/1.0 (Windows)"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception:
        return False


def sync_evidence_folder(worker_url: str, evidence_folder: str,
                          on_log=None) -> tuple[int, int]:
    """
    Upload all local evidence files not yet in R2.
    Returns (uploaded_count, skipped_count).
    """
    def log(msg):
        if on_log:
            on_log(msg)

    if not os.path.exists(evidence_folder):
        log("⚠️  Evidence folder not found.")
        return 0, 0

    # Get list of keys already in R2
    log("☁  Fetching R2 file list...")
    remote = {f["key"] for f in list_files(worker_url)}
    log(f"   {len(remote)} file(s) already in R2.")

    uploaded = skipped = 0
    for category in os.listdir(evidence_folder):
        cat_path = os.path.join(evidence_folder, category)
        if not os.path.isdir(cat_path):
            continue
        for filename in os.listdir(cat_path):
            local_path = os.path.join(cat_path, filename)
            if not os.path.isfile(local_path):
                continue
            r2_key = f"{category}/{filename}"
            if r2_key in remote:
                skipped += 1
                continue
            ok = upload_file(worker_url, local_path, r2_key)
            if ok:
                uploaded += 1
                log(f"   ↑ {r2_key}")
            else:
                log(f"   ✗ Failed: {r2_key}")

    return uploaded, skipped


def restore_from_r2(worker_url: str, evidence_folder: str,
                    on_log=None) -> tuple[int, int]:
    """
    Download all R2 files not present locally.
    Returns (downloaded_count, skipped_count).
    """
    def log(msg):
        if on_log:
            on_log(msg)

    log("☁  Fetching R2 file list...")
    remote_files = list_files(worker_url)
    log(f"   {len(remote_files)} file(s) in R2.")

    downloaded = skipped = 0
    for f in remote_files:
        key = f["key"]
        dest = os.path.join(evidence_folder, key.replace("/", os.sep))
        if os.path.exists(dest):
            skipped += 1
            continue
        ok = download_file(worker_url, key, dest)
        if ok:
            downloaded += 1
            log(f"   ↓ {key}")
        else:
            log(f"   ✗ Failed: {key}")

    return downloaded, skipped
