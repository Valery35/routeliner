"""Общие параметры и помощники алгоритмов Routeliner (QGIS 3.40 и 4.x)."""
from __future__ import annotations

from qgis.core import (Qgis, QgsFeature, QgsFeatureSink, QgsField, QgsFields,
                       QgsProcessingAlgorithm, QgsProcessingException,
                       QgsProcessingParameterBoolean, QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField, QgsProcessingParameterNumber,
                       QgsProcessingParameterString)
from qgis.PyQt.QtCore import QMetaType

from ..i18n import tr
from ..core.assembler import RouteAssembler
from ..core.errors import CoreError
from ..core.events import EventLocator
from ..core.stations import StationFormat, StationParser
from ..layers.route_source import build_routes
from ..layers.tables import read_ledger

T_STR, T_DBL, T_INT = QMetaType.Type.QString, QMetaType.Type.Double, QMetaType.Type.Int
SRC_LINE = Qgis.ProcessingSourceType.VectorLine
SRC_POINT = Qgis.ProcessingSourceType.VectorPoint
SRC_ANY = Qgis.ProcessingSourceType.Vector
DBL = Qgis.ProcessingNumberParameterType.Double
FIELD_ANY = Qgis.ProcessingFieldParameterDataType.Any
FIELD_NUM = Qgis.ProcessingFieldParameterDataType.Numeric

FORMATS = [
    (StationFormat.PK_PLUS, "ПК и плюс (ПК 15+35, 15+35,5, ПК -1+50, +35)"),
    (StationFormat.KM_PLUS, "километр и метры (км 1+535)"),
    (StationFormat.RAIL, "железнодорожная запись (км 12 ПК 3+45)"),
    (StationFormat.METERS, "метры числом (1535,5)"),
    (StationFormat.KM, "километры дробью (1,535)"),
]


def fld(name, t):
    return QgsField(name, t)


def fields_of(*items) -> QgsFields:
    out = QgsFields()
    for it in items:
        if isinstance(it, QgsFields):
            for f in it:
                out.append(f)
        else:
            out.append(it)
    return out


ERROR_FIELDS = [("rl_route", T_STR), ("rl_error", T_STR), ("rl_message", T_STR)]


# Группы и инструменты в панели «Инструменты анализа» идут по алфавиту,
# поэтому номер в начале имени задаёт порядок работы.
GROUPS = {
    "prep": "1. Подготовка",
    "events": "2. События по пикетам",
    "live": "3. Динамические слои",
    "chainage": "4. Пикетаж и привязка",
}

SITE = "https://www.informpp.ru"
ORDER_URL = "https://www.informpp.ru/главная-страница/предприятиям"
HOME_URL = "https://github.com/Valery35/routeliner"


def version() -> str:
    import configparser
    import os
    cp = configparser.ConfigParser(interpolation=None)
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "metadata.txt"),
                  encoding="utf-8") as f:
            cp.read_file(f)
        return cp["general"].get("version", "")
    except Exception:  # nosec
        return ""


def help_footer() -> str:
    """Подпись в конце справки каждого инструмента."""
    return (
        "<hr/><p>" + tr("Разработано при поддержке ООО «Информ++»") +
        f' (<a href="{SITE}">www.informpp.ru</a>).<br/>' +
        tr("Страница плагина") + f': <a href="{HOME_URL}">github.com/Valery35/routeliner</a><br/>'
        f"Routeliner v{version()}<br/>" +
        tr("Routeliner развивается на задачах реальных предприятий. Если вашему производству "
           "не хватает функции, напишите нам") + f': <a href="{ORDER_URL}">{ORDER_URL}</a></p>')


