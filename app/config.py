import os
import sys
import configparser

# %APPDATA%\KPI-assistant\ — survives reinstalls, EXE moves, and Windows updates
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KPI-assistant")
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.ini")

# Kept for PyInstaller — resolves bundled assets (version.json, etc.)
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))


def _ensure_appdata_dir() -> None:
    """Create %APPDATA%/KPI-assistant/ on first launch if it doesn't exist."""
    os.makedirs(APPDATA_DIR, exist_ok=True)


def get_default_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg['DEFAULT'] = {
        'GEMINI_API_KEY':  'YOUR_API_KEY_HERE',
        'MY_LEVEL':        'Intermediate',
        'WATCH_FOLDER':    os.path.join(os.path.expanduser('~'), 'Documents', 'Temp').replace('\\', '/'),
        'BASE_KPI_FOLDER': os.path.join(os.path.expanduser('~'), 'Documents', 'KPI_Evidence').replace('\\', '/'),
        # Log lives in APPDATA — never next to the EXE or in Documents
        'LOG_FILE':        os.path.join(APPDATA_DIR, 'processed_log.json').replace('\\', '/'),
    }
    return cfg


def load_config() -> configparser.ConfigParser:
    _ensure_appdata_dir()
    cfg = get_default_config()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    else:
        # First run — write defaults so the user has something to edit
        with open(CONFIG_PATH, 'w') as f:
            cfg.write(f)
    return cfg


def save_config(cfg: configparser.ConfigParser) -> None:
    _ensure_appdata_dir()
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)
