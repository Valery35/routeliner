"""Полнота перевода: у каждой строки интерфейса есть английская пара
с теми же полями подстановки."""
import os
import string
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))

from i18n_keys import ui_keys  # noqa: E402

from routeliner import i18n  # noqa: E402
from routeliner.translations import TRANSLATIONS  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "routeliner")


def _fields(s):
    return sorted(f for _, f, _, _ in string.Formatter().parse(s) if f)


def test_every_ui_string_translated():
    missing = [k for k in ui_keys(ROOT) if k not in TRANSLATIONS]
    assert not missing, missing


def test_placeholders_match():
    bad = [k for k, v in TRANSLATIONS.items() if _fields(k) != _fields(v)]
    assert not bad, bad


def test_switch_language():
    i18n.set_language("ru_RU")
    assert i18n.tr("Точечные события") == "Точечные события"
    i18n.set_language("en_US")
    assert i18n.tr("Точечные события") == "Point events"
    i18n.set_language(None)
