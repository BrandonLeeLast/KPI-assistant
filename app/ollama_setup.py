"""
Ollama auto-setup — handles everything in the background:
  1. Check Docker is installed and running
  2. Pull ollama/ollama image if not present
  3. Start (or restart) the ollama container
  4. Pull the selected vision model inside the container
  5. Verify the API is responding

All steps stream progress via a callback so the UI can show live output.
"""

import subprocess
import urllib.request
import json
import time
import threading


OLLAMA_CONTAINER = "kpi-ollama"
OLLAMA_IMAGE     = "ollama/ollama"
OLLAMA_PORT      = 11434
OLLAMA_URL       = f"http://localhost:{OLLAMA_PORT}"


def _run(cmd: list, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def is_docker_installed() -> bool:
    code, _, _ = _run(["docker", "--version"])
    return code == 0


def is_docker_running() -> bool:
    code, _, _ = _run(["docker", "info"])
    return code == 0


def is_container_running() -> bool:
    code, out, _ = _run(["docker", "inspect", "-f", "{{.State.Running}}", OLLAMA_CONTAINER])
    return code == 0 and out.strip() == "true"


def is_container_exists() -> bool:
    code, _, _ = _run(["docker", "inspect", OLLAMA_CONTAINER])
    return code == 0


def is_api_ready() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def is_model_pulled(model: str) -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            names = [m["name"] for m in data.get("models", [])]
            # match base name e.g. "llava:13b" in "llava:13b"
            return any(model in n or n in model for n in names)
    except Exception:
        return False


def setup_ollama(model: str, on_log, on_done, on_error) -> None:
    """
    Run the full setup in a background thread.
    on_log(msg, level)  — progress messages for the UI log
    on_done()           — called when setup completes successfully
    on_error(msg)       — called on unrecoverable failure
    """
    threading.Thread(
        target=_setup_worker,
        args=(model, on_log, on_done, on_error),
        daemon=True,
    ).start()


def _setup_worker(model: str, on_log, on_done, on_error) -> None:
    def log(msg, level="info"):
        on_log(msg, level)

    # ── Step 1: Docker installed? ─────────────────────────────────────────────
    log("🔍 Checking Docker installation...")
    if not is_docker_installed():
        on_error(
            "Docker is not installed.\n\n"
            "Download Docker Desktop from:\n"
            "https://www.docker.com/products/docker-desktop\n\n"
            "Install it, start it, then click Setup again."
        )
        return
    log("✅ Docker is installed.", "success")

    # ── Step 2: Docker daemon running? ────────────────────────────────────────
    log("🔍 Checking Docker is running...")
    if not is_docker_running():
        on_error(
            "Docker Desktop is installed but not running.\n\n"
            "Please start Docker Desktop from your taskbar or Start Menu, "
            "wait for it to fully load, then click Setup again."
        )
        return
    log("✅ Docker is running.", "success")

    # ── Step 3: Pull ollama/ollama image if needed ────────────────────────────
    log("🔍 Checking for Ollama Docker image...")
    code, out, _ = _run(["docker", "images", "-q", OLLAMA_IMAGE])
    if not out:
        log(f"⬇️  Pulling {OLLAMA_IMAGE} image (this may take a few minutes)...")
        code, out, err = _run(["docker", "pull", OLLAMA_IMAGE], timeout=300)
        if code != 0:
            on_error(f"Failed to pull Ollama image:\n{err}")
            return
        log("✅ Ollama image downloaded.", "success")
    else:
        log("✅ Ollama image already present.", "success")

    # ── Step 4: Start or create container ─────────────────────────────────────
    if is_container_running():
        log("✅ Ollama container already running.", "success")
    elif is_container_exists():
        log("🔄 Starting existing Ollama container...")
        code, _, err = _run(["docker", "start", OLLAMA_CONTAINER])
        if code != 0:
            on_error(f"Failed to start container:\n{err}")
            return
        log("✅ Ollama container started.", "success")
    else:
        log("🚀 Creating Ollama container...")
        code, _, err = _run([
            "docker", "run", "-d",
            "--name",    OLLAMA_CONTAINER,
            "-v",        "ollama:/root/.ollama",
            "-p",        f"{OLLAMA_PORT}:{OLLAMA_PORT}",
            "--restart", "always",
            OLLAMA_IMAGE,
        ], timeout=60)
        if code != 0:
            on_error(f"Failed to create container:\n{err}")
            return
        log("✅ Ollama container created.", "success")

    # ── Step 5: Wait for API to be ready ──────────────────────────────────────
    log("⏳ Waiting for Ollama API to be ready...")
    for attempt in range(30):
        if is_api_ready():
            break
        time.sleep(1)
        if attempt == 29:
            on_error("Ollama API did not start within 30 seconds. Try again.")
            return
    log("✅ Ollama API is ready.", "success")

    # ── Step 6: Pull model ────────────────────────────────────────────────────
    if is_model_pulled(model):
        log(f"✅ Model '{model}' already downloaded.", "success")
    else:
        log(f"⬇️  Pulling model '{model}' — this is a large download, please wait...")
        log("   (llava:13b ≈ 8GB, gemma3:12b ≈ 7GB — may take 10–30 mins)", "warn")

        # Stream pull output so the user sees progress
        try:
            si = subprocess.STARTUPINFO()
            proc = subprocess.Popen(
                ["docker", "exec", OLLAMA_CONTAINER, "ollama", "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                startupinfo=si,
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    log(f"   {line}", "info")
            proc.wait()
            if proc.returncode != 0:
                on_error(f"Failed to pull model '{model}'. Check the model name and try again.")
                return
        except Exception as e:
            on_error(f"Error pulling model: {e}")
            return

        log(f"✅ Model '{model}' downloaded successfully.", "success")

    # ── Done ──────────────────────────────────────────────────────────────────
    log("🎉 Ollama is ready! Switch to Configuration, select Ollama as provider and save.", "success")
    on_done()


def stop_container() -> None:
    """Stop the Ollama container — called when app exits if user wants."""
    _run(["docker", "stop", OLLAMA_CONTAINER])


def get_status() -> dict:
    """Return current status dict for display in the UI."""
    docker_ok    = is_docker_installed() and is_docker_running()
    container_ok = is_container_running() if docker_ok else False
    api_ok       = is_api_ready() if container_ok else False
    return {
        "docker":    docker_ok,
        "container": container_ok,
        "api":       api_ok,
    }
