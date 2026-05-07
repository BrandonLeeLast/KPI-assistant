"""
KPI Worker deployment helper.

Pulls the worker template from GitHub, runs wrangler login,
sets the AUTH_TOKEN secret, deploys, and returns the worker URL.

Steps:
  1. Check Node.js is installed
  2. Download worker template zip from GitHub
  3. Extract to %APPDATA%/KPI-assistant/worker/
  4. npm install (installs wrangler)
  5. npx wrangler login (opens browser for CF OAuth)
  6. Generate a random AUTH_TOKEN
  7. npx wrangler secret put AUTH_TOKEN (pipes token to wrangler)
  8. npx wrangler deploy (deploys worker)
  9. Parse worker URL from deploy output
  10. Save URL + token to app config
"""

import os
import sys
import shutil
import subprocess
import threading
import urllib.request
import zipfile

# Template repo — the worker source users deploy to their own CF account
TEMPLATE_ZIP_URL = (
    "https://github.com/BrandonLeeLast/KPI-assistant-worker/archive/refs/heads/main.zip"
)

_APPDATA    = os.environ.get("APPDATA", os.path.expanduser("~"))
_WORKER_DIR = os.path.join(_APPDATA, "KPI-assistant", "worker")
_SI = None  # set on first use — hides console windows

# Common Node.js install locations on Windows (PyInstaller strips PATH)
_NODE_DIRS = [
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "nodejs"),
    os.path.join(os.environ.get("APPDATA", ""), "nvm", "current"),
]


def _full_env() -> dict:
    """Return os.environ with common Node.js paths appended to PATH."""
    env  = os.environ.copy()
    path = env.get("PATH", "")

    candidates = list(_NODE_DIRS)

    # nvm for Windows stores versioned dirs: %APPDATA%\nvm\v22.x.x\
    nvm_root = os.path.join(os.environ.get("APPDATA", ""), "nvm")
    if os.path.isdir(nvm_root):
        try:
            for entry in sorted(os.listdir(nvm_root), reverse=True):
                d = os.path.join(nvm_root, entry)
                if os.path.isdir(d) and entry.startswith("v"):
                    candidates.append(d)
                    break  # newest version only
        except OSError:
            pass

    for d in candidates:
        if os.path.isdir(d) and d not in path:
            path = d + os.pathsep + path
    env["PATH"] = path
    return env


def _get_si():
    global _SI
    if _SI is None:
        _SI = subprocess.STARTUPINFO()
        _SI.dwFlags    |= subprocess.STARTF_USESHOWWINDOW
        _SI.wShowWindow = 0
    return _SI


