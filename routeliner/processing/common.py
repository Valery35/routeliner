"""Общие параметры и помощники алгоритмов Routeliner (QGIS 3.40 и 4.x)."""
from __future__ import annotations

from qgis.core import (Qgis, QgsFeature, QgsFeatureSink, QgsField, QgsFields,
                       QgsProcessingAlgorithm, QgsProcessingException,
                       QgsProcessingLayerPostProcessorInterface, QgsVectorLayer,
                       QgsProcessingParameterBoolean, QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField, QgsProcessingParameterNumber,
                       QgsProcessingParameterString)
from qgis.PyQt.QtCore import QMetaType

from ..i18n import tr
from ..core.aliases import (ALIASES, PLAIN_ALIASES, alias_source,  # noqa: F401
                            all_alias_sources, is_raster_field, layer_is_ours,
                            split_gpkg_ref)
from ..core.assembler import RouteAssembler
from ..core.chainage import ChainageSystem
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

# Что пишется в M геометрии результата: ничего, мера по оси или пикетаж
OUT_M = ["без M", "мера по оси, м", "пикетаж, м"]

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


# Округление значений в полях результатов. Точность модуля - миллиметры
# (см. раздел «Точность» руководства), поэтому длины, меры, смещения,
# координаты и отметки пишутся до 0,001 м, углы до 0,01°.
DEC_M = 3
DEC_DEG = 2


def rm(v):
    """Метры до миллиметра, пустое остаётся пустым."""
    return None if v is None or v != v else round(float(v), DEC_M)


def rdeg(v):
    """Градусы до сотой, пустое остаётся пустым."""
    return None if v is None or v != v else round(float(v), DEC_DEG)


ERROR_FIELDS = [("rl_route", T_STR), ("rl_error", T_STR), ("rl_message", T_STR)]

# Псевдонимы полей лежат в core/aliases.py: словари и выбор псевдонима
# проверяются без QGIS. Здесь остаётся работа со слоем и с файлом.
_OURS = None


def _our_aliases():
    """Наши же псевдонимы на обоих языках, чтобы отличать свой от чужого."""
    global _OURS
    if _OURS is None:
        from ..translations import TRANSLATIONS
        src = all_alias_sources()
        _OURS = src | {TRANSLATIONS.get(v, v) for v in src}
    return _OURS


def apply_aliases(layer) -> None:
    """Ставит псевдонимы полям слоя на языке интерфейса.

    Чужой псевдоним не трогаем. Свой, записанный в файл при создании,
    заменяем: язык интерфейса важнее языка, на котором файл собрали.
    """
    if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
        return
    names = [f.name() for f in layer.fields()]
    own = layer_is_ours(names)
    ours = _our_aliases()
    for i, n in enumerate(names):
        cur = layer.attributeAlias(i)
        if cur and cur not in ours and not is_raster_field(n):
            continue
        src = alias_source(n, own)
        if src is None:
            continue
        text = tr(src).format(name=n[2:]) if is_raster_field(n) else tr(src)
        layer.setFieldAlias(i, text)


def _pick_layer(ds, path, layer_name):
    """Слой GeoPackage по имени, а без имени - по имени файла.

    Приёмник результата отдаёт один путь без имени слоя. QGIS называет
    такой слой по файлу, и это первое, что стоит проверить. Если файл
    несёт единственный слой, берём его.
    """
    import os
    if layer_name:
        return ds.GetLayerByName(layer_name)
    stem = os.path.splitext(os.path.basename(path))[0]
    lyr = ds.GetLayerByName(stem)
    if lyr is not None:
        return lyr
    return ds.GetLayer(0) if ds.GetLayerCount() == 1 else None


def bake_aliases(path, layer_name=None) -> int:
    """Пишет псевдонимы в сам GeoPackage. Возвращает число полей.

    Псевдоним, поставленный на слой, живёт в проекте. Демонстрационный
    пример и результаты генерации открывают файлом и без проекта, и там
    подписи снова становились латиницей. GDAL кладёт их в gpkg_data_columns,
    откуда QGIS читает их сам при любом открытии.

    Записывается язык, на котором файл собрали. Открытый в другой локали
    слой перекрывается псевдонимом языка интерфейса в apply_aliases.
    """
    from osgeo import gdal, ogr
    ds = gdal.OpenEx(path, gdal.OF_UPDATE | gdal.OF_VECTOR)
    if ds is None:
        return 0
    lyr = _pick_layer(ds, path, layer_name)
    if lyr is None:
        return 0
    defn = lyr.GetLayerDefn()
    names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    own = layer_is_ours(names)
    done = 0
    for i, n in enumerate(names):
        src = alias_source(n, own)
        if src is None:
            continue
        text = tr(src).format(name=n[2:]) if is_raster_field(n) else tr(src)
        old = defn.GetFieldDefn(i)
        if old.GetAlternativeName() == text:
            done += 1
            continue
        nd = ogr.FieldDefn(old.GetName(), old.GetType())
        nd.SetSubType(old.GetSubType())
        nd.SetAlternativeName(text)
        if lyr.AlterFieldDefn(i, nd, ogr.ALTER_ALTERNATIVE_NAME_FLAG) == 0:
            done += 1
    ds = None
    return done


