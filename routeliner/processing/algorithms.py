"""Алгоритмы Processing Routeliner.

Имена, группы и справка задаются по-русски в атрибутах классов
(NUMBER, TITLE, HELP) и переводятся через i18n.tr на языке интерфейса.
"""
from __future__ import annotations

from qgis.core import (Qgis, QgsCoordinateTransform, QgsFeature, QgsFeatureSink,
                       QgsGeometry, QgsLineString, QgsMultiLineString, QgsPoint,
                       QgsPointXY, QgsProcessingException, QgsProcessingOutputString,
                       QgsProcessingParameterBoolean, QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource, QgsProcessingParameterField,
                       QgsProcessingParameterNumber, QgsProcessingParameterString)

from ..core.errors import CoreError
from ..i18n import tr
from ..layers.tables import _key, read_events
from .common import (DBL, FIELD_ANY, FIELD_NUM, SRC_ANY, SRC_POINT, T_DBL, T_INT,
                     T_STR, RoutelinerAlgorithm, fields_of, fld, rdeg, rm)

FAST = QgsFeatureSink.Flag.FastInsert


def _line_geometry(pieces) -> QgsGeometry:
    lines = []
    for c in pieces:
        if c.shape[1] > 2 and not any(v != v for v in c[:, 2]):
            lines.append(QgsLineString([QgsPoint(x, y, z) for x, y, z in c[:, :3]]))
        else:
            lines.append(QgsLineString([QgsPoint(x, y) for x, y in c[:, :2]]))
    if len(lines) == 1:
        return QgsGeometry(lines[0])
    mls = QgsMultiLineString()
    for ln in lines:
        mls.addGeometry(ln)
    return QgsGeometry(mls)


ERRORS_HELP = (
    "Таблица ошибок повторяет поля исходной записи и добавляет rl_route (маршрут), "
    "rl_error (код причины) и rl_message (пояснение).")


# ============================================================ 1.02 проверка маршрутов
class CheckRoutes(RoutelinerAlgorithm):
    GROUP = "prep"
    NUMBER = "1.02"
    TITLE = "Проверка маршрутов"
    HELP = (
        "Собирает каждый маршрут из всех объектов с одним ID. Мультилинии раскладываются "
        "на части, части упорядочиваются по стыкам, а не по порядку хранения, дуги "
        "сегментируются. Маршрут с разрывом, развилкой или в географической системе "
        "координат попадает в таблицу ошибок.\n\n"
        "Поля результата: route_id (ID маршрута), length (длина по оси, м), parts "
        "(количество частей после сборки), gaps (количество разрывов), gap_max "
        "(наибольший разрыв, м).")

    def name(self):
        return "check_routes"

    def initAlgorithm(self, config=None):
        self.add_route_params()
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("Собранные маршруты"), Qgis.ProcessingSourceType.VectorLine))
        self.add_error_sink()

    def processAlgorithm(self, parameters, context, feedback):
        src, routes, errors = self.routes(parameters, context, feedback)
        fields = fields_of(fld("route_id", T_STR), fld("length", T_DBL),
                           fld("parts", T_INT), fld("gaps", T_INT), fld("gap_max", T_DBL))
        sink, dest = self.parameterAsSink(parameters, "OUTPUT", context, fields,
                                          Qgis.WkbType.MultiLineString, src.sourceCrs())
        for rid, r in routes.items():
            f = QgsFeature(fields)
            g = _line_geometry(r.parts)
            if not g.isMultipart():
                g.convertToMultiType()
            f.setGeometry(g)
            f.setAttributes([str(rid), rm(r.length), len(r.parts), len(r.gaps),
                             rm(max((x.distance for x in r.gaps), default=0.0))])
            sink.addFeature(f, FAST)
        err = self.write_errors(parameters, context, fields_of(), [(None, e) for e in errors])
        feedback.pushInfo(tr("Итого: собрано {a}, ошибок {b}").format(a=len(routes), b=len(errors)))
        return {"OUTPUT": dest, "ERRORS": err}


