import os
import sys
import configparser

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KPI-assistant")
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.ini")
APP_DIR     = os.path.dirname(os.path.abspath(sys.argv[0]))


def _ensure_appdata_dir() -> None:
    os.makedirs(APPDATA_DIR, exist_ok=True)


def get_default_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg['DEFAULT'] = {
        # ── AI Provider ───────────────────────────────────────────────────────
        'AI_PROVIDER':   'Gemini',
        'API_KEY':       'YOUR_API_KEY_HERE',
        'AI_MODEL':      'gemini-2.5-flash',

        # ── Legacy key kept so old configs still load cleanly ─────────────────
        'GEMINI_API_KEY': 'YOUR_API_KEY_HERE',

        # ── Developer level ───────────────────────────────────────────────────
        'MY_LEVEL':      'Intermediate',   # Intern, Graduate, Junior, Intermediate, Senior, Tech Lead

        # ── Folders ───────────────────────────────────────────────────────────
        'WATCH_FOLDER':    os.path.join(os.path.expanduser('~'), 'Documents', 'Screenshots').replace('\\', '/'),
        'BASE_KPI_FOLDER': os.path.join(os.path.expanduser('~'), 'Documents', 'KPI_Evidence').replace('\\', '/'),
        'LOG_FILE':        os.path.join(APPDATA_DIR, 'processed_log.json').replace('\\', '/'),

        # ── Screenshot capture ────────────────────────────────────────────────
        'HOTKEY':          'ctrl+shift+s',
        'CAPTURE_FORMAT':  'PNG',
        'CAPTURE_DELAY':   '0',

        # ── Processing behaviour ──────────────────────────────────────────────
        'AUTO_PROCESS':    'true',
        'SHOW_CONTEXT':    'true',
        'KPA_CATEGORIES':  'Technical Mastery,Engineering Operations,Consultant Mindset,Communication & Collaboration,Leadership',
        'CONTEXT_PROMPT':  'Analyze the image and pick ONE KPA. Use the STAR Method. Format: CATEGORY | STAR SUMMARY.',

        # ── Notifications ─────────────────────────────────────────────────────
        'NOTIFY_ON_SUCCESS': 'false',
        'NOTIFY_ON_FAILURE': 'true',
    }
    return cfg


def load_config() -> configparser.ConfigParser:
    _ensure_appdata_dir()
    cfg = get_default_config()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
        # Migrate old GEMINI_API_KEY to new API_KEY if needed
        if cfg['DEFAULT'].get('API_KEY', '').startswith('YOUR_API') and \
           not cfg['DEFAULT'].get('GEMINI_API_KEY', '').startswith('YOUR_API'):
            cfg['DEFAULT']['API_KEY'] = cfg['DEFAULT']['GEMINI_API_KEY']
    else:
        with open(CONFIG_PATH, 'w') as f:
            cfg.write(f)
    return cfg


def save_config(cfg: configparser.ConfigParser) -> None:
    _ensure_appdata_dir()
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)
