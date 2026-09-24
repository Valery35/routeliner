"""5.01 Таблица профиля и 5.02 Чертёж профиля."""
from __future__ import annotations

import math
import re

import numpy as np
from qgis.core import (Qgis, QgsCoordinateTransform, QgsExpression, QgsExpressionContext,
                       QgsExpressionContextUtils, QgsFeature, QgsFeatureRequest, QgsFeatureSink,
                       QgsGeometry, QgsLineString, QgsPoint, QgsPointXY,
                       QgsProcessingException, QgsProcessingLayerPostProcessorInterface,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField, QgsProcessingParameterMatrix,
                       QgsProcessingParameterMultipleLayers, QgsProcessingParameterNumber,
                       QgsProcessingParameterPoint, QgsProcessingParameterString,
                       QgsProperty)

from ..core.profile import ROW_TYPES, ProfileDrawer, ProfilePoint, Row, collect_points
from ..i18n import tr
from ..layers.rasters import sample
from ..layers.tables import _key
from .common import (DBL, FIELD_ANY, FIELD_NUM, SRC_ANY, SRC_POINT, T_DBL, T_INT, T_STR,
                     RoutelinerAlgorithm, fields_of, fld, rdeg, rm)

FAST = QgsFeatureSink.Flag.FastInsert
VERTEX_MODES = [("significant", "только с поворотом или изломом уклона"),
                ("all", "все вершины"), ("none", "без вершин")]


def compact_station(text: str) -> str:
    """Подпись пикета для сетки профиля: без лишних нулей после точки
    (ПК 6+20.00 -> ПК 6+20, ПК 6+79.30 -> ПК 6+79.3)."""
    def cut(mo):
        frac = mo.group(2).rstrip("0")
        return mo.group(1) + ("." + frac if frac else "")
    return re.sub(r"(\d+)\.(\d+)", cut, text)


def _field_name(name: str, used: set) -> str:
    base = "z_" + (re.sub(r"\W+", "_", name.strip().lower()).strip("_") or "raster")
    base = base[:28]
    out, k = base, 1
    while out in used:
        k += 1
        out = f"{base}_{k}"
    used.add(out)
    return out