# ============================================================ 2.xx события
class _EventsBase(RoutelinerAlgorithm):
    LINE = False

    def initAlgorithm(self, config=None):
        self.add_route_params()
        self.addParameter(QgsProcessingParameterFeatureSource(
            "EVENTS", tr("Таблица событий (слой, CSV, Excel)"), [SRC_ANY]))
        self.addParameter(QgsProcessingParameterField(
            "EV_ROUTE", tr("События: поле ID маршрута"), parentLayerParameterName="EVENTS",
            type=FIELD_ANY))
        self.addParameter(QgsProcessingParameterField(
            "EV_FROM", tr("События: поле пикета начала") if self.LINE else tr("События: поле пикета"),
            parentLayerParameterName="EVENTS", type=FIELD_ANY))
        if self.LINE:
            self.addParameter(QgsProcessingParameterField(
                "EV_TO", tr("События: поле пикета конца"), parentLayerParameterName="EVENTS",
                type=FIELD_ANY))
        self.addParameter(QgsProcessingParameterField(
            "EV_OFFSET", tr("События: поле смещения от оси, м"), parentLayerParameterName="EVENTS",
            type=FIELD_NUM, optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            "OFFSET_RIGHT", tr("Положительное смещение вправо по ходу"), False))
        self.addParameter(QgsProcessingParameterField(
            "EV_SECTION", tr("События: поле номера участка (для обратных вставок)"),
            parentLayerParameterName="EVENTS", type=FIELD_NUM, optional=True))
        self.add_chainage_params()
        self.add_outputs()

    def add_outputs(self):
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("События на маршрутах"),
            Qgis.ProcessingSourceType.VectorLine if self.LINE else Qgis.ProcessingSourceType.VectorPoint))
        self.add_error_sink()

    def processAlgorithm(self, parameters, context, feedback):
        src, routes, route_errors = self.routes(parameters, context, feedback)
        loc, _ = self.locator(parameters, context, feedback, routes)
        ev = self.parameterAsSource(parameters, "EVENTS", context)

        def s(n):
            return self.parameterAsString(parameters, n, context) or None

        sign = -1.0 if self.parameterAsBoolean(parameters, "OFFSET_RIGHT", context) else 1.0
        records, feats = read_events(ev, s("EV_ROUTE"), s("EV_FROM"), s("EV_TO") if self.LINE else None,
                                     s("EV_OFFSET"), s("EV_SECTION"), sign)
        # маршрут не собран - отдельное сообщение вместо «не найден»
        broken = {e.route_id: e for e in route_errors}
        if self.LINE:
            ok, bad = loc.locate_lines(records)
        else:
            ok, bad = loc.locate_points(records)
        bad = [CoreError(e.code, tr("маршрут не собран: {msg}").format(msg=broken[e.route_id].message),
                         e.key, e.route_id)
               if e.route_id in broken else e for e in bad]
        fmt = loc.parser.format
        base = ev.fields()
        if self.LINE:
            extra = [fld("rl_m_from", T_DBL), fld("rl_m_to", T_DBL), fld("rl_length", T_DBL),
                     fld("rl_pk_from", T_STR), fld("rl_pk_to", T_STR), fld("rl_swapped", T_INT)]
            wkb = Qgis.WkbType.MultiLineString
        else:
            extra = [fld("rl_m", T_DBL), fld("rl_pk", T_STR), fld("rl_x", T_DBL),
                     fld("rl_y", T_DBL), fld("rl_azimuth", T_DBL)]
            wkb = Qgis.WkbType.Point
        fields = fields_of(base, *extra)
        sink, dest = self.parameterAsSink(parameters, "OUTPUT", context, fields, wkb, src.sourceCrs())
        for i, r in enumerate(ok):
            if feedback.isCanceled():
                break
            f = QgsFeature(fields)
            attrs = list(feats[r.key].attributes())
            if self.LINE:
                g = _line_geometry(r.pieces)
                if not g.isMultipart():
                    g.convertToMultiType()
                attrs += [rm(r.m_from), rm(r.m_to), rm(r.m_to - r.m_from), fmt(r.st_from),
                          fmt(r.st_to), int(r.swapped)]
            else:
                g = QgsGeometry.fromPointXY(QgsPointXY(r.x, r.y))
                attrs += [rm(r.m), fmt(r.station), rm(r.x), rm(r.y), rdeg(r.azimuth)]
            f.setGeometry(g)
            f.setAttributes(attrs)
            sink.addFeature(f, FAST)
            if i % 1000 == 0:
                feedback.setProgress(100 * i / max(len(ok), 1))
        err = self.write_errors(parameters, context, base, [(feats.get(e.key), e) for e in bad])
        feedback.pushInfo(tr("Итого: поставлено {a} из {n}, ошибок {b}").format(
            a=len(ok), n=len(records), b=len(bad)))
        return {"OUTPUT": dest, "ERRORS": err}


