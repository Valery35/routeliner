"""Демонстрационный пример: GeoPackage с маршрутами, ведомостью, таблицами
событий и точками дефектов, у каждой записи — эталонный ответ.
При включённой проверке пример сразу прогоняется через алгоритмы модуля
и сравнивается с эталоном."""
from __future__ import annotations

import csv
import math
import os

from qgis.core import (Qgis, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsProcessingContext, QgsProcessingException,
                       QgsProcessingOutputBoolean, QgsProcessingOutputString,
                       QgsProcessingParameterBoolean, QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterNumber, QgsProcessingUtils,
                       QgsVectorFileWriter, QgsVectorLayer)

from ..core import demo as D
from ..i18n import tr
from .common import T_DBL, T_INT, T_STR, RoutelinerAlgorithm, fields_of, fld

TOL = 0.01          # допуск сравнения с эталоном, м
GPKG = "routeliner_demo.gpkg"
DEM = "routeliner_demo_dem.tif"


def _memory(geom: str, fields, name):
    lyr = QgsVectorLayer(f"{geom}?crs={D.CRS}", name, "memory")
    lyr.dataProvider().addAttributes(list(fields))
    lyr.updateFields()
    return lyr


def _add(lyr, rows, geoms=None):
    feats = []
    for i, row in enumerate(rows):
        f = QgsFeature(lyr.fields())
        # эталон пишется до миллиметра, как и результаты модуля
        f.setAttributes([round(v, 3) if isinstance(v, float) else v for v in row])
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
        _add(le, [[ln[c] for c in lcols] for ln in d.lines])
        _write(le, path, "events_lines", context)

        dcols = ["did", "exp_route", "exp_m", "exp_station", "exp_offset"]
        dl = _memory("Point", fields_of(fld("did", T_INT), fld("exp_route", T_STR),
                                        fld("exp_m", T_DBL), fld("exp_station", T_DBL),
                                        fld("exp_offset", T_DBL)), "defects")
        _add(dl, [[f[c] for c in dcols] for f in d.defects],
             [QgsGeometry.fromPointXY(QgsPointXY(f["x"], f["y"])) for f in d.defects])
        _write(dl, path, "defects", context)

        dem_path = os.path.join(folder, DEM)
        self._write_dem(dem_path)

        feedback.pushInfo(tr("Пример записан: {path}").format(path=path))
        feedback.pushInfo(tr("Событий: точечных {a}, линейных {b}, дефектов {c}").format(
            a=len(d.points), b=len(d.lines), c=len(d.defects)))

        group = tr("Routeliner, пример")
        for name, title in (("routes", "Маршруты"), ("defects", "Дефекты"),
                            ("ledger", "Ведомость"), ("events_points", "Точечные события"),
                            ("events_lines", "Линейные события")):
            self._load(context, f"{path}|layername={name}", tr(title), group)
        self._load(context, dem_path, tr("Рельеф"), group)

        summary = {}
        if self.parameterAsBoolean(parameters, "RUN", context):
            summary = self._check(path, context, feedback, group, dem_path)
        return {"FOLDER": folder, **summary}

    @staticmethod
    def _write_dem(dem_path):
        """Растр рельефа примера: плоскость D.dem_z по центрам ячеек, GeoTIFF."""
        import numpy as np
        from osgeo import gdal, osr
        x0, y0, x1, y1 = D.DEM_EXTENT
        c = D.DEM_CELL
        cols, rows = int(round((x1 - x0) / c)), int(round((y1 - y0) / c))
        xc = x0 + (np.arange(cols) + 0.5) * c
        yc = y1 - (np.arange(rows) + 0.5) * c
        grid = D.dem_z(xc[None, :], yc[:, None]).astype("float64")
        if os.path.exists(dem_path):
            os.remove(dem_path)
        ds = gdal.GetDriverByName("GTiff").Create(dem_path, cols, rows, 1, gdal.GDT_Float64)
        ds.SetGeoTransform((x0, c, 0.0, y1, 0.0, -c))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(D.CRS.split(":")[1]))
        ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1)
        band.WriteArray(grid)
        band.SetNoDataValue(-9999.0)
        band.FlushCache()
        ds = None

    def _load(self, context, uri, title, group):
        det = QgsProcessingContext.LayerDetails(title, context.project(), title)
        if hasattr(det, "groupName"):
            det.groupName = group
        context.addLayerToLoadOnCompletion(uri, det)

    # ------------------------------------------------------------ проверка
    def _check(self, path, context, feedback, group, dem_path):
        import processing

        def uri(n):
            return f"{path}|layername={n}"

        common = dict(ROUTES=uri("routes"), ROUTE_ID="route_id", SNAP=0.01,
                      FORMAT=0, PICKET=100.0, START=0.0,
                      LEDGER=uri("ledger"), LG_ROUTE="route_id", LG_STATION="station",
                      LG_MEASURE="measure", LG_AHEAD="station_ahead", LG_SYSTEM="system",
                      SYSTEM=D.SYSTEM)

        def run(alg, extra):
            return processing.run(
                f"routeliner:{alg}", {**common, **extra}, context=context, feedback=None,
                is_child_algorithm=True)

        def layer(ref):
            return QgsProcessingUtils.mapLayerFromString(ref, context)

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

        # калибровка: пикетаж ведомости уходит в M, и те же события ставятся
        # по M без ведомости. Записи с номером участка пропускаются: участки
        # пикетажа из M нумеруются по изломам масштаба, а не по реперам.
        res = run("calibrate_routes", dict(OUT_M=2, OUTPUT="memory:", ERRORS="memory:"))
        cal = res["OUTPUT"]
        cal_ok = {f["route_id"]: (f["source"], f["equations"]) for f in layer(cal).getFeatures()} == {
            "R1": ("length", 0), "R2": ("length", 0), "R3": ("ledger", 2)}
        self._load(context, cal, tr("Калиброванные маршруты"), group)
        res = processing.run("routeliner:point_events", {
            **common, "ROUTES": cal, "LEDGER": None, "USE_M": True,
            "EVENTS": uri("events_points"), "EV_ROUTE": "route_id", "EV_FROM": "pk",
            "EV_OFFSET": "offset", "OUTPUT": "memory:", "ERRORS": "memory:"},
            context=context, feedback=None, is_child_algorithm=True)

        def plain(f):
            return not f["exp_error"] and not isinstance(f["section"], (int, float))

        m_ok = m_total = 0
        for f in layer(res["OUTPUT"]).getFeatures():
            if not plain(f):
                continue
            m_total += 1
            m_ok += math.hypot(f["rl_x"] - f["exp_x"], f["rl_y"] - f["exp_y"]) <= TOL
        m_exp = sum(1 for f in QgsVectorLayer(uri("events_points")).getFeatures() if plain(f))

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

        located = res["OUTPUT"]

        res = run("pickets", dict(STEP=100.0, OUTPUT="memory:"))
        self._load(context, res["OUTPUT"], tr("Пикеты"), group)

        # профиль: отметки рельефа и оси сверяются с формулами
        res = run("profile_table", dict(RASTERS=[dem_path], PICKET_STEP=100.0, STEP=50.0,
                                        VERTICES=0, POIS=uri("defects"), POI_LABEL="did",
                                        CORRIDOR=5.0, OUTPUT="memory:"))
        table = layer(res["OUTPUT"])
        zf = "z_" + os.path.splitext(DEM)[0]
        g_ok = g_total = a_ok = a_total = n_eq = 0
        g_worst = 0.0
        for f in table.getFeatures():
            n_eq += f["route_id"] == "R3" and f["kind"] == "equation"
            if f[zf] is not None:
                g_total += 1
                dz = abs(f[zf] - D.dem_z(f["x"], f["y"]))
                g_worst = max(g_worst, dz)
                g_ok += dz <= TOL
            if f["route_id"] == "R1":
                a_total += 1
                a_ok += f["z_axis"] is not None and abs(f["z_axis"] - D.r1_z(f["m"])) <= TOL
        self._load(context, res["OUTPUT"], tr("Таблица профиля"), group)
        n_table = table.featureCount()
        res = processing.run("routeliner:profile_drawing", dict(
            TABLE=res["OUTPUT"], ROUTE="R1", GROUND=zf, PLAN=located, PLAN_LABEL="did",
            LINES="memory:", TEXTS="memory:"), context=context, feedback=None, is_child_algorithm=True)
        drawn = (abs(res["WIDTH_MM"] - 2000.0 / 500.0 * 1000.0) <= TOL
                 and layer(res["LINES"]).featureCount() > 0 and layer(res["TEXTS"]).featureCount() > 0)
        from .alg_profile import _KEEP, _StyleLines, _StyleTexts
        for ref, title, style in ((res["LINES"], "Профиль, линии", _StyleLines()),
                                  (res["TEXTS"], "Профиль, подписи", _StyleTexts())):
            self._load(context, ref, tr(title), group)
            _KEEP.append(style)
            context.layerToLoadOnCompletionDetails(ref).setPostProcessor(style)

        n_def = QgsVectorLayer(uri("defects")).featureCount()
        passed = (ok_routes and p_ok == p_total == p_total_all and e_ok == exp_err
                  and l_ok == l_total and l_err == 1 and d_ok == d_total == n_def
                  and g_total == n_table and g_ok == g_total and a_ok == a_total > 0
                  and n_eq == 2 and drawn and cal_ok and m_ok == m_total == m_exp > 0)
        yes, no = tr("да"), tr("нет")
        lines = [
            tr("Маршруты: не собран только R4 - {v}").format(
                v=yes if ok_routes else no + " " + str(bad_routes)),
            tr("Точечные: совпало {a} из {n} (наибольшее расхождение {w:.1f} мм), "
               "ожидаемых ошибок распознано {e} из {en}").format(
                a=p_ok, n=p_total_all, w=worst * 1000, e=e_ok, en=exp_err),
            tr("Калибровка: источники и уравнения маршрутов верны - {v}, точечные события "
               "по M совпали {a} из {n}").format(v=yes if cal_ok else no, a=m_ok, n=m_exp),
            tr("Участки: совпало {a} из {n}, ошибка нулевой длины распознана: {v}").format(
                a=l_ok, n=l_total, v=yes if l_err == 1 else no),
            tr("Дефекты: привязано верно {a} из {n}").format(a=d_ok, n=n_def),
            tr("Профиль: отметки рельефа совпали {a} из {n} (наибольшее расхождение {w:.1f} мм), "
               "отметки оси R1 {b} из {m}, уравнений R3 {e} из 2, чертёж построен: {v}").format(
                a=g_ok, n=n_table, w=g_worst * 1000, b=a_ok, m=a_total, e=n_eq,
                v=yes if drawn else no),
            tr("ПРОВЕРКА ПРОЙДЕНА") if passed else tr("ПРОВЕРКА НЕ ПРОЙДЕНА"),
        ]
        for s in lines:
            if passed:
                feedback.pushInfo(s)
            else:
                feedback.reportError(s, False)
        return {"PASSED": passed, "REPORT": "\n".join(lines)}
