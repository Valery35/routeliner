from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from ..i18n import tr
from .alg_demo import DemoAlgorithm
from .algorithms import ALGORITHMS
from ..resources import icon_path


class RoutelinerProvider(QgsProcessingProvider):
    def id(self):
        return "routeliner"

    def name(self):
        return "Routeliner"

    def longName(self):
        return tr("Routeliner, события на маршрутах и пикетаж")

    def icon(self):
        return QIcon(icon_path())

    def loadAlgorithms(self):
        for cls in [DemoAlgorithm, *ALGORITHMS]:
            self.addAlgorithm(cls())
