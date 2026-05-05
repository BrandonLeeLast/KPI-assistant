import os
import sys
import configparser

APP_DIR     = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")


def get_default_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg['DEFAULT'] = {
        'GEMINI_API_KEY':  'YOUR_API_KEY_HERE',
        'MY_LEVEL':        'Intermediate',
        'WATCH_FOLDER':    os.path.join(os.path.expanduser('~'), 'Documents', 'Temp').replace('\\', '/'),
        'BASE_KPI_FOLDER': os.path.join(os.path.expanduser('~'), 'Documents', 'KPI_Evidence').replace('\\', '/'),
        'LOG_FILE':        os.path.join(os.path.expanduser('~'), 'Documents', 'processed_log.txt').replace('\\', '/'),
    }
    return cfg


def load_config() -> configparser.ConfigParser:
    cfg = get_default_config()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    else:
        with open(CONFIG_PATH, 'w') as f:
            cfg.write(f)
    return cfg


def save_config(cfg: configparser.ConfigParser) -> None:
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)