# ============================================================ 5.01 таблица профиля
class ProfileTable(RoutelinerAlgorithm):
    GROUP = "profile"
    NUMBER = "5.01"
    TITLE = "Таблица профиля"
    HELP = (
        "Собирает точки продольного профиля по каждому маршруту и снимает в них значения "
        "растров. Точки ставятся в начале и конце маршрута, на пикетажных уравнениях, на "
        "целых пикетах, на вершинах оси и с постоянным шагом. Точки из слоя событий "
        "(переходы, колодцы, скважины) ставятся по проекции на ось, если лежат в коридоре "
        "от оси.\n\n"
        "Значения растров интерполируются билинейно по центрам ячеек. Растр может быть в "
        "любой системе координат, точки пересчитываются.\n\n"
        "Поля результата: route_id (ID маршрута), n (номер точки), kind (start, end, "
        "equation, event, picket, vertex, step), m (мера по оси, м), station (пикетаж, м), "
        "station_ahead (пикетаж вперёд, только у уравнения), pk (пикет в выбранной "
        "записи), section (номер участка пикетажа), x и y (координаты на оси), z_axis "
        "(отметка оси по Z маршрута, пусто, если у маршрута нет Z или все Z нулевые), turn (угол поворота трассы в вершине, градусы, плюс "
        "влево), label (подпись события) и по одному полю z_имя на каждый растр.")

    def name(self):
        return "profile_table"

    def initAlgorithm(self, config=None):
        self.add_route_params()
        self.addParameter(QgsProcessingParameterString(
            "ROUTE_LIST", tr("Маршруты через запятую (пусто - все)"), optional=True))
        self.add_chainage_params()
        self.addParameter(QgsProcessingParameterMultipleLayers(
            "RASTERS", tr("Растры (рельеф, проектная поверхность, пласт)"),
            Qgis.ProcessingSourceType.Raster, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "BAND", tr("Номер канала растров"), Qgis.ProcessingNumberParameterType.Integer, 1,
            minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            "PICKET_STEP", tr("Точки на целых пикетах через, м (0 - нет)"), DBL, 100.0, minValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "STEP", tr("Точки с постоянным шагом, м (0 - нет)"), DBL, 0.0, minValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            "VERTICES", tr("Вершины оси"), [tr(d) for _, d in VERTEX_MODES], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "POIS", tr("События на профиль: точки (необязательно)"), [SRC_POINT], optional=True))
        self.addParameter(QgsProcessingParameterField(
            "POI_LABEL", tr("События: поле подписи"), parentLayerParameterName="POIS",
            type=FIELD_ANY, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "CORRIDOR", tr("События: коридор от оси, м"), DBL, 10.0, minValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("Таблица профиля"), Qgis.ProcessingSourceType.VectorPoint))

    def processAlgorithm(self, parameters, context, feedback):
        src, routes, _ = self.routes(parameters, context, feedback)
        loc, _ = self.locator(parameters, context, feedback, routes)
        wanted = [s.strip() for s in (self.parameterAsString(parameters, "ROUTE_LIST", context)
                                      or "").split(",") if s.strip()]
        if wanted:
            keys = {str(k): k for k in routes}
            missing = [w for w in wanted if w not in keys]
            for w in missing:
                feedback.reportError(tr("маршрут «{rid}» не найден").format(rid=w), False)
            routes = {keys[w]: routes[keys[w]] for w in wanted if w in keys}
        rasters = self.parameterAsLayerList(parameters, "RASTERS", context) or []
        band = self.parameterAsInt(parameters, "BAND", context)
        used = set()
        rfields = [_field_name(r.name(), used) for r in rasters]
        mode = VERTEX_MODES[self.parameterAsEnum(parameters, "VERTICES", context)][0]

        events = {rid: [] for rid in routes}
        pois = self.parameterAsSource(parameters, "POIS", context)
        if pois is not None:
            lab = self.parameterAsString(parameters, "POI_LABEL", context) or None
            corridor = self.parameterAsDouble(parameters, "CORRIDOR", context)
            xform = QgsCoordinateTransform(pois.sourceCrs(), src.sourceCrs(), context.transformContext())
            for f in pois.getFeatures():
                if not f.hasGeometry():
                    continue
                p = xform.transform(f.geometry().asPoint())
                best = None
                for rid, r in routes.items():
                    pr = r.locate(p.x(), p.y())
                    if hasattr(pr, "m") and (best is None or abs(pr.offset) < abs(best[1].offset)):
                        best = (rid, pr)
                if best is not None and abs(best[1].offset) <= corridor:
                    text = "" if lab is None or f[lab] is None else str(f[lab])
                    events[best[0]].append((best[1].m, text))

        fields = fields_of(fld("route_id", T_STR), fld("n", T_INT), fld("kind", T_STR),
                           fld("m", T_DBL), fld("station", T_DBL), fld("station_ahead", T_DBL),
                           fld("pk", T_STR), fld("section", T_INT), fld("x", T_DBL),
                           fld("y", T_DBL), fld("z_axis", T_DBL), fld("turn", T_DBL),
                           fld("label", T_STR), *[fld(n, T_DBL) for n in rfields])
        sink, dest = self.parameterAsSink(parameters, "OUTPUT", context, fields,
                                          Qgis.WkbType.Point, src.sourceCrs())
        fmt = loc.parser.format
        total = 0
        for rid, r in routes.items():
            if feedback.isCanceled():
                break
            pts = collect_points(r, loc.system_for(rid),
                                 self.parameterAsDouble(parameters, "PICKET_STEP", context),
                                 self.parameterAsDouble(parameters, "STEP", context),
                                 mode, events=events.get(rid, ()))
            ms = [p.m for p in pts]
            xyz = r.points_at(ms)
            zs = np.asarray(xyz["z"], dtype=float)
            if not np.any(np.nan_to_num(zs) != 0):
                zs = np.full(len(ms), np.nan)      # Z нет или все нули: отметки оси нет
            values = [sample(ras, xyz["x"], xyz["y"], src.sourceCrs(), context.transformContext(), band)
                      for ras in rasters]
            for i, p in enumerate(pts):
                pk = fmt(p.station) if p.kind != "equation" else \
                    f"{fmt(p.station)} = {fmt(p.station_ahead)}"
                f = QgsFeature(fields)
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(xyz["x"][i], xyz["y"][i])))
                z = float(zs[i])
                f.setAttributes([str(rid), i + 1, p.kind, rm(p.m), rm(p.station),
                                 rm(p.station_ahead), pk, p.section, rm(xyz["x"][i]),
                                 rm(xyz["y"][i]), rm(z), rdeg(p.turn) if p.turn else None,
                                 p.label or None, *[rm(v[i]) for v in values]])
                sink.addFeature(f, FAST)
            total += len(pts)
        feedback.pushInfo(tr("Итого: точек профиля {n}, растров {r}").format(n=total, r=len(rasters)))
        return {"OUTPUT": dest}


