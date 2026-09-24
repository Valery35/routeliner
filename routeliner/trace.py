# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Журнал работы модуля.

Когда у заказчика «ничего не происходит», понять, что именно не
происходит, нельзя: нет ни ошибки, ни следа. Поэтому модуль пишет в файл
каждый свой шаг, и успешный тоже. По одному файлу видно, какая версия
работает, какой инструмент запускали, с какими параметрами, чем кончилось
и где упало.

Файл routeliner.log лежит в папке профиля QGIS и открывается кнопкой
«Журнал» в окне «О модуле». Его достаточно приложить к письму.

QGIS здесь не нужен: путь подставляется при загрузке модуля, а проверки
задают свою папку.
"""

import datetime
import os
import traceback

NAME = "routeliner.log"
MAX_BYTES = 2 * 1024 * 1024      # больше - старый журнал уходит в .old

_PATH = None


def path():
    return _PATH


def setup(folder=None, name=NAME):
    """Заводит журнал. Возвращает путь или пустую строку, если писать
    некуда: журнал не должен мешать работе."""
    global _PATH
    if folder is None:
        try:
            from qgis.core import QgsApplication
            folder = QgsApplication.qgisSettingsDirPath()
        except Exception:  # nosec - вне QGIS
            folder = ""
    if not folder:
        _PATH = None
        return ""
    try:
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, name)
        if os.path.isfile(p) and os.path.getsize(p) > MAX_BYTES:
            os.replace(p, p + ".old")
        with open(p, "a", encoding="utf-8"):
            pass
        _PATH = p
    except Exception:  # nosec - недоступную папку лучше узнать здесь
        _PATH = None
        return ""
    return _PATH


def _line(mark, message):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "%s  %-7s %s" % (stamp, mark, message)


def write(mark, message):
    """Дописывает строку. Молчит, если файл недоступен."""
    if not _PATH:
        return
    try:
        with open(_PATH, "a", encoding="utf-8") as fh:
            fh.write(_line(mark, message) + "\n")
    except Exception:  # nosec
        pass


def step(message):
    write("ШАГ", message)


def data(message):
    write("ДАННЫЕ", message)


def fail(message, exc=None):
    """Ошибка и, если она пришла исключением, весь её стек."""
    write("ОШИБКА", message)
    if exc is not None:
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        for ln in text.rstrip().splitlines():
            write("", "    " + ln)


def tail(n=200):
    """Последние n строк журнала, для окна «О модуле» и проверок."""
    if not _PATH or not os.path.isfile(_PATH):
        return []
    try:
        with open(_PATH, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-n:]
    except Exception:  # nosec
        return []
