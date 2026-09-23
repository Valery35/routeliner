"""Оболочка модуля: провайдер Processing и пункты меню."""
from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .resources import icon_path

MENU = "&Routeliner"


class RoutelinerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []

    def initProcessing(self):
        from .processing.provider import RoutelinerProvider
        self.provider = RoutelinerProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        from .layers import binder
        binder.manager = binder.BindingManager(iface=self.iface)
        if binder.manager.project.fileName():
            binder.manager.restore()       # модуль включили при уже открытом проекте
        from .i18n import tr
        # тот же порядок и те же номера, что в панели «Инструменты анализа»
        items = [
            ("1.01", "Демонстрационный пример", "demo"),
            ("1.02", "Проверка маршрутов", "check_routes"),
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
        ]
        for item in items:
            if item is None:
                self._separator()
                continue
            num, title, alg = item
            a = QAction(QIcon(icon_path()), f"{num} {tr(title)}…", self.iface.mainWindow())
            a.triggered.connect(lambda _=False, alg=alg: self._open(alg))
            self.iface.addPluginToMenu(MENU, a)
            self.actions.append(a)
        from . import about
        for title, slot in (("Руководство (PDF)", about.open_manual),
                            ("О модуле", about.show_about)):
            a = QAction(tr(title), self.iface.mainWindow())
            a.triggered.connect(lambda _=False, slot=slot: slot(self.iface.mainWindow()))
            self.iface.addPluginToMenu(MENU, a)
            self.actions.append(a)

    def _separator(self):
        a = QAction(self.iface.mainWindow())
        a.setSeparator(True)
        self.iface.addPluginToMenu(MENU, a)
        self.actions.append(a)

    def _open(self, alg):
        from qgis import processing
        processing.execAlgorithmDialog(f"routeliner:{alg}", {})

    def unload(self):
        from .layers import binder
        if binder.manager is not None:
            binder.manager.unload()
            binder.manager = None
        for a in self.actions:
            self.iface.removePluginMenu(MENU, a)
        self.actions = []
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