# ============================================================ 5.02 чертёж профиля
TEMPLATE_PIPE = [
    ("Отметка земли проектная, м", "value", "{design}", "2", "15", "1"),
    ("Отметка земли фактическая, м", "value", "{ground}", "2", "15", "1"),
    ("Отметка верха трубы, м", "value", "{pipe}", "2", "15", "1"),
    ("Отметка дна траншеи, м", "value", "{pipe} - {d} - {base}", "2", "15", "1"),
    ("Расстояние земля - труба, м", "value", "{ground} - {pipe}", "2", "10", "0"),
    ("Глубина траншеи, м", "value", "{ground} - ({pipe} - {d} - {base})", "2", "10", "0"),
    ("Обозначение трубы и тип изоляции", "text", "pipe", "", "15", "0"),
    ("Основание", "text", "base", "", "10", "0"),
    ("Уклон, ‰ / длина, м", "grade", "{pipe}", "1", "15", "0"),
    ("Расстояние, м", "distance", "", "1", "10", "0"),
    ("Пикет", "station", "", "", "20", "0"),
    ("Развёрнутый план", "plan", "", "", "25", "0"),
]
MATRIX_HEADERS = ["Заголовок", "Тип", "Источник", "Знаков", "Высота, мм", "Линия (1/0)"]

_KEEP = []          # постпроцессоры живут до загрузки слоёв


def _prop(name):
    from qgis.core import QgsPalLayerSettings
    P = getattr(QgsPalLayerSettings, "Property", None)
    return getattr(P, name) if P is not None and hasattr(P, name) else getattr(QgsPalLayerSettings, name)


class _StyleLines(QgsProcessingLayerPostProcessorInterface):
    def postProcessLayer(self, layer, context, feedback):
        from qgis.core import QgsLineSymbol, QgsSingleSymbolRenderer, QgsSymbolLayer
        sym = QgsLineSymbol.createSimple({"color": "0,0,0", "width": "0.1"})
        sl = sym.symbolLayer(0)
        sl.setWidthUnit(Qgis.RenderUnit.MapUnits)
        sl.setDataDefinedProperty(QgsSymbolLayer.Property.StrokeColor if hasattr(QgsSymbolLayer, "Property")
                                  else QgsSymbolLayer.PropertyStrokeColor, QgsProperty.fromField("color"))
        sl.setDataDefinedProperty(QgsSymbolLayer.Property.StrokeWidth if hasattr(QgsSymbolLayer, "Property")
                                  else QgsSymbolLayer.PropertyStrokeWidth, QgsProperty.fromField("width"))
        layer.setRenderer(QgsSingleSymbolRenderer(sym))
        layer.triggerRepaint()


