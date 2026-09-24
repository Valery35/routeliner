# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Окно «О модуле»: версия, ссылки, история изменений, руководство, журнал.

Версия и история читаются из metadata.txt. Отдельный файл истории не
заводится, иначе появится расхождение между двумя списками.

Qt импортируется внутри функций: read_metadata и manual_path проверяются
без QGIS.
"""

import os

_HERE = os.path.dirname(__file__)
SITE = "https://www.informpp.ru"
ORDER_URL = "https://www.informpp.ru/главная-страница/предприятиям"


def read_metadata():
    import configparser
    cp = configparser.ConfigParser(interpolation=None)
    with open(os.path.join(_HERE, "metadata.txt"), encoding="utf-8") as f:
        cp.read_file(f)
    return dict(cp["general"])


def changelog_lines():
    """История изменений из metadata.txt, по строке на версию."""
    text = read_metadata().get("changelog", "")
    return [ln.strip() for ln in text.replace("\\n", "\n").splitlines() if ln.strip()]


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


def _open_file(path):
    from qgis.PyQt.QtCore import QUrl
    from qgis.PyQt.QtGui import QDesktopServices
    return QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def open_manual(parent=None):
    from qgis.PyQt.QtWidgets import QMessageBox
    from .i18n import tr
    from . import trace
    path = manual_path()
    if path:
        trace.step("открыто руководство " + os.path.basename(path))
        _open_file(path)
    else:
        trace.fail("руководство не найдено")
        QMessageBox.warning(parent, "Routeliner", tr("Руководство не найдено."))


def open_log(parent=None):
    """Открыть журнал системным редактором."""
    from qgis.PyQt.QtWidgets import QMessageBox
    from .i18n import tr
    from . import trace
    path = trace.path()
    if path and os.path.isfile(path):
        _open_file(path)
    else:
        QMessageBox.information(parent, "Routeliner", tr("Журнал ещё не заведён."))


def open_log_folder(parent=None):
    from . import trace
    path = trace.path()
    if path:
        _open_file(os.path.dirname(path))


def _close_box(dlg):
    from qgis.PyQt.QtWidgets import QDialogButtonBox
    box = QDialogButtonBox(getattr(getattr(QDialogButtonBox, "StandardButton", QDialogButtonBox),
                                   "Close"), dlg)
    box.rejected.connect(dlg.reject)
    return box


def show_changelog(parent=None):
    from qgis.PyQt.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout
    from .i18n import tr
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("История изменений"))
    dlg.resize(720, 520)
    lay = QVBoxLayout(dlg)
    txt = QPlainTextEdit(dlg)
    txt.setReadOnly(True)
    txt.setPlainText("\n\n".join(changelog_lines()))
    lay.addWidget(txt)
    lay.addWidget(_close_box(dlg))
    dlg.exec()


def show_about(parent=None):
    """Значок, версия, назначение, ссылки и кнопки: история изменений,
    руководство, журнал. Внизу последние строки журнала, чтобы ошибку
    было видно сразу, без поиска файла."""
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtGui import QIcon, QTextCursor
    from qgis.PyQt.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                                     QPushButton, QVBoxLayout)
    from .i18n import tr
    from .resources import icon_path
    from . import trace
    md = read_metadata()
    ver = md.get("version", "?")
    home = md.get("homepage", "")
    tracker = md.get("tracker", "")

    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("О модуле"))
    dlg.resize(640, 520)
    lay = QVBoxLayout(dlg)

    head = QHBoxLayout()
    icon = QLabel(dlg)
    icon.setPixmap(QIcon(icon_path()).pixmap(64, 64))
    head.addWidget(icon)
    head.addWidget(QLabel(
        "<b style='font-size:14pt'>Routeliner</b><br>" + tr("Версия {v}").format(v=ver) +
        "<br>" + tr("События на маршрутах и пикетаж для QGIS") +
        "<br>© 2026 " + tr("ООО «Информ++»") + ", GNU GPL 2+", dlg), 1)
    lay.addLayout(head)

    links = QLabel(
        f'<a href="{SITE}">www.informpp.ru</a> · <a href="{home}">{tr("Исходный код")}</a> · '
        f'<a href="{tracker}">{tr("Сообщить об ошибке")}</a><br>' +
        tr("Routeliner развивается на задачах реальных предприятий. Если вашему производству "
           "не хватает функции, напишите нам") + f': <a href="{ORDER_URL}">{tr("страница для предприятий")}</a>',
        dlg)
    links.setWordWrap(True)
    links.setOpenExternalLinks(True)
    links.setTextInteractionFlags(getattr(getattr(Qt, "TextInteractionFlag", Qt),
                                          "TextBrowserInteraction"))
    lay.addWidget(links)

    row = QHBoxLayout()
    for text, slot in ((tr("История изменений"), lambda: show_changelog(dlg)),
                       (tr("Руководство (PDF)"), lambda: open_manual(dlg)),
                       (tr("Журнал"), lambda: open_log(dlg)),
                       (tr("Папка журнала"), lambda: open_log_folder(dlg))):
        b = QPushButton(text, dlg)
        b.clicked.connect(slot)
        row.addWidget(b)
    lay.addLayout(row)

    where = trace.path() or tr("не заведён")
    lay.addWidget(QLabel(tr("Журнал: {p}").format(p=where), dlg))
    log = QPlainTextEdit(dlg)
    log.setReadOnly(True)
    log.setPlainText("\n".join(trace.tail(60)))
    log.moveCursor(getattr(getattr(QTextCursor, "MoveOperation", QTextCursor), "End"))
    lay.addWidget(log, 1)
    lay.addWidget(_close_box(dlg))
    dlg.exec()
