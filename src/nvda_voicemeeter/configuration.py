import json
from pathlib import Path

SETTINGS = Path.cwd() / "settings.json"


def config_from_json():
    data = {}
    if not SETTINGS.exists():
        return data
    with open(SETTINGS, "r") as f:
        data = json.load(f)
    return data


config = config_from_json()


def get(key, default=None):
    if key in config:
        return config[key]
    return default


def set(key, value):
    config[key] = value
    with open(SETTINGS, "w") as f:
        json.dump(config, f)


def delete(key):
    del config[key]
    with open(SETTINGS, "w") as f:
        json.dump(config, f)
