import os

_HERE = os.path.dirname(__file__)


def icon_path(name: str = "icon.svg") -> str:
    return os.path.join(_HERE, name)