def bake_refs(refs, feedback=None) -> None:
    """Псевдонимы в файл для тех результатов, что легли в GeoPackage.

    Ссылки приходят из двух мест. Слои, которые инструмент грузит
    в проект, стоят в контексте. Приёмники результата в контекст не
    попадают вовсе, когда инструмент запущен скриптом, поэтому базовый
    класс помнит их отдельно.
    """
    seen = set()
    for ref in refs:
        target = split_gpkg_ref(ref)
        if target is None or target in seen:
            continue
        seen.add(target)
        try:
            bake_aliases(*target)
        except Exception as e:      # запись подписей не вправе ронять инструмент
            if feedback is not None:
                feedback.pushDebugInfo(
                    tr("псевдонимы в файл не записаны: {why}").format(why=e))


def bake_loaded_layers(context, feedback=None) -> None:
    """Псевдонимы в файл для слоёв, которые грузятся в проект."""
    bake_refs(list(context.layersToLoadOnCompletion().keys()), feedback)


class AliasPostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Ставит псевдонимы полей после загрузки слоя, затем передаёт слой
    прежнему постпроцессору (оформление профиля)."""

    def __init__(self, inner=None):
        super().__init__()
        self.inner = inner

    def postProcessLayer(self, layer, context, feedback):
        if self.inner is not None:
            self.inner.postProcessLayer(layer, context, feedback)
        apply_aliases(layer)


_POST = []          # постпроцессоры должны жить до загрузки слоёв


def alias_loaded_layers(context) -> None:
    for ref in list(context.layersToLoadOnCompletion().keys()):
        det = context.layerToLoadOnCompletionDetails(ref)
        old = det.postProcessor()
        if isinstance(old, AliasPostProcessor):
            continue
        pp = AliasPostProcessor(old)
        _POST.append(pp)
        det.setPostProcessor(pp)


# Группы и инструменты в панели «Инструменты анализа» идут по алфавиту,
# поэтому номер в начале имени задаёт порядок работы.
GROUPS = {
    "prep": "1. Подготовка",
    "events": "2. События по пикетам",
    "live": "3. Динамические слои",
    "chainage": "4. Пикетаж и привязка",
    "profile": "5. Профили",
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


def help_html(text: str) -> str:
    """Абзацы через пустую строку, перечни строками с дефиса."""
    paras = text.split("\n\n")
    return "".join("<p>" + p.replace("\n", "<br/>") + "</p>" for p in paras)


def help_footer() -> str:
    """Подпись в конце справки каждого инструмента."""
    return (
        "<hr/><p>" + tr("Разработано при поддержке ООО «Информ++»") +
        f' (<a href="{SITE}">www.informpp.ru</a>).<br/>' +
        tr("Страница плагина") + f': <a href="{HOME_URL}">github.com/Valery35/routeliner</a><br/>'
        f"Routeliner v{version()}<br/>" +
        tr("Routeliner развивается на задачах реальных предприятий. Если вашему производству "
           "не хватает функции, напишите нам") + f': <a href="{ORDER_URL}">{ORDER_URL}</a></p>')


def _journaled(run):
    """Обёртка processAlgorithm: запуск, параметры, замечания, итог и сбой
    инструмента пишутся в журнал модуля (trace.py). Ошибка не глотается,
    Processing показывает её как прежде."""
    import functools
    import time

    @functools.wraps(run)
    def wrapper(self, parameters, context, feedback):
        from .. import trace
        title = f"{self.NUMBER} {self.name()}"
        trace.step(title + ": запуск")
        trace.data(title + ": " + _params_text(parameters))
        _journal_feedback(feedback, title)
        t0 = time.time()
        try:
            res = run(self, parameters, context, feedback)
        except Exception as e:
            trace.fail(title + ": сбой, " + str(e), e)
            raise
        trace.step(title + ": готово за %.1f с" % (time.time() - t0))
        return res
    return wrapper


def _params_text(parameters) -> str:
    out = []
    for k, v in sorted((parameters or {}).items()):
        v = getattr(v, "sink", v)
        out.append(f"{k}={v}")
    return "; ".join(out)[:2000]


def _journal_feedback(feedback, title):
    """Замечания инструмента (reportError) дублируются в журнал."""
    if feedback is None:
        return
    try:
        orig = feedback.reportError

        def report(msg, fatal=False):
            from .. import trace
            trace.write("ЗАМЕЧ", f"{title}: {msg}")
            return orig(msg, fatal)
        feedback.reportError = report
    except Exception:  # nosec - журнал не вправе мешать инструменту
        pass


class RoutelinerAlgorithm(QgsProcessingAlgorithm):
    """Базовый класс: параметры маршрутов, пикетажа и ведомости."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "processAlgorithm" in cls.__dict__:
            cls.processAlgorithm = _journaled(cls.__dict__["processAlgorithm"])

    GROUP = "events"
    NUMBER = ""
    TITLE = ""
    HELP = ""
    HELP_TAIL = ()

    def displayName(self):
        return f"{self.NUMBER} {tr(self.TITLE)}"

    def shortHelpString(self):
        text = "\n\n".join(tr(t) for t in (self.HELP, *self.HELP_TAIL))
        return help_html(text) + help_footer()

    def group(self):
        return tr(GROUPS[self.GROUP])

    def groupId(self):
        return self.GROUP

    def createInstance(self):
        return type(self)()

    def parameterAsSink(self, *args, **kwargs):
        """Помнит, куда лёг результат: туда же пишутся псевдонимы полей."""
        sink, dest = super().parameterAsSink(*args, **kwargs)
        if dest:
            self._dests = getattr(self, "_dests", [])
            self._dests.append(dest)
        return sink, dest

    def postProcessAlgorithm(self, context, feedback):
        alias_loaded_layers(context)
        bake_refs(list(context.layersToLoadOnCompletion().keys())
                  + getattr(self, "_dests", []), feedback)
        return {}

    # ------------------------------------------------------------ параметры
    def add_route_params(self):
        self.addParameter(QgsProcessingParameterFeatureSource(
            "ROUTES", tr("Слой маршрутов (линии)"), [SRC_LINE]))
        self.addParameter(QgsProcessingParameterField(
            "ROUTE_ID", tr("Поле ID маршрута"), defaultValue="route_id",
            parentLayerParameterName="ROUTES", type=FIELD_ANY))
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
        self.addParameter(QgsProcessingParameterBoolean(
            "USE_M", tr("Пикетаж из M-значений геометрии маршрута"), False))
        p = QgsProcessingParameterNumber(
            "M_FACTOR", tr("Метров в единице M (1000, если M в километрах)"), DBL, 1.0,
            minValue=1e-9)
        p.setFlags(p.flags() | Qgis.ProcessingParameterFlag.Advanced)
        self.addParameter(p)

    def add_out_m_param(self, default=0):
        self.addParameter(QgsProcessingParameterEnum(
            "OUT_M", tr("M-значения результата"), [tr(d) for d in OUT_M], defaultValue=default))

    def out_m(self, parameters, context) -> int:
        if self.parameterDefinition("OUT_M") is None:
            return 0
        return self.parameterAsEnum(parameters, "OUT_M", context)

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
            def f(n):
                return self.parameterAsString(parameters, n, context) or None

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
        m_sys, m_err = self.m_systems(parameters, context, feedback, routes, set(systems))
        systems.update(m_sys)
        errors = list(errors) + m_err
        loc = EventLocator(routes, parser, systems,
                           self.parameterAsDouble(parameters, "START", context))
        return loc, errors

    def m_systems(self, parameters, context, feedback, routes, skip=()):
        """Системы пикетажа из M-значений маршрутов, у которых нет ведомости.
        Маршрут без M остаётся с пикетажем по длине."""
        if self.parameterDefinition("USE_M") is None or \
                not self.parameterAsBoolean(parameters, "USE_M", context):
            return {}, []
        factor = self.parameterAsDouble(parameters, "M_FACTOR", context) or 1.0
        out, errors, plain = {}, [], 0
        for rid, r in routes.items():
            if rid in skip:
                continue
            if not r.has_m:
                plain += 1
                continue
            s = ChainageSystem.from_measures(tr("M геометрии"), r.vertex_measures(), r.length, factor)
            if isinstance(s, CoreError):
                errors.append(s.with_key(None, rid))
                feedback.reportError(tr("M маршрута {rid}: {msg}").format(rid=rid, msg=s.message), False)
            else:
                out[rid] = s
        feedback.pushInfo(tr("Пикетаж из M: маршрутов {a}, без M {b}, ошибок {c}").format(
            a=len(out), b=plain, c=len(errors)))
        return out, errors

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