POINT_HELP = (
    "Ставит на маршруты записи таблицы по пикету в выбранной записи, со смещением от "
    "оси. Пикет переводится в меру через ведомость маршрута, а без ведомости по длине "
    "оси от пикета начала. Запись «+35» берёт пикет предыдущей записи того же маршрута.\n\n"
    "К полям исходной записи добавляются rl_m (мера по оси, м), rl_pk (пикет в выбранной "
    "записи), rl_x и rl_y (координаты точки в СК маршрутов), rl_azimuth (азимут оси в "
    "точке, градусы от севера по часовой стрелке).")

LINE_HELP = (
    "Вырезает участки маршрутов между пикетами начала и конца, с параллельным смещением. "
    "Участок, записанный против хода маршрута, переворачивается. Участок через разрыв "
    "маршрута при разрешённых разрывах выдаётся мультилинией.\n\n"
    "К полям исходной записи добавляются rl_m_from и rl_m_to (меры начала и конца, м), "
    "rl_length (длина по оси, м), rl_pk_from и rl_pk_to (пикеты начала и конца), "
    "rl_swapped (1, если начало и конец поменяны местами).")


class PointEvents(_EventsBase):
    NUMBER = "2.01"
    TITLE = "Точечные события"
    HELP = POINT_HELP
    HELP_TAIL = (ERRORS_HELP,)
    LINE = False

    def name(self):
        return "point_events"


class LineEvents(_EventsBase):
    NUMBER = "2.02"
    TITLE = "Участки (линейные события)"
    HELP = LINE_HELP
    HELP_TAIL = (ERRORS_HELP,)
    LINE = True

    def name(self):
        return "line_events"


# ============================================================ 3.xx динамические слои
LIVE_HELP = (
    "Параметры те же, что у инструмента {src}, а результат не разовый. Слой в памяти "
    "пересчитывается сам при правке геометрии маршрутов, таблицы событий или ведомости, "
    "в том числе при несохранённой правке и при изменении файла CSV или Excel на диске. "
    "Рядом создаётся таблица ошибок.\n\n"
    "Привязка хранится в проекте и восстанавливается при его открытии. Чтобы отключить "
    "пересчёт, удалите слой событий из проекта.\n\n"
    "Поля слоя совпадают с полями результата инструмента {src}.")