def _run(cmd: list, cwd: str = None, timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            stdin=subprocess.DEVNULL,  # Prevent hanging on input
            timeout=timeout, startupinfo=_get_si(),
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=_full_env(),
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except FileNotFoundError:
        return -1, "", f"Not found: {cmd[0]}"


def _run_visible(cmd: list, cwd: str = None,
                 timeout: int = 120) -> tuple[int, str, str]:
    """Run with a visible window — needed for wrangler login (browser OAuth)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, timeout=timeout, env=_full_env(),
        )
        return r.returncode, "", ""
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except FileNotFoundError:
        return -1, "", f"Not found: {cmd[0]}"


def _run_with_console(cmd: list, cwd: str = None,
                      timeout: int = 180) -> tuple[int, str, str]:
    """Run with visible console window — shows live output, also captures for parsing."""
    try:
        # No CREATE_NO_WINDOW — lets a console pop up
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=timeout,
            env=_full_env(),
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except FileNotFoundError:
        return -1, "", f"Not found: {cmd[0]}"


def _find_exe(name: str) -> str | None:
    """Find node.exe or npm.cmd in common Windows paths."""
    # Try shutil.which first with expanded PATH
    exe = shutil.which(name, path=_full_env()["PATH"])
    if exe:
        return exe

    # Explicit search in common dirs
    exts = [".exe", ".cmd", ""]
    for d in [r"C:\Program Files\nodejs",
              r"C:\Program Files (x86)\nodejs",
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "nodejs")]:
        for ext in exts:
            path = os.path.join(d, name + ext)
            if os.path.isfile(path):
                return path

    # nvm versioned dirs
    nvm_root = os.path.join(os.environ.get("APPDATA", ""), "nvm")
    if os.path.isdir(nvm_root):
        try:
            for entry in sorted(os.listdir(nvm_root), reverse=True):
                if entry.startswith("v"):
                    d = os.path.join(nvm_root, entry)
                    for ext in exts:
                        path = os.path.join(d, name + ext)
                        if os.path.isfile(path):
                            return path
        except OSError:
            pass
    return None


def check_node() -> tuple[bool, str]:
    node_exe = _find_exe("node")
    if node_exe:
        code, out, _ = _run([node_exe, "--version"])
        if code == 0:
            return True, out
    return False, ""


def check_npm() -> tuple[bool, str]:
    npm_exe = _find_exe("npm")
    if npm_exe:
        code, out, _ = _run([npm_exe, "--version"])
        if code == 0:
            return True, out
    return False, ""


def deploy_worker(on_log, on_done, on_error) -> None:
    """Run full deployment on a background thread."""
    threading.Thread(
        target=_deploy_worker,
        args=(on_log, on_done, on_error),
        daemon=True,
    ).start()


def _deploy_worker(on_log, on_done, on_error) -> None:
    def log(msg): on_log(msg)

    # ── Step 1: Check Node ────────────────────────────────────────────────────
    log("🔍 Checking Node.js...")
    ok, ver = check_node()
    if not ok:
        on_error(
            "Node.js is not installed.\n\n"
            "Download from: https://nodejs.org\n"
            "Install it, then click Deploy again."
        )
        return
    log(f"✅ Node.js {ver} found.")

    ok, ver = check_npm()
    if not ok:
        on_error("npm not found — reinstall Node.js from https://nodejs.org")
        return
    log(f"✅ npm {ver} found.")

    # Find full paths to executables
    npm_exe = _find_exe("npm")
    npx_exe = _find_exe("npx")
    if not npm_exe or not npx_exe:
        on_error("npm or npx not found — reinstall Node.js")
        return

    # ── Step 2: Download template ─────────────────────────────────────────────
    log("⬇️  Downloading worker template...")
    zip_path = os.path.join(_APPDATA, "KPI-assistant", "worker_template.zip")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    try:
        urllib.request.urlretrieve(TEMPLATE_ZIP_URL, zip_path)
    except Exception as e:
        on_error(f"Failed to download template:\n{e}")
        return
    log("✅ Template downloaded.")

    # ── Step 3: Extract ───────────────────────────────────────────────────────
    log("📦 Extracting template...")
    if os.path.exists(_WORKER_DIR):
        shutil.rmtree(_WORKER_DIR)
    os.makedirs(_WORKER_DIR, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(_WORKER_DIR)
    except Exception as e:
        on_error(f"Failed to extract template:\n{e}")
        return

    # Find the extracted subfolder (GitHub zips add repo-branch/ prefix)
    subdirs = [d for d in os.listdir(_WORKER_DIR)
               if os.path.isdir(os.path.join(_WORKER_DIR, d))]
    if not subdirs:
        on_error("Template extraction failed — no folder found.")
        return

    # Navigate into my-worker subfolder where wrangler.jsonc lives
    worker_root = os.path.join(_WORKER_DIR, subdirs[0], "my-worker")
    if not os.path.exists(worker_root):
        worker_root = os.path.join(_WORKER_DIR, subdirs[0])
    log(f"✅ Extracted to: {worker_root}")

    # ── Step 4: npm install ───────────────────────────────────────────────────
    log("📦 Installing dependencies (wrangler)...")
    code, out, err = _run([npm_exe, "install"], cwd=worker_root, timeout=120)
    if code != 0:
        on_error(f"npm install failed:\n{err}")
        return
    log("✅ Dependencies installed.")

    # ── Step 5: wrangler login ────────────────────────────────────────────────
    log("🌐 Opening browser for Cloudflare login...")
    log("   Complete the login in your browser, then come back here.")
    code, out, err = _run_visible(
        [npx_exe, "wrangler", "login"],
        cwd=worker_root, timeout=300
    )
    if code != 0:
        on_error(f"Cloudflare login failed:\n{err or out}")
        return
    log("✅ Cloudflare login successful.")

    # ── Step 6: Deploy ────────────────────────────────────────────────────────
    log("🚀 Deploying worker to Cloudflare...")
    log("   (Console window will show live progress)")
    code, out, err = _run_with_console(
        [npx_exe, "wrangler", "deploy"],
        cwd=worker_root, timeout=180
    )
    if code != 0:
        on_error(f"Deployment failed:\n{err or out}")
        return
    log("✅ Worker deployed!")

    # ── Step 7: Parse worker URL from output ──────────────────────────────────
    import re
    worker_url = ""
    for line in (out + "\n" + err).splitlines():
        if "workers.dev" in line:
            match = re.search(r'https://[\w\-\.]+\.workers\.dev', line)
            if match:
                worker_url = match.group(0)
                break

    if not worker_url:
        on_error(
            "Worker deployed but could not detect URL.\n"
            "Check your Cloudflare dashboard for the worker URL,\n"
            "then paste it manually in Configuration → API Key."
        )
        return

    log(f"🎉 Worker URL: {worker_url}")

    # ── Step 8: Auto-accept Llama license ─────────────────────────────────────
    log("📝 Accepting Llama 3.2 license terms...")
    import json
    import base64
    # Tiny 1x1 transparent PNG
    tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = json.dumps({"prompt": "agree", "image_base64": tiny_png}).encode()

    try:
        req = urllib.request.Request(
            worker_url, data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()  # Ignore response
        log("✅ License accepted.")
    except Exception:
        log("⚠️  License acceptance skipped (you may need to accept manually on first use)")

    on_done(worker_url)
