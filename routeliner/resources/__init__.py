import os


def icon_path() -> str:
    return os.path.join(os.path.dirname(__file__), "icon.svg")