class _StyleTexts(QgsProcessingLayerPostProcessorInterface):
    def postProcessLayer(self, layer, context, feedback):
        from qgis.core import (QgsMarkerSymbol, QgsPalLayerSettings, QgsSingleSymbolRenderer,
                               QgsSymbolLayer, QgsTextFormat, QgsVectorLayerSimpleLabeling)
        from qgis.PyQt.QtGui import QColor
        # знак рисуется только у точек плана, остальные объекты несут подписи
        mk = QgsMarkerSymbol.createSimple({"name": "circle", "color": "0,0,0", "size": "1.2"})
        mk.setSizeUnit(Qgis.RenderUnit.MapUnits)
        prop = QgsSymbolLayer.Property.Size if hasattr(QgsSymbolLayer, "Property") else QgsSymbolLayer.PropertySize
        mk.symbolLayer(0).setDataDefinedProperty(
            prop, QgsProperty.fromExpression("CASE WHEN \"kind\" = 'plan_point' THEN 1.2 ELSE 0 END"))
        layer.setRenderer(QgsSingleSymbolRenderer(mk))

        s = QgsPalLayerSettings()
        s.fieldName = "text"
        s.placement = Qgis.LabelPlacement.OverPoint
        fmt = QgsTextFormat()
        fmt.setSize(2.5)
        fmt.setSizeUnit(Qgis.RenderUnit.MapUnits)
        fmt.setColor(QColor(0, 0, 0))
        s.setFormat(fmt)
        pc = s.dataDefinedProperties()
        pc.setProperty(_prop("Size"), QgsProperty.fromField("size"))
        pc.setProperty(_prop("LabelRotation"), QgsProperty.fromField("rot"))
        pc.setProperty(_prop("PositionX"), QgsProperty.fromExpression("$x"))
        pc.setProperty(_prop("PositionY"), QgsProperty.fromExpression("$y"))
        pc.setProperty(_prop("Hali"), QgsProperty.fromField("halign"))
        pc.setProperty(_prop("Vali"), QgsProperty.fromField("valign"))
        s.setDataDefinedProperties(pc)
        try:
            s.placementSettings().setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapAtNoCost)
            s.obstacleSettings().setIsObstacle(False)
        except AttributeError:
            pass
        layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()