class _LiveBase(_EventsBase):
    """Те же параметры, что у обычной постановки, но результат - слои в памяти,
    которые пересчитываются при правке маршрутов, таблицы или ведомости."""

    GROUP = "live"
    TARGET = ""

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def shortHelpString(self):
        from .common import help_footer
        src = {"point_events": "2.01", "line_events": "2.02"}[self.TARGET]
        return "<p>" + tr(LIVE_HELP).format(src=src).replace("\n\n", "</p><p>") + "</p>" + help_footer()

    def add_outputs(self):
        self.addParameter(QgsProcessingParameterString(
            "NAME", tr("Имя слоя"), tr("Участки") if self.LINE else tr("События")))
        self.addOutput(QgsProcessingOutputString("LAYER_ID", tr("Слой событий")))
        self.addOutput(QgsProcessingOutputString("STATUS", tr("Итог первого расчёта")))

    def processAlgorithm(self, parameters, context, feedback):
        from ..layers import binder
        if binder.manager is None or binder.manager.project is not context.project():
            raise QgsProcessingException(tr("Динамические слои работают только в открытом проекте QGIS"))
        params = {}
        for d in self.parameterDefinitions():
            name = d.name()
            if name == "NAME" or name not in parameters:
                continue
            if name in ("ROUTES", "EVENTS", "LEDGER"):
                lyr = self.parameterAsVectorLayer(parameters, name, context)
                if lyr is None:
                    if name == "LEDGER":
                        continue
                    raise QgsProcessingException(
                        tr("Не найден слой для параметра «{p}»").format(p=d.description()))
                if context.project().mapLayer(lyr.id()) is None:
                    raise QgsProcessingException(
                        tr("Слой «{name}» должен быть в проекте, иначе нечего отслеживать").format(
                            name=lyr.name()))
                params[name] = lyr.id()
            else:
                v = parameters[name]
                params[name] = v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
        routes = self.parameterAsVectorLayer(parameters, "ROUTES", context)
        name = self.parameterAsString(parameters, "NAME", context) or tr("События")
        b = binder.manager.add(self.TARGET, params, name, routes.crs(),
                               "MultiLineString" if self.LINE else "Point")
        feedback.pushInfo(tr("Динамический слой «{name}»: {status}").format(name=name, status=b.last))
        return {"LAYER_ID": b.cfg["out_id"], "STATUS": b.last}


class LivePointEvents(_LiveBase):
    NUMBER = "3.01"
    TITLE = "Динамический слой точечных событий"
    LINE = False
    TARGET = "point_events"

    def name(self):
        return "live_point_events"


class LiveLineEvents(_LiveBase):
    NUMBER = "3.02"
    TITLE = "Динамический слой участков"
    LINE = True
    TARGET = "line_events"

    def name(self):
        return "live_line_events"


# ============================================================ 4.01 пикеты
class Pickets(RoutelinerAlgorithm):
    GROUP = "chainage"
    NUMBER = "4.01"
    TITLE = "Пикетная разбивка"
    HELP = (
        "Ставит точки целых пикетов по каждому маршруту с подписью и азимутом для поворота "
        "подписи. При ведомости учитываются рубленые пикеты и пикетажные уравнения. В прямой "
        "вставке пропущенные пикеты не ставятся, в обратной повторяющиеся ставятся дважды "
        "с разными номерами участков.\n\n"
        "Поля результата: route_id (ID маршрута), pk (пикет в выбранной записи), station "
        "(пикетаж, м), m (мера по оси, м), section (номер участка пикетажа, с нуля), azimuth "
        "(азимут оси, градусы), km (1 для пикета, кратного километру).")

    def name(self):
        return "pickets"

    def initAlgorithm(self, config=None):
        self.add_route_params()
        self.add_chainage_params()
        self.addParameter(QgsProcessingParameterNumber(
            "STEP", tr("Шаг разбивки, м"), DBL, 100.0, minValue=0.001))
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("Пикеты"), Qgis.ProcessingSourceType.VectorPoint))

    def processAlgorithm(self, parameters, context, feedback):
        src, routes, _ = self.routes(parameters, context, feedback)
        loc, _ = self.locator(parameters, context, feedback, routes)
        step = self.parameterAsDouble(parameters, "STEP", context)
        fields = fields_of(fld("route_id", T_STR), fld("pk", T_STR), fld("station", T_DBL),
                           fld("m", T_DBL), fld("section", T_INT), fld("azimuth", T_DBL),
                           fld("km", T_INT))
        sink, dest = self.parameterAsSink(parameters, "OUTPUT", context, fields,
                                          Qgis.WkbType.Point, src.sourceCrs())
        n = 0
        for rid, r in routes.items():
            items = loc.system_for(rid).whole_stations(step)
            if not items:
                continue
            p = r.points_at([m for m, _, _ in items])
            for i, (m, st, sec) in enumerate(items):
                f = QgsFeature(fields)
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(p["x"][i], p["y"][i])))
                f.setAttributes([str(rid), loc.parser.format(st), rm(st), rm(m), sec,
                                 rdeg(p["azimuth"][i]), int(abs(st) % 1000 < 1e-6)])
                sink.addFeature(f, FAST)
                n += 1
        feedback.pushInfo(tr("Итого: пикетов {n}").format(n=n))
        return {"OUTPUT": dest}


