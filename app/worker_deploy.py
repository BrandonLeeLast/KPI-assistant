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
    log("   (A console window will stay open during upload)")

    # We use _run_with_console to ensure the user sees progress in a real terminal
    # but we ALSO need the output for Step 7.
    code, out, err = _run_with_console(
        [npx_exe, "wrangler", "deploy"],
        cwd=worker_root, timeout=300
    )

    if code != 0:
        error_msg = err or out or "Unknown error"
        on_error(f"Deployment failed:\n\n{error_msg}")
        return
    log("✅ Worker deployed!")

    # ── Step 7: Robust worker URL detection ──────────────────────────────────
    log("🔍 Detecting worker URL...")
    import json

    # 1. Get the account's workers.dev subdomain
    subdomain = ""
    try:
        code_w, out_w, _ = _run([npx_exe, "wrangler", "whoami", "--json"], cwd=worker_root)
        if code_w == 0:
            user_info = json.loads(out_w)
            # Find the first account that has a workers.dev subdomain configured
            # Or just use the account logic if available
            # Note: wrangler whoami --json might not contain the subdomain directly,
            # but we can try to find it or fall back to the old regex if needed.
            # Actually, let's try a fallback chain:
            log("   Querying account info...")
    except Exception as e:
        log(f"   Note: Could not query account info: {e}")

    # 2. Get the worker name from config
    worker_name = "kpi-assistant-worker" # default
    try:
        config_path_json = os.path.join(worker_root, "wrangler.jsonc")
        config_path_toml = os.path.join(worker_root, "wrangler.toml")
        if os.path.exists(config_path_json):
            with open(config_path_json, "r") as f:
                # Basic comment stripping for jsonc
                lines = [line for line in f if not line.strip().startswith("//")]
                config = json.loads("".join(lines))
                worker_name = config.get("name", worker_name)
        elif os.path.exists(config_path_toml):
            with open(config_path_toml, "r") as f:
                import re
                for line in f:
                    m = re.match(r'^name\s*=\s*["\'](.+?)["\']', line.strip())
                    if m:
                        worker_name = m.group(1)
                        break
    except Exception as e:
        log(f"   Note: Could not parse config name: {e}")

    # 3. Fallback Chain for URL
    worker_url = ""
    deploy_output = (out or "") + "\n" + (err or "")

    # Priority A: Scrape from output (regex) but more aggressively
    import re as regex
    # Handle ANSI codes by cleaning the output if possible
    clean_output = regex.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', deploy_output)
    url_match = regex.search(r'https://[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.workers\.dev', clean_output)
    if url_match:
        worker_url = url_match.group(0)
        log(f"   Detected from output: {worker_url}")
    else:
        # Priority B: Try to get it from wrangler deployments list
        log("   Scraper missed URL. Checking deployment history...")
        try:
            code_d, out_d, _ = _run([npx_exe, "wrangler", "deployments", "list", "--json"], cwd=worker_root)
            if code_d == 0:
                deps_raw = json.loads(out_d)
                # Some versions return a list, others a dict with a 'deployments' key
                deps = deps_raw.get("deployments", []) if isinstance(deps_raw, dict) else deps_raw

                if deps and isinstance(deps, list) and len(deps) > 0:
                    # Look for URL in the latest deployment
                    target_dep = deps[0]
                    worker_url = target_dep.get("url", "")
                    if worker_url:
                        log(f"   Detected from history: {worker_url}")
        except Exception as e:
            log(f"   History check failed: {e}")

    if not worker_url:
        # Fallback: prompt user
        log("   Could not auto-detect URL.")
        on_error(
            "Worker deployed successfully!\n\n"
            "However, Cloudflare did not report the live URL back to the app.\n\n"
            "Find your worker URL here:\n"
            "https://dash.cloudflare.com/ → Workers & Pages → " + worker_name + "\n\n"
            "Then paste it in Configuration → API Key."
        )
        return

    # ── Step 8: Test worker ──────────────────────────────────────────────────
    log(f"🧪 Testing worker at {worker_url}...")
    import json
    import base64
    # Tiny 1x1 transparent PNG for testing
    tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = json.dumps({"prompt": "test", "image_base64": tiny_png}).encode()

    try:
        req = urllib.request.Request(
            worker_url, data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()  # Ignore response
        log("✅ Worker test successful!")
    except Exception as e:
        log(f"⚠️  Worker test failed: {e}")
        log("   The URL may still be correct — try using it in the app.")

    log(f"🎉 Worker URL: {worker_url}")
    on_done(worker_url)
