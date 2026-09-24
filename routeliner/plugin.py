# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Оболочка модуля: провайдер Processing, меню, панель инструментов, журнал.

Панель Routeliner несёт три кнопки: список инструментов с теми же номерами,
что в меню и в панели «Инструменты анализа», окно «О модуле» и руководство.
Всё, что делает оболочка, пишется в журнал (trace.py), и сбой любой кнопки
не роняет остальные.
"""
from qgis.core import QgsApplication, QgsMessageLog

from .resources import icon_path

MENU = "&Routeliner"

# тот же порядок и те же номера, что в панели «Инструменты анализа»
TOOLS = [
    ("1.01", "Демонстрационный пример", "demo"),
    ("1.02", "Проверка маршрутов", "check_routes"),
    ("1.03", "Калибровка маршрутов", "calibrate_routes"),
    None,
    ("2.01", "Точечные события", "point_events"),
    ("2.02", "Участки (линейные события)", "line_events"),
    None,
    ("3.01", "Динамический слой точечных событий", "live_point_events"),
    ("3.02", "Динамический слой участков", "live_line_events"),
    None,
    ("4.01", "Пикетная разбивка", "pickets"),
    ("4.02", "Привязка точек к маршрутам", "locate_points"),
    None,
    ("5.01", "Таблица профиля", "profile_table"),
    ("5.02", "Чертёж профиля", "profile_drawing"),
]


def _log(msg):
    try:
        QgsMessageLog.logMessage(msg, "Routeliner")
    except Exception:  # nosec
        pass


def _qaction():
    try:
        from qgis.PyQt.QtGui import QAction        # Qt6 (QGIS 4)
    except ImportError:
        from qgis.PyQt.QtWidgets import QAction    # Qt5 (QGIS 3)
    return QAction


class RoutelinerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []
        self.toolbar = None
        self.tools_menu = None

    def initProcessing(self):
        from . import trace
        try:
            from .processing.provider import RoutelinerProvider
            self.provider = RoutelinerProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)
            trace.step("провайдер Processing зарегистрирован")
        except Exception as e:
            self.provider = None
            trace.fail("провайдер Processing не зарегистрирован", e)
            _log("Провайдер Processing не зарегистрирован: %s" % e)

    def initGui(self):
        # журнал заводится первым, чтобы в него попало всё, что будет дальше
        from . import trace
        trace.setup()
        try:
            from .about import read_metadata
            from qgis.core import Qgis
            trace.step("Routeliner %s, QGIS %s, язык %s: загрузка" % (
                read_metadata().get("version", "?"), Qgis.version(), _lang()))
        except Exception as e:  # nosec
            trace.fail("не прочитана версия", e)
        self.initProcessing()
        try:
            from .layers import binder
            binder.manager = binder.BindingManager(iface=self.iface)
            if binder.manager.project.fileName():
                binder.manager.restore()       # модуль включили при уже открытом проекте
        except Exception as e:
            trace.fail("динамические слои не подключены", e)
        try:
            self._build_gui()
        except Exception as e:
            trace.fail("меню и панель модуля не созданы", e)
            _log("Интерфейс Routeliner не создан: %s" % e)

    def _build_gui(self):
        from qgis.PyQt.QtGui import QIcon
        from qgis.PyQt.QtWidgets import QMenu, QToolButton
        from .i18n import tr
        QAction = _qaction()
        win = self.iface.mainWindow()
        icon = QIcon(icon_path())
        self.toolbar = self.iface.addToolBar("Routeliner")
        self.toolbar.setObjectName("RoutelinerToolbar")
        self.toolbar.setToolTip("Routeliner")

        # меню модуля и выпадающий список инструментов на панели
        self.tools_menu = QMenu(tr("Инструменты Routeliner"), win)
        for item in TOOLS:
            if item is None:
                self._separator()
                self.tools_menu.addSeparator()
                continue
            num, title, alg = item
            a = QAction(icon, f"{num} {tr(title)}…", win)
            a.triggered.connect(lambda _=False, alg=alg: self._open(alg))
            self.iface.addPluginToMenu(MENU, a)
            self.actions.append(a)
            self.tools_menu.addAction(a)
        self._separator()

        btn = QToolButton(win)
        btn.setIcon(icon)
        btn.setToolTip(tr("Инструменты Routeliner"))
        btn.setMenu(self.tools_menu)
        btn.setPopupMode(getattr(getattr(QToolButton, "ToolButtonPopupMode", QToolButton),
                                 "InstantPopup"))
        self.toolbar.addWidget(btn)

        a_about = QAction(QIcon(icon_path("icon_about.svg")), tr("О модуле…"), win)
        a_about.setToolTip(tr("Версия, ссылки, история изменений, руководство и журнал"))
        a_about.triggered.connect(self._about)
        a_manual = QAction(tr("Руководство (PDF)"), win)
        a_manual.triggered.connect(self._manual)
        a_log = QAction(tr("Журнал работы"), win)
        a_log.triggered.connect(self._journal)
        for a, on_bar in ((a_manual, False), (a_log, False), (a_about, True)):
            self.iface.addPluginToMenu(MENU, a)
            self.actions.append(a)
            if on_bar:
                self.toolbar.addAction(a)

    def _separator(self):
        a = _qaction()(self.iface.mainWindow())
        a.setSeparator(True)
        self.iface.addPluginToMenu(MENU, a)
        self.actions.append(a)

    def _open(self, alg):
        from . import trace
        try:
            from qgis import processing
            trace.step("открыт инструмент " + alg)
            processing.execAlgorithmDialog(f"routeliner:{alg}", {})
        except Exception as e:
            trace.fail("инструмент %s не открылся" % alg, e)
            _log("Инструмент %s не открылся: %s" % (alg, e))

    def _about(self):
        self._safe("show_about")

    def _manual(self):
        self._safe("open_manual")

    def _journal(self):
        self._safe("open_log")

    def _safe(self, name):
        """Кнопка оболочки: сбой пишется в журнал и не роняет QGIS."""
        from . import trace
        try:
            from . import about
            trace.step("кнопка " + name)
            getattr(about, name)(self.iface.mainWindow())
        except Exception as e:
            trace.fail("сбой кнопки " + name, e)
            _log("Сбой кнопки %s: %s" % (name, e))

    def unload(self):
        from . import trace
        try:
            from .layers import binder
            if binder.manager is not None:
                binder.manager.unload()
                binder.manager = None
        except Exception as e:  # nosec
            trace.fail("динамические слои не отключены", e)
        for a in self.actions:
            try:
                self.iface.removePluginMenu(MENU, a)
            except Exception:  # nosec
                pass
        self.actions = []
        if self.toolbar is not None:
            try:
                self.toolbar.deleteLater()
            except Exception:  # nosec
                pass
            self.toolbar = None
        self.tools_menu = None
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        trace.step("модуль выгружен")


def _lang():
    try:
        from .i18n import language
        return language()
    except Exception:  # nosec
        return "?"
