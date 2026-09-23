# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Руководство и окно «О модуле». Версия и история читаются из metadata.txt."""

import os

_HERE = os.path.dirname(__file__)


def read_metadata():
    import configparser
    cp = configparser.ConfigParser(interpolation=None)
    with open(os.path.join(_HERE, "metadata.txt"), encoding="utf-8") as f:
        cp.read_file(f)
    return dict(cp["general"])


def manual_path():
    """PDF на языке интерфейса, иначе на другом языке."""
    from .i18n import language
    names = ["Routeliner.pdf", "Routeliner_en.pdf"]
    if language() == "en":
        names.reverse()
    for name in names:
        path = os.path.join(_HERE, "doc", name)
        if os.path.isfile(path):
            return path
    return ""


def open_manual(parent=None):
    from qgis.PyQt.QtCore import QUrl
    from qgis.PyQt.QtGui import QDesktopServices
    from qgis.PyQt.QtWidgets import QMessageBox
    from .i18n import tr
    path = manual_path()
    if path:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    else:
        QMessageBox.warning(parent, "Routeliner", tr("Руководство не найдено."))


def show_about(parent=None):
    from qgis.PyQt.QtWidgets import QMessageBox
    from .i18n import tr
    from .processing.common import help_footer
    md = read_metadata()
    text = ("<h3>Routeliner " + md.get("version", "") + "</h3><p>" +
            tr("События на маршрутах и пикетаж для QGIS") + "</p>" + help_footer())
    box = QMessageBox(parent)
    box.setWindowTitle(tr("О модуле"))
    box.setTextFormat(1)  # Qt.RichText
    box.setText(text)
    box.exec()