class ProfileDrawing(RoutelinerAlgorithm):
    GROUP = "profile"
    NUMBER = "5.02"
    TITLE = "Чертёж профиля"
    HELP = (
        "Строит чертёж продольного профиля одного маршрута по таблице 5.01: линии "
        "поверхностей над сеткой, сетку профиля со строками, шкалу отметок и развёрнутый "
        "план. Чертёж ставится в той же системе координат, что и таблица, в миллиметрах "
        "бумаги: одна единица карты равна миллиметру. В компоновке QGIS профиль печатается "
        "в натуральную величину при масштабе карты 1:1000.\n\n"
        "Строки сетки задаются таблицей. Тип строки: value (число по выражению), text "
        "(подписи участков из поля слоя участков), grade (уклон и длина по выражению), "
        "distance (расстояния между точками), station (пикеты), plan (развёрнутый план). "
        "В выражениях можно писать поля таблицы профиля и подстановки {ground}, {design}, "
        "{pipe}, {d}, {base}, которые заменяются полями и числами из параметров. Строка, "
        "у которой нет данных, в сетку не выводится.\n\n"
        "Подписи точек прореживаются: если точки на бумаге ближе заданного промежутка, "
        "подпись остаётся у точки с большим приоритетом (начало и конец, уравнение, "
        "событие, пикет, вершина, шаг).\n\n"
        "Поля слоя линий: kind (вид линии), row (строка), color, width (толщина, мм). Поля "
        "слоя подписей: text, kind, rot (поворот, градусы), size (высота, мм), halign, "
        "valign.")

    def name(self):
        return "profile_drawing"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            "TABLE", tr("Таблица профиля (результат 5.01)"), [SRC_ANY]))
        self.addParameter(QgsProcessingParameterString(
            "ROUTE", tr("Маршрут (пусто - первый в таблице)"), optional=True))
        for name, desc in (("GROUND", "Поле отметки земли {ground}"),
                           ("DESIGN", "Поле проектной отметки {design}"),
                           ("PIPE", "Поле отметки трубы или оси {pipe} (пусто - z_axis)")):
            self.addParameter(QgsProcessingParameterField(
                name, tr(desc), parentLayerParameterName="TABLE", type=FIELD_NUM, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "D", tr("Наружный диаметр трубы {d}, м"), DBL, 0.16, minValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "BASE", tr("Толщина основания {base}, м"), DBL, 0.3, minValue=0))
        default = [tr(c) if i == 0 else c for row in TEMPLATE_PIPE for i, c in enumerate(row)]
        self.addParameter(QgsProcessingParameterMatrix(
            "ROWS", tr("Строки сетки профиля"), numberRows=len(TEMPLATE_PIPE),
            hasFixedNumberRows=False, headers=[tr(h) for h in MATRIX_HEADERS],
            defaultValue=default))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "SECTIONS", tr("Участки для текстовых строк (необязательно)"), [SRC_ANY], optional=True))
        for name, desc, dflt in (("SEC_ROUTE", "Участки: поле ID маршрута", None),
                                 ("SEC_FROM", "Участки: поле меры начала", "rl_m_from"),
                                 ("SEC_TO", "Участки: поле меры конца", "rl_m_to")):
            self.addParameter(QgsProcessingParameterField(
                name, tr(desc), defaultValue=dflt, parentLayerParameterName="SECTIONS",
                type=FIELD_ANY if name == "SEC_ROUTE" else FIELD_NUM, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "PLAN", tr("Точки для развёрнутого плана (результат 4.02, необязательно)"),
            [SRC_POINT], optional=True))
        self.addParameter(QgsProcessingParameterField(
            "PLAN_LABEL", tr("План: поле подписи"), parentLayerParameterName="PLAN",
            type=FIELD_ANY, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "H_SCALE", tr("Масштаб по горизонтали 1:"), DBL, 500.0, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            "V_SCALE", tr("Масштаб по вертикали 1:"), DBL, 100.0, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            "HORIZON", tr("Условный горизонт, м (пусто - автоматически)"), DBL, None, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "GRADE_TOL", tr("Допуск выделения уклонов, м"), DBL, 0.02, minValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            "MIN_GAP", tr("Наименьший промежуток между подписями, мм"), DBL, 3.0, minValue=0))
        self.addParameter(QgsProcessingParameterPoint(
            "ORIGIN", tr("Левый нижний угол профиля над сеткой (пусто - под маршрутом)"),
            optional=True))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "LINES", tr("Профиль, линии"), Qgis.ProcessingSourceType.VectorLine))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "TEXTS", tr("Профиль, подписи"), Qgis.ProcessingSourceType.VectorPoint))

    # ------------------------------------------------------------ чтение
    def _points(self, table, rid):
        feats = [f for f in table.getFeatures() if rid is None or str(f["route_id"]) == rid]
        if not feats:
            raise QgsProcessingException(tr("В таблице нет точек маршрута «{rid}»").format(rid=rid))
        rid = str(feats[0]["route_id"]) if rid is None else rid
        feats = [f for f in feats if str(f["route_id"]) == rid]
        feats.sort(key=lambda f: f["m"])

        def num(v, dflt=math.nan):
            return dflt if v is None or v == "" else float(v)

        pts = [ProfilePoint(m=float(f["m"]), kind=str(f["kind"] or "step"),
                            label=str(f["label"] or ""), turn=num(f["turn"], 0.0),
                            station=num(f["station"]), station_ahead=num(f["station_ahead"]),
                            section=int(f["section"] or 0)) for f in feats]
        return rid, feats, pts

    def processAlgorithm(self, parameters, context, feedback):
        table = self.parameterAsSource(parameters, "TABLE", context)
        if table is None:
            raise QgsProcessingException(tr("Не задана таблица профиля"))
        for need in ("route_id", "m", "kind", "pk"):
            if table.fields().lookupField(need) < 0:
                raise QgsProcessingException(
                    tr("В таблице нет поля «{f}», нужна таблица инструмента 5.01").format(f=need))
        rid, feats, pts = self._points(table, self.parameterAsString(parameters, "ROUTE", context) or None)

        subst = {"d": repr(self.parameterAsDouble(parameters, "D", context)),
                 "base": repr(self.parameterAsDouble(parameters, "BASE", context))}
        for key, par in (("ground", "GROUND"), ("design", "DESIGN"), ("pipe", "PIPE")):
            name = self.parameterAsString(parameters, par, context)
            if not name and key == "pipe" and table.fields().lookupField("z_axis") >= 0:
                name = "z_axis"
            subst[key] = QgsExpression.quotedColumnRef(name) if name else None

        ctx = QgsExpressionContext()
        ctx.appendScope(QgsExpressionContextUtils.globalScope())
        ctx.setFields(table.fields())

        def evaluate(text):
            missing = [k for k in re.findall(r"\{(\w+)\}", text) if subst.get(k) is None]
            if missing:
                return None, tr("не задано: {names}").format(names=", ".join(missing))
            expr_text = re.sub(r"\{(\w+)\}", lambda mo: subst[mo.group(1)], text)
            e = QgsExpression(expr_text)
            if e.hasParserError():
                return None, e.parserErrorString()
            e.prepare(ctx)
            out = np.full(len(feats), np.nan)
            for i, f in enumerate(feats):
                ctx.setFeature(f)
                v = e.evaluate(ctx)
                if e.hasEvalError():
                    return None, e.evalErrorString()
                try:
                    out[i] = float(v) if v is not None else np.nan
                except (TypeError, ValueError):
                    out[i] = np.nan
            return out, ""

        sections = self._sections(parameters, context, rid)
        grade_tol = self.parameterAsDouble(parameters, "GRADE_TOL", context)
        raw = self.parameterAsMatrix(parameters, "ROWS", context) or []
        rows = []
        for k in range(0, len(raw) - len(raw) % 6, 6):
            title, kind, source, dec, height, draw = [("" if v is None else str(v)).strip()
                                                      for v in raw[k:k + 6]]
            kind = kind.lower()
            if kind not in ROW_TYPES:
                feedback.reportError(tr("Строка «{t}»: неизвестный тип «{k}»").format(t=title, k=kind), False)
                continue
            try:
                decimals = int(float(dec)) if dec else (0 if kind in ("station", "text") else 2)
                h = float(height) if height else 15.0
            except ValueError:
                feedback.reportError(tr("Строка «{t}»: знаков и высота должны быть числами").format(t=title), False)
                continue
            row = Row(title, kind, h, decimals, draw in ("1", "да", "yes", "true"), tolerance=grade_tol)
            if kind in ("value", "grade"):
                vals, why = evaluate(source)
                if vals is None:
                    feedback.pushInfo(tr("Строка «{t}» пропущена: {why}").format(t=title, why=why))
                    continue
                row.values = vals
            elif kind == "text":
                row.segments = sections.get(source, [])
                if not row.segments:
                    feedback.pushInfo(tr("Строка «{t}» пропущена: нет участков с полем «{f}»").format(
                        t=title, f=source))
                    continue
            rows.append(row)

        plan = self._plan(parameters, context, rid)
        horizon = parameters.get("HORIZON")
        horizon = None if horizon in (None, "") else self.parameterAsDouble(parameters, "HORIZON", context)
        drawer = ProfileDrawer(pts, [compact_station(str(f["pk"] or "")) for f in feats],
                               self.parameterAsDouble(parameters, "H_SCALE", context),
                               self.parameterAsDouble(parameters, "V_SCALE", context),
                               horizon, self.parameterAsDouble(parameters, "MIN_GAP", context), plan)
        sheet = drawer.build(rows)

        ext = table.sourceExtent()
        top = max([y for c, *_ in sheet.lines for _, y in c] + [0.0])
        if parameters.get("ORIGIN"):
            o = self.parameterAsPoint(parameters, "ORIGIN", context, table.sourceCrs())
            ox, oy = o.x(), o.y()
        else:
            ox, oy = ext.xMinimum(), ext.yMinimum() - 100.0 - top

        lf = fields_of(fld("kind", T_STR), fld("row", T_STR), fld("color", T_STR), fld("width", T_DBL))
        lsink, ldest = self.parameterAsSink(parameters, "LINES", context, lf,
                                            Qgis.WkbType.LineString, table.sourceCrs())
        for coords, kind, row, color, width in sheet.lines:
            f = QgsFeature(lf)
            f.setGeometry(QgsGeometry(QgsLineString([QgsPoint(ox + x, oy + y) for x, y in coords])))
            f.setAttributes([kind, row, color, width])
            lsink.addFeature(f, FAST)
        tf = fields_of(fld("text", T_STR), fld("kind", T_STR), fld("rot", T_DBL), fld("size", T_DBL),
                       fld("halign", T_STR), fld("valign", T_STR))
        tsink, tdest = self.parameterAsSink(parameters, "TEXTS", context, tf,
                                            Qgis.WkbType.Point, table.sourceCrs())
        for x, y, text, rot, size, ha, va, kind in sheet.texts:
            f = QgsFeature(tf)
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(ox + x, oy + y)))
            f.setAttributes([text, kind, rot, size, ha, va])
            tsink.addFeature(f, FAST)
        for x, y, kind, _ in sheet.marks:
            f = QgsFeature(tf)
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(ox + x, oy + y)))
            f.setAttributes(["", kind, 0.0, 0.0, "Center", "Half"])
            tsink.addFeature(f, FAST)

        for dest, style in ((ldest, _StyleLines()), (tdest, _StyleTexts())):
            if context.willLoadLayerOnCompletion(dest):
                _KEEP.append(style)
                context.layerToLoadOnCompletionDetails(dest).setPostProcessor(style)
        feedback.pushInfo(tr("Профиль маршрута «{rid}»: строк {r}, ширина {w:.0f} мм, условный "
                             "горизонт {h:.2f}").format(rid=rid, r=len(rows), w=sheet.width, h=sheet.horizon))
        return {"LINES": ldest, "TEXTS": tdest, "WIDTH_MM": sheet.width, "HORIZON": sheet.horizon}

    def _sections(self, parameters, context, rid) -> dict:
        src = self.parameterAsSource(parameters, "SECTIONS", context)
        if src is None:
            return {}
        rf = self.parameterAsString(parameters, "SEC_ROUTE", context) or None
        f0 = self.parameterAsString(parameters, "SEC_FROM", context) or "rl_m_from"
        f1 = self.parameterAsString(parameters, "SEC_TO", context) or "rl_m_to"
        if src.fields().lookupField(f0) < 0 or src.fields().lookupField(f1) < 0:
            raise QgsProcessingException(tr("В слое участков нет полей меры «{a}» и «{b}»").format(a=f0, b=f1))
        out = {}
        names = [f.name() for f in src.fields()]
        for f in src.getFeatures():
            if rf and str(_key(f[rf])) != rid and str(f[rf]) != rid:
                continue
            try:
                m0, m1 = float(f[f0]), float(f[f1])
            except (TypeError, ValueError):
                continue
            for n in names:
                v = f[n]
                if v is not None and str(v) != "":
                    out.setdefault(n, []).append((m0, m1, str(v)))
        return out

    def _plan(self, parameters, context, rid) -> list:
        src = self.parameterAsSource(parameters, "PLAN", context)
        if src is None:
            return []
        names = [f.name() for f in src.fields()]
        if "rl_m" not in names or "rl_offset" not in names:
            raise QgsProcessingException(tr("В слое плана нужны поля rl_m и rl_offset (результат 4.02)"))
        lab = self.parameterAsString(parameters, "PLAN_LABEL", context) or None
        out = []
        for f in src.getFeatures(QgsFeatureRequest()):
            if "rl_route" in names and str(f["rl_route"]) != rid:
                continue
            if f["rl_m"] is None or f["rl_offset"] is None:
                continue
            out.append((float(f["rl_m"]), float(f["rl_offset"]),
                        "" if lab is None or f[lab] is None else str(f[lab])))
        return out


PROFILE_ALGORITHMS = [ProfileTable, ProfileDrawing]
