"""Демонстрационный пример: GeoPackage с маршрутами, ведомостью, таблицами
событий и точками дефектов, у каждой записи — эталонный ответ.
При включённой проверке пример сразу прогоняется через алгоритмы модуля
и сравнивается с эталоном."""
from __future__ import annotations

import csv
import math
import os

from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsProcessingContext, QgsProcessingException,
                       QgsProcessingOutputBoolean, QgsProcessingOutputString,
                       QgsProcessingParameterBoolean, QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterNumber, QgsProcessingUtils, QgsProject,
                       QgsVectorFileWriter, QgsVectorLayer)

from ..core import demo as D
from ..i18n import tr
from .common import DBL, T_DBL, T_INT, T_STR, RoutelinerAlgorithm, fields_of, fld

TOL = 0.01          # допуск сравнения с эталоном, м
GPKG = "routeliner_demo.gpkg"


def _memory(geom: str, fields, name):
    lyr = QgsVectorLayer(f"{geom}?crs={D.CRS}", name, "memory")
    lyr.dataProvider().addAttributes(list(fields))
    lyr.updateFields()
    return lyr


def _add(lyr, rows, geoms=None):
    feats = []
    for i, row in enumerate(rows):
        f = QgsFeature(lyr.fields())
        f.setAttributes(list(row))
        if geoms is not None:
            f.setGeometry(geoms[i])
        feats.append(f)
    lyr.dataProvider().addFeatures(feats)


def _write(lyr, path, name, context):
    opt = QgsVectorFileWriter.SaveVectorOptions()
    opt.driverName = "GPKG"
    opt.layerName = name
    opt.fileEncoding = "UTF-8"
    opt.actionOnExistingFile = (QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                                if os.path.exists(path) else
                                QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile)
    err = QgsVectorFileWriter.writeAsVectorFormatV3(lyr, path, context.transformContext(), opt)
    if err[0] != QgsVectorFileWriter.WriterError.NoError:
        raise QgsProcessingException(tr("Не записан слой {name}: {err}").format(name=name, err=err[1]))