# ============================================================ 4.02 привязка точек
class LocatePoints(RoutelinerAlgorithm):
    GROUP = "chainage"
    NUMBER = "4.02"
    TITLE = "Привязка точек к маршрутам"
    HELP = (
        "Обратная задача. Для каждой точки находится ближайший маршрут, и по нему "
        "считаются мера, пикет и смещение от оси со знаком. Точки дальше радиуса поиска "
        "уходят в таблицу ошибок. Если у точек есть поле ID маршрута, привязка идёт только "
        "к этому маршруту.\n\n"
        "К полям точки добавляются rl_route (ID маршрута), rl_m (мера по оси, м), rl_pk "
        "(пикет в выбранной записи), rl_offset (смещение, м, плюс влево по ходу), rl_side "
        "(сторона по ходу маршрута: left, right или axis).")
    HELP_TAIL = (ERRORS_HELP,)

    def name(self):
        return "locate_points"

    def initAlgorithm(self, config=None):
        self.add_route_params()
        self.addParameter(QgsProcessingParameterFeatureSource("POINTS", tr("Точки"), [SRC_POINT]))
        self.addParameter(QgsProcessingParameterField(
            "PT_ROUTE", tr("Точки: поле ID маршрута (необязательно)"),
            parentLayerParameterName="POINTS", type=FIELD_ANY, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "RADIUS", tr("Радиус поиска, м (0 без ограничения)"), DBL, 50.0, minValue=0))
        self.add_chainage_params()
        self.addParameter(QgsProcessingParameterFeatureSink(
            "OUTPUT", tr("Точки с пикетами"), Qgis.ProcessingSourceType.VectorPoint))
        self.add_error_sink()

    def processAlgorithm(self, parameters, context, feedback):
        src, routes, _ = self.routes(parameters, context, feedback)
        loc, _ = self.locator(parameters, context, feedback, routes)
        pts = self.parameterAsSource(parameters, "POINTS", context)
        rf = self.parameterAsString(parameters, "PT_ROUTE", context) or None
        radius = self.parameterAsDouble(parameters, "RADIUS", context) or None
        xform = QgsCoordinateTransform(pts.sourceCrs(), src.sourceCrs(), context.transformContext())
        fields = fields_of(pts.fields(), fld("rl_route", T_STR), fld("rl_m", T_DBL),
                           fld("rl_pk", T_STR), fld("rl_offset", T_DBL), fld("rl_side", T_STR))
        sink, dest = self.parameterAsSink(parameters, "OUTPUT", context, fields,
                                          Qgis.WkbType.Point, src.sourceCrs())
        errors, n = [], 0
        for f in pts.getFeatures():
            if feedback.isCanceled():
                break
            g = f.geometry()
            if g.isEmpty():
                continue
            g.transform(xform)
            p = g.asPoint() if not g.isMultipart() else g.asMultiPoint()[0]
            ids = [_key(f[rf])] if rf else None
            r = loc.locate_xy(f.id(), p.x(), p.y(), ids, radius)
            if isinstance(r, CoreError):
                errors.append((f, r))
                continue
            out = QgsFeature(fields)
            out.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(p)))
            # сторона - код, а не слово: значение поля не зависит от языка интерфейса
            off = rm(r.offset)
            side = "left" if off > 0 else ("right" if off < 0 else "axis")
            out.setAttributes(list(f.attributes()) + [
                str(r.route_id), rm(r.m), loc.parser.format(r.station), off, side])
            sink.addFeature(out, FAST)
            n += 1
        err = self.write_errors(parameters, context, pts.fields(), errors)
        feedback.pushInfo(tr("Итого: привязано {a}, ошибок {b}").format(a=n, b=len(errors)))
        return {"OUTPUT": dest, "ERRORS": err}


ALGORITHMS = [CheckRoutes, PointEvents, LineEvents, LivePointEvents, LiveLineEvents,
              Pickets, LocatePoints]