class RoutelinerAlgorithm(QgsProcessingAlgorithm):
    """Базовый класс: параметры маршрутов, пикетажа и ведомости."""

    GROUP = "events"
    NUMBER = ""
    TITLE = ""
    HELP = ""
    HELP_TAIL = ()

    def displayName(self):
        return f"{self.NUMBER} {tr(self.TITLE)}"

    def shortHelpString(self):
        text = "\n\n".join(tr(t) for t in (self.HELP, *self.HELP_TAIL))
        return "<p>" + text.replace("\n\n", "</p><p>") + "</p>" + help_footer()

    def group(self):
        return tr(GROUPS[self.GROUP])

    def groupId(self):
        return self.GROUP

    def createInstance(self):
        return type(self)()

    # ------------------------------------------------------------ параметры
    def add_route_params(self):
        self.addParameter(QgsProcessingParameterFeatureSource(
            "ROUTES", tr("Слой маршрутов (линии)"), [SRC_LINE]))
        self.addParameter(QgsProcessingParameterField(
            "ROUTE_ID", tr("Поле ID маршрута"), parentLayerParameterName="ROUTES", type=FIELD_ANY))
        p = QgsProcessingParameterNumber("SNAP", tr("Допуск стыковки частей, м"), DBL, 0.01, minValue=0)
        p.setFlags(p.flags() | Qgis.ProcessingParameterFlag.Advanced)
        self.addParameter(p)
        for name, desc in (("ALLOW_GAPS", "Разрешить разрывы (участок через разрыв выдаётся мультилинией)"),
                           ("USE_Z", "Длина по 3D (с учётом Z)"),
                           ("REVERSE", "Обратное направление маршрутов")):
            p = QgsProcessingParameterBoolean(name, tr(desc), False)
            p.setFlags(p.flags() | Qgis.ProcessingParameterFlag.Advanced)
            self.addParameter(p)

    def add_chainage_params(self, with_format=True):
        if with_format:
            self.addParameter(QgsProcessingParameterEnum(
                "FORMAT", tr("Запись пикета"), [tr(d) for _, d in FORMATS], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "PICKET", tr("Длина пикета, м"), DBL, 100.0, minValue=0.001))
        self.addParameter(QgsProcessingParameterNumber(
            "START", tr("Пикет начала маршрута (без ведомости), м"), DBL, 0.0))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "LEDGER", tr("Пикетажная ведомость (необязательно)"), [SRC_ANY], optional=True))
        for name, desc, opt, t in (
                ("LG_ROUTE", "Ведомость: поле ID маршрута", True, FIELD_ANY),
                ("LG_STATION", "Ведомость: поле пикета", True, FIELD_ANY),
                ("LG_MEASURE", "Ведомость: поле метража (мера по оси)", True, FIELD_NUM),
                ("LG_AHEAD", "Ведомость: поле пикета вперёд (уравнение)", True, FIELD_ANY),
                ("LG_SYSTEM", "Ведомость: поле системы пикетажа", True, FIELD_ANY)):
            self.addParameter(QgsProcessingParameterField(
                name, tr(desc), parentLayerParameterName="LEDGER", type=t, optional=opt))
        self.addParameter(QgsProcessingParameterString(
            "SYSTEM", tr("Система пикетажа (значение поля системы)"), optional=True))

    def add_error_sink(self):
        self.addParameter(QgsProcessingParameterFeatureSink(
            "ERRORS", tr("Ошибки"), Qgis.ProcessingSourceType.Vector, optional=True))

    # ------------------------------------------------------------ чтение
    def parser(self, parameters, context) -> StationParser:
        idx = self.parameterAsEnum(parameters, "FORMAT", context) \
            if self.parameterDefinition("FORMAT") is not None else 0
        return StationParser(FORMATS[idx][0],
                             self.parameterAsDouble(parameters, "PICKET", context))

    def routes(self, parameters, context, feedback):
        src = self.parameterAsSource(parameters, "ROUTES", context)
        if src is None:
            raise QgsProcessingException(tr("Не задан слой маршрутов"))
        asm = RouteAssembler(
            snap_tolerance=self.parameterAsDouble(parameters, "SNAP", context),
            allow_gaps=self.parameterAsBoolean(parameters, "ALLOW_GAPS", context),
            use_z=self.parameterAsBoolean(parameters, "USE_Z", context),
            reverse=self.parameterAsBoolean(parameters, "REVERSE", context))
        routes, errors = build_routes(
            src, self.parameterAsString(parameters, "ROUTE_ID", context), asm,
            crs=src.sourceCrs())
        feedback.pushInfo(tr("Маршрутов собрано {a}, не собрано {b}").format(a=len(routes), b=len(errors)))
        for e in errors:
            feedback.reportError(tr("Маршрут {rid}: {msg}").format(rid=e.route_id, msg=e.message), False)
        return src, routes, errors

    def locator(self, parameters, context, feedback, routes) -> tuple[EventLocator, list]:
        parser = self.parser(parameters, context)
        systems, errors = {}, []
        ledger = self.parameterAsSource(parameters, "LEDGER", context)
        if ledger is not None:
            f = lambda n: self.parameterAsString(parameters, n, context) or None
            if not (f("LG_ROUTE") and f("LG_STATION")):
                raise QgsProcessingException(tr("Для ведомости нужны поля ID маршрута и пикета"))
            systems, errors = read_ledger(
                ledger, parser, f("LG_ROUTE"), f("LG_STATION"), f("LG_MEASURE"),
                f("LG_AHEAD"), f("LG_SYSTEM"), f("SYSTEM"),
                {k: r.length for k, r in routes.items()})
            systems = {k: v for k, v in systems.items() if k in routes}
            feedback.pushInfo(tr("Ведомость: систем пикетажа {a}, ошибок {b}").format(a=len(systems), b=len(errors)))
            for e in errors:
                feedback.reportError(tr("Ведомость, маршрут {rid}: {msg}").format(
                    rid=e.route_id, msg=e.message), False)
        loc = EventLocator(routes, parser, systems,
                           self.parameterAsDouble(parameters, "START", context))
        return loc, errors

    # ------------------------------------------------------------ ошибки
    def write_errors(self, parameters, context, base_fields: QgsFields, items):
        """items: (исходный объект или None, CoreError)."""
        fields = fields_of(base_fields, *[fld(n, t) for n, t in ERROR_FIELDS])
        sink, dest = self.parameterAsSink(parameters, "ERRORS", context, fields,
                                          Qgis.WkbType.NoGeometry)
        if sink is None:
            return None
        for src_feat, err in items:
            f = QgsFeature(fields)
            attrs = list(src_feat.attributes()) if src_feat is not None else \
                [None] * base_fields.count()
            f.setAttributes(attrs + [None if err.route_id is None else str(err.route_id),
                                     err.code.value, err.message])
            sink.addFeature(f, QgsFeatureSink.Flag.FastInsert)
        return dest