class DemoAlgorithm(RoutelinerAlgorithm):
    def name(self):
        return "demo"

    GROUP = "prep"
    NUMBER = "1.01"
    TITLE = "Демонстрационный пример"
    HELP = (
        "Создаёт GeoPackage с четырьмя маршрутами: прямая с отметками, настоящая дуга "
        "R=300 м, ломаная из частей в произвольном порядке, маршрут с разрывом. В нём же "
        "исполнительная ведомость с рублеными пикетами, обратной и прямой вставками, "
        "таблицы точечных и линейных событий, в том числе заведомо ошибочных, и точки "
        "дефектов. У каждой записи есть эталонный ответ в полях exp_*, посчитанный "
        "аналитически, без участия модуля.\n\n"
        "С включённой проверкой пример сразу прогоняется через инструменты модуля. Итог "
        "сравнения с эталоном выводится в журнал, результаты добавляются в проект.")

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFolderDestination("FOLDER", tr("Папка для примера")))
        self.addParameter(QgsProcessingParameterNumber(
            "N_POINTS", tr("Количество случайных точечных событий"), Qgis.ProcessingNumberParameterType.Integer,
            60, minValue=3, maxValue=200000))
        self.addParameter(QgsProcessingParameterNumber(
            "SEED", tr("Зерно случайных чисел"), Qgis.ProcessingNumberParameterType.Integer, 1))
        self.addParameter(QgsProcessingParameterBoolean(
            "RUN", tr("Сразу прогнать через модуль и сравнить с эталоном"), True))
        self.addOutput(QgsProcessingOutputBoolean("PASSED", tr("Проверка пройдена")))
        self.addOutput(QgsProcessingOutputString("REPORT", tr("Итог проверки")))

    # ------------------------------------------------------------ запись примера
    def processAlgorithm(self, parameters, context, feedback):
        folder = self.parameterAsString(parameters, "FOLDER", context)
        os.makedirs(folder, exist_ok=True)
        n = self.parameterAsInt(parameters, "N_POINTS", context)
        seed = self.parameterAsInt(parameters, "SEED", context)
        d = D.build(n_points=n, n_defects=max(30, n // 2), seed=seed)
        path = os.path.join(folder, GPKG)
        if os.path.exists(path):
            os.remove(path)

        rl = _memory("MultiCurveZ", fields_of(fld("route_id", T_STR), fld("name", T_STR)), "routes")
        geoms = []
        for _, _, wkt in d.routes:
            g = QgsGeometry.fromWkt(wkt)
            g.convertToMultiType()
            if not g.constGet().is3D():
                g.get().addZValue(0)
            geoms.append(g)
        _add(rl, [(rid, name) for rid, name, _ in d.routes], geoms)
        _write(rl, path, "routes", context)

        lg = _memory("None", fields_of(fld("route_id", T_STR), fld("system", T_STR),
                                       fld("station", T_STR), fld("measure", T_DBL),
                                       fld("station_ahead", T_STR), fld("note", T_STR)), "ledger")
        _add(lg, d.ledger)
        _write(lg, path, "ledger", context)

        pcols = ["eid", "route_id", "pk", "offset", "section", "exp_m", "exp_x", "exp_y",
                 "exp_error", "note"]
        ptypes = [T_INT, T_STR, T_STR, T_DBL, T_INT, T_DBL, T_DBL, T_DBL, T_STR, T_STR]
        ev = _memory("None", fields_of(*[fld(c, t) for c, t in zip(pcols, ptypes)]), "events_points")
        _add(ev, [[p[c] for c in pcols] for p in d.points])
        _write(ev, path, "events_points", context)
        with open(os.path.join(folder, "events_points.csv"), "w", encoding="utf-8-sig",
                  newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(pcols)
            for p in d.points:
                w.writerow(["" if p[c] is None else p[c] for c in pcols])

        lcols = ["eid", "route_id", "pk_from", "pk_to", "offset", "exp_m_from", "exp_m_to",
                 "exp_error", "note"]
        ltypes = [T_INT, T_STR, T_STR, T_STR, T_DBL, T_DBL, T_DBL, T_STR, T_STR]
        le = _memory("None", fields_of(*[fld(c, t) for c, t in zip(lcols, ltypes)]), "events_lines")
        _add(le, [[l[c] for c in lcols] for l in d.lines])
        _write(le, path, "events_lines", context)

        dcols = ["did", "exp_route", "exp_m", "exp_station", "exp_offset"]
        dl = _memory("Point", fields_of(fld("did", T_INT), fld("exp_route", T_STR),
                                        fld("exp_m", T_DBL), fld("exp_station", T_DBL),
                                        fld("exp_offset", T_DBL)), "defects")
        _add(dl, [[f[c] for c in dcols] for f in d.defects],
             [QgsGeometry.fromPointXY(QgsPointXY(f["x"], f["y"])) for f in d.defects])
        _write(dl, path, "defects", context)

        feedback.pushInfo(tr("Пример записан: {path}").format(path=path))
        feedback.pushInfo(tr("Событий: точечных {a}, линейных {b}, дефектов {c}").format(
            a=len(d.points), b=len(d.lines), c=len(d.defects)))

        group = tr("Routeliner, пример")
        for name, title in (("routes", "Маршруты"), ("defects", "Дефекты"),
                            ("ledger", "Ведомость"), ("events_points", "Точечные события"),
                            ("events_lines", "Линейные события")):
            self._load(context, f"{path}|layername={name}", tr(title), group)

        summary = {}
        if self.parameterAsBoolean(parameters, "RUN", context):
            summary = self._check(path, context, feedback, group)
        return {"FOLDER": folder, **summary}

    def _load(self, context, uri, title, group):
        det = QgsProcessingContext.LayerDetails(title, context.project(), title)
        if hasattr(det, "groupName"):
            det.groupName = group
        context.addLayerToLoadOnCompletion(uri, det)

    # ------------------------------------------------------------ проверка
    def _check(self, path, context, feedback, group):
        import processing

        uri = lambda n: f"{path}|layername={n}"
        common = dict(ROUTES=uri("routes"), ROUTE_ID="route_id", SNAP=0.01,
                      FORMAT=0, PICKET=100.0, START=0.0,
                      LEDGER=uri("ledger"), LG_ROUTE="route_id", LG_STATION="station",
                      LG_MEASURE="measure", LG_AHEAD="station_ahead", LG_SYSTEM="system",
                      SYSTEM=D.SYSTEM)
        run = lambda alg, extra: processing.run(
            f"routeliner:{alg}", {**common, **extra}, context=context, feedback=None,
            is_child_algorithm=True)
        layer = lambda ref: QgsProcessingUtils.mapLayerFromString(ref, context)

        res = run("check_routes", dict(OUTPUT="memory:", ERRORS="memory:"))
        bad_routes = [f["rl_route"] for f in layer(res["ERRORS"]).getFeatures()]
        ok_routes = bad_routes == ["R4"]
        self._load(context, res["OUTPUT"], tr("Собранные маршруты"), group)

        # точечные события
        res = run("point_events", dict(EVENTS=uri("events_points"), EV_ROUTE="route_id",
                                       EV_FROM="pk", EV_OFFSET="offset", EV_SECTION="section",
                                       OUTPUT="memory:", ERRORS="memory:"))
        out, err = layer(res["OUTPUT"]), layer(res["ERRORS"])
        p_ok = p_total = 0
        worst = 0.0
        for f in out.getFeatures():
            if f["exp_error"]:
                continue
            p_total += 1
            dxy = math.hypot(f["rl_x"] - f["exp_x"], f["rl_y"] - f["exp_y"])
            worst = max(worst, dxy)
            p_ok += dxy <= TOL
        exp_err = sum(1 for f in QgsVectorLayer(uri("events_points")).getFeatures()
                      if f["exp_error"])
        e_ok = sum(1 for f in err.getFeatures() if f["rl_error"] == f["exp_error"])
        p_total_all = QgsVectorLayer(uri("events_points")).featureCount() - exp_err
        self._load(context, res["OUTPUT"], tr("Точечные события, результат"), group)
        self._load(context, res["ERRORS"], tr("Точечные события, ошибки"), group)

        # линейные события
        res = run("line_events", dict(EVENTS=uri("events_lines"), EV_ROUTE="route_id",
                                      EV_FROM="pk_from", EV_TO="pk_to", EV_OFFSET="offset",
                                      OUTPUT="memory:", ERRORS="memory:"))
        l_ok = l_total = 0
        for f in layer(res["OUTPUT"]).getFeatures():
            l_total += 1
            l_ok += (abs(f["rl_m_from"] - f["exp_m_from"]) <= TOL and
                     abs(f["rl_m_to"] - f["exp_m_to"]) <= TOL)
        l_err = sum(1 for f in layer(res["ERRORS"]).getFeatures() if f["rl_error"] == f["exp_error"])
        self._load(context, res["OUTPUT"], tr("Участки, результат"), group)

        # дефекты: обратная привязка
        res = run("locate_points", dict(POINTS=uri("defects"), RADIUS=50.0,
                                        OUTPUT="memory:", ERRORS="memory:"))
        d_ok = d_total = 0
        for f in layer(res["OUTPUT"]).getFeatures():
            d_total += 1
            d_ok += (f["rl_route"] == f["exp_route"] and abs(f["rl_m"] - f["exp_m"]) <= TOL
                     and abs(f["rl_offset"] - f["exp_offset"]) <= TOL)
        self._load(context, res["OUTPUT"], tr("Дефекты, привязка"), group)

        res = run("pickets", dict(STEP=100.0, OUTPUT="memory:"))
        self._load(context, res["OUTPUT"], tr("Пикеты"), group)

        n_def = QgsVectorLayer(uri("defects")).featureCount()
        passed = (ok_routes and p_ok == p_total == p_total_all and e_ok == exp_err
                  and l_ok == l_total and l_err == 1 and d_ok == d_total == n_def)
        yes, no = tr("да"), tr("нет")
        lines = [
            tr("Маршруты: не собран только R4 - {v}").format(
                v=yes if ok_routes else no + " " + str(bad_routes)),
            tr("Точечные: совпало {a} из {n} (наибольшее расхождение {w:.1f} мм), "
               "ожидаемых ошибок распознано {e} из {en}").format(
                a=p_ok, n=p_total_all, w=worst * 1000, e=e_ok, en=exp_err),
            tr("Участки: совпало {a} из {n}, ошибка нулевой длины распознана: {v}").format(
                a=l_ok, n=l_total, v=yes if l_err == 1 else no),
            tr("Дефекты: привязано верно {a} из {n}").format(a=d_ok, n=n_def),
            tr("ПРОВЕРКА ПРОЙДЕНА") if passed else tr("ПРОВЕРКА НЕ ПРОЙДЕНА"),
        ]
        for s in lines:
            if passed:
                feedback.pushInfo(s)
            else:
                feedback.reportError(s, False)
        return {"PASSED": passed, "REPORT": "\n".join(lines)}
