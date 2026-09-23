# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Двуязычие интерфейса (RU/EN).

Словарный слой, как в Isoliner3D: исходные строки в коде русские, при
любой нерусской локали QGIS они подменяются английскими по таблице
TRANSLATIONS (translations.py). Нет перевода - остаётся русская строка.
QGIS на верхнем уровне не импортируется, поэтому модуль работает и в
проверках без QGIS (там язык английский, если его не задать явно).
"""

_LANG = None  # 'ru' | 'en'; None - ещё не определён


def set_language(lang):
    """Задать язык ('ru', 'en', 'ru_RU', ...). None - определить заново."""
    global _LANG
    if lang is None:
        _LANG = None
        return
    code = str(lang).strip().lower().replace("-", "_").split("_")[0]
    _LANG = "ru" if code == "ru" else "en"


def language():
    if _LANG is None:
        init_from_qgis()
    return _LANG or "en"


def init_from_qgis():
    loc = ""
    try:
        from qgis.core import QgsApplication
        loc = QgsApplication.instance().locale() or ""
    except Exception:  # nosec - вне QGIS
        loc = ""
    if not loc:
        try:
            from qgis.PyQt.QtCore import QSettings
            s = QSettings()
            if s.value("locale/overrideFlag", False, type=bool):
                loc = s.value("locale/userLocale", "")
        except Exception:  # nosec
            loc = ""
    set_language(loc or "en")
    return _LANG


def tr(s):
    """Строка на активном языке. Шаблоны с {полями} переводятся до format()."""
    if _LANG is None:
        init_from_qgis()
    if _LANG == "en":
        from .translations import TRANSLATIONS
        return TRANSLATIONS.get(s, s)
    return s
