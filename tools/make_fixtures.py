"""Эталонные прогоны ядра Routeliner для сверки расширения RustGIS.

Пишет в tests/fixtures/
- demo_seed1.json - демонстрационный пример 1.01 (зерно 1, 60 точечных
  событий, 30 дефектов) как таблицы и маршруты в виде частей, какими их
  отдаёт адаптер слоя (дуга R2 уже нарезана).
- tool_X_YY.json - прогоны каждого инструмента на этом примере, параметры,
  ожидаемые слои результата и таблицы ошибок.

Расчёт идёт через ядро routeliner.core без QGIS. Склейка инструментов
(processAlgorithm: чтение таблиц, округление полей, выбор M, подписи)
повторена здесь по коду routeliner/processing. Пустые помощники оттуда
(rm, rdeg, FORMATS, compact_station, _field_name, TEMPLATE_PIPE) берутся
из самого модуля через заглушку qgis.

Запуск из корня репозитория:
    python tools/make_fixtures.py          пересобрать
    python tools/make_fixtures.py --check  сверить с кодом
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from qgis_stub import stubbed_qgis  # noqa: E402

from routeliner import i18n  # noqa: E402
from routeliner.core import demo as D  # noqa: E402
from routeliner.core.assembler import RouteAssembler  # noqa: E402
from routeliner.core.chainage import ChainageSystem  # noqa: E402
from routeliner.core.errors import CoreError, ErrorCode  # noqa: E402
from routeliner.core.events import EventLocator, EventRecord  # noqa: E402
from routeliner.core.profile import ProfileDrawer, ProfilePoint, Row, bilinear, collect_points  # noqa: E402
from routeliner.core.stations import StationParser  # noqa: E402

SEED, N_POINTS = 1, 60
N_DEFECTS = max(30, N_POINTS // 2)          # как в alg_demo
CURVE_ANGLE_DEG = 0.02                       # layers/route_source.py
ARC_ANGLE_DEG = CURVE_ANGLE_DEG              # нарезка дуги R2 в этом прогоне
IN_DIGITS = 6                                # знаков координат частей на входе
GEOM_FULL = 400                              # длиннее - геометрия кратко
TR = i18n.tr

# пустые помощники модуля, взятые из кода инструментов
_H = {}


def _load_helpers():
    i18n.set_language("ru")
    with stubbed_qgis():
        from routeliner.layers import route_source
        from routeliner.processing import alg_demo, alg_profile, common
        _H.update(rm=common.rm, rdeg=common.rdeg, FORMATS=common.FORMATS,
                  compact=alg_profile.compact_station, field_name=alg_profile._field_name,
                  template=alg_profile.TEMPLATE_PIPE, vertex_modes=alg_profile.VERTEX_MODES,
                  dem_name=os.path.splitext(alg_demo.DEM)[0], TOL=alg_demo.TOL,
                  curve=route_source.CURVE_ANGLE_DEG)
    assert _H["curve"] == CURVE_ANGLE_DEG


def rm(v):
    return _H["rm"](v)


def rdeg(v):
    return _H["rdeg"](v)


def parser(fmt=0, picket=100.0):
    return StationParser(_H["FORMATS"][fmt][0], picket)


# ============================================================ адаптер слоя
def _pts(text):
    return [[float(v) for v in p.split()] for p in text.split(",")]


def _circle(p1, p2, p3):
    """Центр и радиус окружности через три точки (как circleCenterRadius QGIS)."""
    dx21, dy21 = p2[0] - p1[0], p2[1] - p1[1]
    dx31, dy31 = p3[0] - p1[0], p3[1] - p1[1]
    h21, h31 = dx21 ** 2 + dy21 ** 2, dx31 ** 2 + dy31 ** 2
    d = 2 * (dx21 * dy31 - dx31 * dy21)
    cx = p1[0] + (h21 * dy31 - h31 * dy21) / d
    cy = p1[1] - (h21 * dx31 - h31 * dx21) / d
    return cx, cy, math.hypot(cx - p1[0], cy - p1[1])


def segmentize_arc(p1, p2, p3, angle_deg=None):
    """Нарезка дуги по наибольшему углу, по образцу QgsGeometryUtils.segmentizeArc.
    Дуга примера поворачивает влево (против часовой), обращать порядок не нужно.
    Без угла берётся ARC_ANGLE_DEG (у модуля - CURVE_ANGLE_DEG)."""
    angle_deg = ARC_ANGLE_DEG if angle_deg is None else angle_deg
    cx, cy, r = _circle(p1, p2, p3)
    inc = math.radians(angle_deg)
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    a3 = math.atan2(p3[1] - cy, p3[0] - cx)
    if a3 <= a1:
        a3 += 2 * math.pi
    out = [list(p1)]
    stop = a3 - inc / 100
    a = a1 + inc
    while a < stop:
        out.append([cx + r * math.cos(a), cy + r * math.sin(a), 0.0])
        a += inc
    out.append(list(p3))
    return out


def wkt_parts(wkt):
    """Части геометрии маршрута, как их отдаёт geometry_parts для MultiCurveZ.
    В GeoPackage примера маршруты без Z получают Z = 0."""
    def z3(pts):
        return [p if len(p) == 3 else p + [0.0] for p in pts]
    head = wkt.split("(", 1)[0].strip().lower()
    body = wkt[wkt.index("(") + 1:wkt.rindex(")")]
    if head.startswith("compoundcurve"):
        line = []
        for kind, text in re.findall(r"(CircularString)?\s*\(([^()]+)\)", body):
            pts = z3(_pts(text))
            if kind:
                pts = segmentize_arc(*pts)
            line += pts[1:] if line else pts
        return [line]
    if head.startswith("multilinestring"):
        return [z3(_pts(t)) for t in re.findall(r"\(([^()]+)\)", body)]
    return [z3(_pts(body))]


def _round_parts(parts):
    return [[[round(v, IN_DIGITS) for v in p] for p in part] for part in parts]


def build_routes(route_parts, snap=0.01, allow_gaps=False, use_z=False, reverse=False):
    """build_routes адаптера: маршруты по порядку первого появления ID."""
    asm = RouteAssembler(snap_tolerance=snap, allow_gaps=allow_gaps, use_z=use_z, reverse=reverse)
    routes, errors = {}, []
    for rid, parts in route_parts.items():
        r = asm.build(rid, [np.array(p, dtype=float) for p in parts])
        if isinstance(r, CoreError):
            errors.append(r)
        else:
            routes[rid] = r
    return routes, errors


# ============================================================ запись в JSON
def _num(v):
    if v is None:
        return None
    v = float(v)
    return None if v != v else v


def geom_line(pieces, mvals=None):
    """Линия или мультилиния: куски [[x, y(, m)]...]. Длинный кусок пишется
    кратко - число вершин, первая, последняя и каждая сотая вершина."""
    out = []
    for i, c in enumerate(pieces):
        c = np.asarray(c, dtype=float)
        rows = [[float(x), float(y)] + ([float(mvals[i][k])] if mvals is not None else [])
                for k, (x, y) in enumerate(c[:, :2])]
        if len(rows) <= GEOM_FULL:
            out.append(rows)
        else:
            out.append({"n": len(rows), "first": rows[0], "last": rows[-1],
                        "every_100th": rows[::100]})
    return out


def err_row(e, key=None):
    return {"key": key if key is not None else e.key,
            "rl_route": None if e.route_id is None else str(e.route_id),
            "rl_error": e.code.value, "rl_message": e.message}


# ============================================================ пример
def demo_data():
    d = D.build(n_points=N_POINTS, n_defects=N_DEFECTS, seed=SEED)
    route_parts = {}
    routes_tab = []
    for fid, (rid, name, wkt) in enumerate(d.routes, 1):
        parts = _round_parts(wkt_parts(wkt))
        route_parts.setdefault(rid, []).extend(parts)
        routes_tab.append({"fid": fid, "route_id": rid, "name": name, "wkt": wkt, "parts": parts})

    def r3(v):                                   # _add в alg_demo пишет дроби до 0,001
        return round(v, 3) if isinstance(v, float) else v
    ledger = [dict(zip(("route_id", "system", "station", "measure", "station_ahead", "note"),
                       [r3(v) for v in row])) for row in d.ledger]
    points = [{k: r3(v) for k, v in p.items()} for p in d.points]
    lines = [{k: r3(v) for k, v in ln.items()} for ln in d.lines]
    defects = [{"did": f["did"], "x": f["x"], "y": f["y"],
                **{k: r3(f[k]) for k in ("exp_route", "exp_m", "exp_station", "exp_offset")}}
               for f in d.defects]
    return d, route_parts, {"routes": routes_tab, "ledger": ledger, "events_points": points,
                            "events_lines": lines, "defects": defects}


def dem_grid():
    """Растр рельефа примера, как _write_dem: плоскость по центрам ячеек."""
    x0, y0, x1, y1 = D.DEM_EXTENT
    c = D.DEM_CELL
    cols, rows = int(round((x1 - x0) / c)), int(round((y1 - y0) / c))
    xc = x0 + (np.arange(cols) + 0.5) * c
    yc = y1 - (np.arange(rows) + 0.5) * c
    return D.dem_z(xc[None, :], yc[:, None]).astype("float64"), (x0, y1, c)


def sample(grid, origin, xs, ys):
    """layers/rasters.sample без пересчёта СК: окно растра и билинейная интерполяция."""
    x0, y0, dx = origin
    dy = dx
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    nrow, ncol = grid.shape
    c0 = max(int(math.floor((np.nanmin(xs) - x0) / dx)) - 2, 0)
    c1 = min(int(math.ceil((np.nanmax(xs) - x0) / dx)) + 2, ncol)
    r0 = max(int(math.floor((y0 - np.nanmax(ys)) / dy)) - 2, 0)
    r1 = min(int(math.ceil((y0 - np.nanmin(ys)) / dy)) + 2, nrow)
    if c1 <= c0 or r1 <= r0:
        return np.full(len(xs), np.nan)
    win = grid[r0:r1, c0:c1]
    return bilinear(win, x0 + c0 * dx, y0 - r0 * dy, dx, -dy, xs, ys)


# ============================================================ склейка инструментов
class World:
    """Пример, собранный так, как его видят инструменты."""

    def __init__(self):
        self.d, self.route_parts, self.tables = demo_data()

    def routes(self, **kw):
        return build_routes(self.route_parts, **kw)

    def ledger_systems(self, prs, routes):
        """read_ledger с фильтром по системе D.SYSTEM."""
        rows, errors = {}, []
        for fid, f in enumerate(self.tables["ledger"], 1):
            if str(f["system"]).strip() != D.SYSTEM:
                continue
            rid = f["route_id"]
            st = prs.parse(f["station"])
            if isinstance(st, CoreError):
                errors.append(st.with_key(fid, rid))
                continue
            ahead = None
            if f["station_ahead"] not in (None, ""):
                a = prs.parse(f["station_ahead"])
                if isinstance(a, CoreError):
                    errors.append(a.with_key(fid, rid))
                    continue
                ahead = a.value
            rows.setdefault(rid, []).append((st.value, f["measure"], ahead))
        systems = {}
        for rid, rr in rows.items():
            s = ChainageSystem.from_table(D.SYSTEM, rr, routes[rid].length if rid in routes else None)
            if isinstance(s, CoreError):
                errors.append(s.with_key(None, rid))
            else:
                systems[rid] = s
        return {k: v for k, v in systems.items() if k in routes}, errors

    def locator(self, routes, fmt=0, ledger=True, use_m=False, factor=1.0, start=0.0):
        prs = parser(fmt)
        systems, errors = self.ledger_systems(prs, routes) if ledger else ({}, [])
        if use_m:
            for rid, r in routes.items():
                if rid in systems or not r.has_m:
                    continue
                s = ChainageSystem.from_measures(TR("M геометрии"), r.vertex_measures(), r.length, factor)
                if isinstance(s, CoreError):
                    errors.append(s.with_key(None, rid))
                else:
                    systems[rid] = s
        return EventLocator(routes, prs, systems, start), errors


LEDGER_PARAMS = dict(LEDGER="demo:ledger", LG_ROUTE="route_id", LG_STATION="station",
                     LG_MEASURE="measure", LG_AHEAD="station_ahead", LG_SYSTEM="system",
                     SYSTEM=D.SYSTEM)
ROUTE_PARAMS = dict(ROUTES="demo:routes", ROUTE_ID="route_id", SNAP=0.01, ALLOW_GAPS=False,
                    USE_Z=False, REVERSE=False)
CHAIN_PARAMS = dict(FORMAT=0, PICKET=100.0, START=0.0, USE_M=False, M_FACTOR=1.0)


def pieces_m(pieces, piece_m, out_m, system):
    """_pieces_m из algorithms.py."""
    if not out_m:
        return pieces, None
    if out_m == 1:
        return pieces, [list(m) for m in piece_m]
    cs, ms = [], []
    for c, m in zip(pieces, piece_m):
        c2, _, st = system.stations_along(c, m)
        cs.append(c2)
        ms.append(list(st))
    return cs, ms


# ------------------------------------------------------------ 1.02
def run_check_routes(w, allow_gaps=False, reverse=False):
    routes, errors = w.routes(allow_gaps=allow_gaps, reverse=reverse)
    out = [{"route_id": str(rid), "length": rm(r.length), "parts": len(r.parts), "gaps": len(r.gaps),
            "gap_max": rm(max((x.distance for x in r.gaps), default=0.0)),
            "geometry": geom_line(r.parts)} for rid, r in routes.items()]
    return {"OUTPUT": out, "ERRORS": [err_row(e) for e in errors]}


# ------------------------------------------------------------ 1.03
def calibrate(w, routes, route_errors, out_m=2, ledger=True, fmt=0, control=None, radius=10.0,
              use_m=False):
    loc, lerr = w.locator(routes, fmt=fmt, ledger=ledger, use_m=use_m)
    ledger_ids = {k for k, v in loc.systems.items() if v.name != TR("M геометрии")} if ledger else set()
    m_ids = set(loc.systems) - ledger_ids
    ct, ct_err = {}, []
    if control is not None:
        plain = EventLocator(routes, loc.parser)
        rows = {}
        for f in control:
            st = loc.parser.parse(f["station"])
            if isinstance(st, CoreError):
                ct_err.append(st.with_key(f["key"]))
                continue
            r = plain.locate_xy(f["key"], f["x"], f["y"], None, radius or None)
            if isinstance(r, CoreError):
                ct_err.append(r)
                continue
            rows.setdefault(r.route_id, []).append((st.value, r.m, None))
        for rid, rr in rows.items():
            s = ChainageSystem.from_table(TR("контрольные точки"), rr, routes[rid].length)
            if isinstance(s, CoreError):
                ct_err.append(s.with_key(None, rid))
            else:
                ct[rid] = s
    loc.systems.update(ct)
    out_m = out_m or 2
    out, geoms = [], {}
    route_errors = list(route_errors)
    for rid, r in routes.items():
        system = loc.system_for(rid)
        pieces = r.substring_m(0.0, r.length)
        if isinstance(pieces, CoreError):
            route_errors.append(pieces.with_key(None, rid))
            continue
        cs, ms = pieces_m([c for c, _ in pieces], [m for _, m in pieces], out_m, system)
        geoms[rid] = (cs, ms)
        source = "points" if rid in ct else "ledger" if rid in ledger_ids else \
            "m" if rid in m_ids else "length"
        s0, s1 = system.to_station(0.0), system.to_station_back(r.length)
        out.append({"route_id": str(rid), "length": rm(r.length), "st_from": rm(s0), "st_to": rm(s1),
                    "pk_from": loc.parser.format(s0), "pk_to": loc.parser.format(s1),
                    "sections": len(system.sections), "equations": len(system.equations()),
                    "source": source, "geometry": geom_line(cs, ms)})
    errs = [err_row(e) for e in route_errors + lerr + ct_err]
    return {"OUTPUT": out, "ERRORS": errs}, geoms


def calibrated_parts(geoms):
    """Калиброванные маршруты, прочитанные обратно: x, y, Z нет (NaN), M."""
    parts = {}
    for rid, (cs, ms) in geoms.items():
        parts[rid] = [[[round(float(x), IN_DIGITS), round(float(y), IN_DIGITS), float("nan"),
                        round(float(m), IN_DIGITS)] for (x, y), m in
                       zip(np.asarray(c)[:, :2], mm)] for c, mm in zip(cs, ms)]
    return parts


# ------------------------------------------------------------ 2.01 и 2.02
def read_events(rows, line, offset_right=False, section=True, from_f="pk", to_f="pk_to"):
    sign = -1.0 if offset_right else 1.0
    recs = []
    for f in rows:
        off = f.get("offset")
        sec = f.get("section") if section else None
        recs.append(EventRecord(f["eid"], f["route_id"],
                                f[from_f] if not line else f["pk_from"],
                                f[to_f] if line else None,
                                sign * (off or 0.0), int(sec) if sec is not None else None))
    return recs


def run_events(w, line, out_m=0, offset_right=False, routes=None, route_errors=None, ledger=True,
               use_m=False, section=True):
    if routes is None:
        routes, route_errors = w.routes()
    loc, _ = w.locator(routes, ledger=ledger, use_m=use_m)
    rows = w.tables["events_lines" if line else "events_points"]
    recs = read_events(rows, line, offset_right, section=section)
    broken = {e.route_id: e for e in route_errors}
    ok, bad = (loc.locate_lines if line else loc.locate_points)(recs)
    bad = [CoreError(e.code, TR("маршрут не собран: {msg}").format(msg=broken[e.route_id].message),
                     e.key, e.route_id) if e.route_id in broken else e for e in bad]
    fmt = loc.parser.format
    out = []
    for r in ok:
        if line:
            cs, ms = pieces_m(r.pieces, r.piece_m, out_m, loc.system_for(r.route_id))
            out.append({"key": r.key, "rl_m_from": rm(r.m_from), "rl_m_to": rm(r.m_to),
                        "rl_length": rm(r.m_to - r.m_from), "rl_pk_from": fmt(r.st_from),
                        "rl_pk_to": fmt(r.st_to), "rl_swapped": int(r.swapped),
                        "geometry": geom_line(cs, ms)})
        else:
            g = [r.x, r.y] + ([r.m if out_m == 1 else r.station] if out_m else [])
            out.append({"key": r.key, "rl_m": rm(r.m), "rl_pk": fmt(r.station), "rl_x": rm(r.x),
                        "rl_y": rm(r.y), "rl_azimuth": rdeg(r.azimuth), "geometry": g,
                        "_raw": r})
    return {"OUTPUT": out, "ERRORS": [err_row(e) for e in bad]}


# ------------------------------------------------------------ 4.01
def run_pickets(w, step=100.0, out_m=0, ledger=True):
    routes, _ = w.routes()
    loc, _ = w.locator(routes, ledger=ledger)
    out = []
    for rid, r in routes.items():
        items = loc.system_for(rid).whole_stations(step)
        if not items:
            continue
        p = r.points_at([m for m, _, _ in items])
        for i, (m, st, sec) in enumerate(items):
            x, y = float(p["x"][i]), float(p["y"][i])
            out.append({"route_id": str(rid), "pk": loc.parser.format(st), "station": rm(st), "m": rm(m),
                        "section": sec, "azimuth": rdeg(p["azimuth"][i]),
                        "km": int(abs(st) % 1000 < 1e-6),
                        "geometry": [x, y] + ([m if out_m == 1 else st] if out_m else [])})
    return {"OUTPUT": out}


# ------------------------------------------------------------ 4.02
def run_locate(w, radius=50.0, ledger=True):
    routes, _ = w.routes()
    loc, _ = w.locator(routes, ledger=ledger)
    out, errors = [], []
    for f in w.tables["defects"]:
        r = loc.locate_xy(f["did"], f["x"], f["y"], None, radius or None)
        if isinstance(r, CoreError):
            errors.append(err_row(r))
            continue
        off = rm(r.offset)
        side = "left" if off > 0 else ("right" if off < 0 else "axis")
        out.append({"key": f["did"], "rl_route": str(r.route_id), "rl_m": rm(r.m),
                    "rl_pk": loc.parser.format(r.station), "rl_offset": off, "rl_side": side,
                    "geometry": [f["x"], f["y"]]})
    return {"OUTPUT": out, "ERRORS": errors}


# ------------------------------------------------------------ 5.01
def run_profile_table(w, picket_step=100.0, step=50.0, vertices=0, corridor=5.0, rasters=True,
                      pois=True, route_list=None):
    routes, _ = w.routes()
    loc, _ = w.locator(routes)
    if route_list:
        routes = {k: routes[k] for k in route_list if k in routes}
    mode = _H["vertex_modes"][vertices][0]
    grid, origin = dem_grid()
    zf = _H["field_name"](_H["dem_name"], set()) if rasters else None
    events = {rid: [] for rid in routes}
    if pois:
        for f in w.tables["defects"]:
            best = None
            for rid, r in routes.items():
                pr = r.locate(f["x"], f["y"])
                if hasattr(pr, "m") and (best is None or abs(pr.offset) < abs(best[1].offset)):
                    best = (rid, pr)
            if best is not None and abs(best[1].offset) <= corridor:
                events[best[0]].append((best[1].m, str(f["did"])))
    fmt = loc.parser.format
    out = []
    for rid, r in routes.items():
        pts = collect_points(r, loc.system_for(rid), picket_step, step, mode, events=events.get(rid, ()))
        ms = [p.m for p in pts]
        xyz = r.points_at(ms)
        zs = np.asarray(xyz["z"], dtype=float)
        if not np.any(np.nan_to_num(zs) != 0):
            zs = np.full(len(ms), np.nan)
        vals = sample(grid, origin, xyz["x"], xyz["y"]) if rasters else None
        for i, p in enumerate(pts):
            pk = fmt(p.station) if p.kind != "equation" else f"{fmt(p.station)} = {fmt(p.station_ahead)}"
            row = {"route_id": str(rid), "n": i + 1, "kind": p.kind, "m": rm(p.m),
                   "station": rm(p.station), "station_ahead": rm(p.station_ahead), "pk": pk,
                   "section": p.section, "x": rm(xyz["x"][i]), "y": rm(xyz["y"][i]),
                   "z_axis": rm(float(zs[i])), "turn": rdeg(p.turn) if p.turn else None,
                   "label": p.label or None}
            if rasters:
                row[zf] = rm(vals[i])
            row["geometry"] = [float(xyz["x"][i]), float(xyz["y"][i])]
            out.append(row)
    return {"OUTPUT": out}, zf


# ------------------------------------------------------------ 5.02
def run_profile_drawing(table, zf, plan_rows, route="R1", d=0.16, base=0.3, h_scale=500.0,
                        v_scale=100.0, min_gap=3.0, grade_tol=0.02):
    feats = [f for f in table if f["route_id"] == route]
    feats.sort(key=lambda f: f["m"])

    def num(v, dflt=math.nan):
        return dflt if v is None or v == "" else float(v)
    pts = [ProfilePoint(m=float(f["m"]), kind=str(f["kind"] or "step"), label=str(f["label"] or ""),
                        turn=num(f["turn"], 0.0), station=num(f["station"]),
                        station_ahead=num(f["station_ahead"]), section=int(f["section"] or 0))
           for f in feats]
    subst = {"d": repr(d), "base": repr(base), "ground": zf, "design": None, "pipe": "z_axis"}

    def evaluate(text):
        missing = [k for k in re.findall(r"\{(\w+)\}", text) if subst.get(k) is None]
        if missing:
            return None
        expr = re.sub(r"\{(\w+)\}", lambda mo: subst[mo.group(1)], text)
        out = np.full(len(feats), np.nan)
        for i, f in enumerate(feats):
            env = {k: (math.nan if v is None else v) for k, v in f.items() if k != "geometry"}
            out[i] = float(eval(expr, {"__builtins__": {}}, env))  # nosec - шаблон модуля
        return out
    rows, used = [], []
    for title, kind, source, dec, height, draw in _H["template"]:
        title = TR(title)
        decimals = int(float(dec)) if dec else (0 if kind in ("station", "text") else 2)
        row = Row(title, kind, float(height) if height else 15.0, decimals, draw == "1",
                  tolerance=grade_tol)
        if kind in ("value", "grade"):
            vals = evaluate(source)
            if vals is None:
                continue
            row.values = vals
        elif kind == "text":
            continue                     # слоя участков в прогоне нет
        rows.append(row)
        used.append(title)
    plan = [(p["rl_m"], p["rl_offset"], str(p["key"])) for p in plan_rows if p["rl_route"] == route]
    drawer = ProfileDrawer(pts, [_H["compact"](str(f["pk"] or "")) for f in feats],
                           h_scale, v_scale, None, min_gap, plan)
    sheet = drawer.build(rows)
    xs = [f["geometry"][0] for f in table]
    ys = [f["geometry"][1] for f in table]
    top = max([y for c, *_ in sheet.lines for _, y in c] + [0.0])
    origin = [min(xs), min(ys) - 100.0 - top]
    return {
        "rows_used": used,
        "origin": origin,
        "WIDTH_MM": sheet.width,
        "HORIZON": sheet.horizon,
        "LINES": [{"kind": k, "row": r, "color": c, "width": wd, "geometry": [list(p) for p in co]}
                  for co, k, r, c, wd in sheet.lines],
        "TEXTS": [{"text": t, "kind": k, "rot": rot, "size": sz, "halign": ha, "valign": va,
                   "geometry": [x, y]} for x, y, t, rot, sz, ha, va, k in sheet.texts]
        + [{"text": "", "kind": k, "rot": 0.0, "size": 0.0, "halign": "Center", "valign": "Half",
            "geometry": [x, y]} for x, y, k, _ in sheet.marks],
    }


# ============================================================ сборка файлов
def _strip(res):
    for f in res.get("OUTPUT", []):
        f.pop("_raw", None)
    return res


def _case(name, about, params, expected):
    return {"name": name, "about": about, "params": params, "expected": expected}


def build_all() -> dict:
    _load_helpers()
    i18n.set_language("ru")
    w = World()
    files = {}
    common = {**ROUTE_PARAMS, **CHAIN_PARAMS, **LEDGER_PARAMS}

    files["demo_seed1.json"] = {
        "about": "Демонстрационный пример 1.01 при зерне 1. Маршруты даны частями в том виде, "
                 "в каком их отдаёт адаптер слоя, дуга R2 нарезана по углу "
                 f"{CURVE_ANGLE_DEG} градуса на хорду. Дроби таблиц округлены до 0,001, "
                 f"координаты частей до {IN_DIGITS} знаков, как читает модуль.",
        "build": {"n_points": N_POINTS, "n_defects": N_DEFECTS, "seed": SEED},
        "crs": D.CRS,
        "dem": {"extent": list(D.DEM_EXTENT), "cell": D.DEM_CELL,
                "formula": "z = 151.5 + 0.01 * (x - X0) + 0.02 * (y - Y0)",
                "origin": [D.X0, D.Y0], "layer_name": _H["dem_name"],
                "note": "Значение берётся в центре ячейки, растр Float64, нет данных -9999"},
        **w.tables,
    }

    # 1.01 - итог проверки примера, посчитанный ядром
    r_out = run_check_routes(w)
    p_res = run_events(w, False)
    l_res = run_events(w, True)
    loc_res = run_locate(w)
    routes, rerr = w.routes()
    cal, geoms = calibrate(w, routes, rerr)
    mroutes, _ = build_routes(calibrated_parts(geoms))
    m_res = run_events(w, False, routes=mroutes, route_errors=[], ledger=False, use_m=True, section=False)
    table, zf = run_profile_table(w)
    TOL = _H["TOL"]
    pts = {p["eid"]: p for p in w.tables["events_points"]}
    lns = {p["eid"]: p for p in w.tables["events_lines"]}
    dfs = {p["did"]: p for p in w.tables["defects"]}

    def near(f, e):
        return math.hypot(f["_raw"].x - e["exp_x"], f["_raw"].y - e["exp_y"])
    p_dist = [near(f, pts[f["key"]]) for f in p_res["OUTPUT"] if not pts[f["key"]]["exp_error"]]
    plain = [p for p in w.tables["events_points"] if not p["exp_error"] and p["section"] is None]
    m_ok = sum(near(f, pts[f["key"]]) <= TOL for f in m_res["OUTPUT"]
               if not pts[f["key"]]["exp_error"] and pts[f["key"]]["section"] is None)
    g_err = [abs(f[zf] - D.dem_z(f["geometry"][0], f["geometry"][1])) for f in table["OUTPUT"]
             if f[zf] is not None]
    a_rows = [f for f in table["OUTPUT"] if f["route_id"] == "R1"]
    check = {
        "routes_not_built": [e["rl_route"] for e in r_out["ERRORS"]],
        "points_matched": sum(x <= TOL for x in p_dist), "points_total": len(p_dist),
        "points_worst_mm": round(max(p_dist) * 1000, 3),
        "point_errors_recognized": sum(e["rl_error"] == pts[e["key"]]["exp_error"] for e in p_res["ERRORS"]),
        "point_errors_expected": sum(1 for p in pts.values() if p["exp_error"]),
        "calibration": {f["route_id"]: [f["source"], f["equations"]] for f in cal["OUTPUT"]},
        "points_by_m_matched": m_ok, "points_by_m_total": len(plain),
        "lines_matched": sum(abs(f["rl_m_from"] - lns[f["key"]]["exp_m_from"]) <= TOL and
                             abs(f["rl_m_to"] - lns[f["key"]]["exp_m_to"]) <= TOL for f in l_res["OUTPUT"]),
        "lines_total": len(l_res["OUTPUT"]),
        "line_errors_recognized": sum(e["rl_error"] == lns[e["key"]]["exp_error"] for e in l_res["ERRORS"]),
        "defects_matched": sum(f["rl_route"] == dfs[f["key"]]["exp_route"]
                               and abs(f["rl_m"] - dfs[f["key"]]["exp_m"]) <= TOL
                               and abs(f["rl_offset"] - dfs[f["key"]]["exp_offset"]) <= TOL
                               for f in loc_res["OUTPUT"]),
        "defects_total": len(w.tables["defects"]),
        "profile_points": len(table["OUTPUT"]),
        "profile_ground_matched": sum(x <= TOL for x in g_err), "profile_ground_total": len(g_err),
        "profile_ground_worst_mm": round(max(g_err) * 1000, 3),
        "profile_axis_r1_matched": sum(f["z_axis"] is not None and abs(f["z_axis"] - D.r1_z(f["m"])) <= TOL
                                       for f in a_rows),
        "profile_axis_r1_total": len(a_rows),
        "profile_equations_r3": sum(f["route_id"] == "R3" and f["kind"] == "equation"
                                    for f in table["OUTPUT"]),
    }
    files["tool_1_01.json"] = {
        "tool": "1.01", "about": "Итог встроенной проверки примера, посчитанный ядром без QGIS. "
                                 "Входные таблицы лежат в demo_seed1.json.",
        "cases": [_case("seed1", "Параметры инструмента по умолчанию",
                        {"N_POINTS": N_POINTS, "SEED": SEED, "RUN": True}, {"check": check})]}

    files["tool_1_02.json"] = {"tool": "1.02", "cases": [
        _case("default", "R4 с разрывом 15 м уходит в ошибки", dict(ROUTE_PARAMS), r_out),
        _case("allow_gaps", "Разрывы разрешены, R4 собран из двух частей",
              {**ROUTE_PARAMS, "ALLOW_GAPS": True}, run_check_routes(w, allow_gaps=True)),
        _case("reverse", "Обратное направление маршрутов", {**ROUTE_PARAMS, "REVERSE": True},
              run_check_routes(w, reverse=True)),
    ]}

    cal_m1, _ = calibrate(w, routes, rerr, out_m=1)
    control = [{"key": f["did"], "x": f["x"], "y": f["y"], "station": f["exp_station"]}
               for f in w.tables["defects"]]
    cal_ct, _ = calibrate(w, routes, rerr, ledger=False, fmt=3, control=control, radius=10.0)
    files["tool_1_03.json"] = {"tool": "1.03", "cases": [
        _case("ledger_station", "Пикетаж ведомости в M, R3 получает два уравнения",
              {**common, "OUT_M": 2}, cal),
        _case("ledger_measure", "Мера по оси в M", {**common, "OUT_M": 1}, cal_m1),
        _case("control_points", "Контрольные точки - дефекты примера с exp_station, запись "
                                "метрами, радиус 10 м. Дефекты дальше 10 м уходят в ошибки",
              {**ROUTE_PARAMS, **CHAIN_PARAMS, "FORMAT": 3, "CONTROL": "demo:defects",
               "CT_STATION": "exp_station", "CT_ROUTE": None, "CT_RADIUS": 10.0, "OUT_M": 2}, cal_ct),
    ]}

    ev_p = dict(EVENTS="demo:events_points", EV_ROUTE="route_id", EV_FROM="pk", EV_OFFSET="offset",
                EV_SECTION="section", OFFSET_RIGHT=False)
    files["tool_2_01.json"] = {"tool": "2.01", "cases": [
        _case("ledger", "Как во встроенной проверке", {**common, **ev_p, "OUT_M": 0}, _strip(p_res)),
        _case("ledger_out_m_station", "Пикетаж в M точки", {**common, **ev_p, "OUT_M": 2},
              _strip(run_events(w, False, out_m=2))),
        _case("offset_right", "Положительное смещение вправо", {**common, **ev_p, "OFFSET_RIGHT": True},
              _strip(run_events(w, False, offset_right=True))),
        _case("by_m", "Маршруты - результат 1.03 ledger_station, пикетаж из M без ведомости, "
                      "поле участка не задано",
              {**ROUTE_PARAMS, **CHAIN_PARAMS, **ev_p, "ROUTES": "tool_1_03:ledger_station",
               "EV_SECTION": None, "USE_M": True, "LEDGER": None},
              {"routes_parts": calibrated_parts(geoms), **_strip(m_res)}),
    ]}
    ev_l = dict(EVENTS="demo:events_lines", EV_ROUTE="route_id", EV_FROM="pk_from", EV_TO="pk_to",
                EV_OFFSET="offset", EV_SECTION=None, OFFSET_RIGHT=False)
    files["tool_2_02.json"] = {"tool": "2.02", "cases": [
        _case("ledger", "Как во встроенной проверке", {**common, **ev_l, "OUT_M": 0}, l_res),
        _case("ledger_out_m_station", "Пикетаж в M, на уравнении две вершины в одной точке",
              {**common, **ev_l, "OUT_M": 2}, run_events(w, True, out_m=2)),
        _case("ledger_out_m_measure", "Мера по оси в M", {**common, **ev_l, "OUT_M": 1},
              run_events(w, True, out_m=1)),
    ]}
    for num, src in (("3.01", "tool_2_01.json"), ("3.02", "tool_2_02.json")):
        files[f"tool_{num.replace('.', '_')}.json"] = {
            "tool": num, "about": "Динамический слой считается тем же инструментом при каждой "
                                 f"правке, ожидаемые слои те же, что в {src}",
            "same_as": src, "cases": []}

    files["tool_4_01.json"] = {"tool": "4.01", "cases": [
        _case("ledger_100", "Шаг 100 м с ведомостью", {**common, "STEP": 100.0, "OUT_M": 0},
              run_pickets(w)),
        _case("ledger_500_station", "Шаг 500 м, пикетаж в M", {**common, "STEP": 500.0, "OUT_M": 2},
              run_pickets(w, step=500.0, out_m=2)),
        _case("length_100", "Без ведомости, пикетаж по длине", {**ROUTE_PARAMS, **CHAIN_PARAMS,
                                                                "STEP": 100.0, "OUT_M": 0},
              run_pickets(w, ledger=False)),
    ]}
    files["tool_4_02.json"] = {"tool": "4.02", "cases": [
        _case("radius_50", "Дефекты примера, радиус 50 м",
              {**common, "POINTS": "demo:defects", "PT_ROUTE": None, "RADIUS": 50.0}, loc_res),
        _case("radius_5", "Радиус 5 м, дальние дефекты уходят в ошибки",
              {**common, "POINTS": "demo:defects", "PT_ROUTE": None, "RADIUS": 5.0}, run_locate(w, 5.0)),
    ]}
    t_vert, _ = run_profile_table(w, picket_step=0.0, step=0.0, vertices=1, rasters=False, pois=False,
                                  route_list=["R1", "R3"])
    files["tool_5_01.json"] = {"tool": "5.01", "cases": [
        _case("demo", "Как во встроенной проверке, растр - рельеф примера",
              {**common, "ROUTE_LIST": None, "RASTERS": ["demo:dem"], "BAND": 1, "PICKET_STEP": 100.0,
               "STEP": 50.0, "VERTICES": 0, "POIS": "demo:defects", "POI_LABEL": "did",
               "CORRIDOR": 5.0}, table),
        _case("all_vertices", "Маршруты R1 и R3, только начало, конец, уравнения и все вершины, "
                              "без растров",
              {**common, "ROUTE_LIST": "R1,R3", "RASTERS": None, "BAND": 1, "PICKET_STEP": 0.0,
               "STEP": 0.0, "VERTICES": 1, "POIS": None, "CORRIDOR": 10.0}, t_vert),
    ]}
    drawing = run_profile_drawing(table["OUTPUT"], zf, loc_res["OUTPUT"])
    files["tool_5_02.json"] = {"tool": "5.02", "about": "Координаты чертежа в мм бумаги от начала "
                                                       "сетки. В слое QGIS к ним прибавляется origin.",
                               "cases": [_case("demo_r1", "Как во встроенной проверке",
                                               {"TABLE": "tool_5_01:demo", "ROUTE": "R1", "GROUND": zf,
                                                "DESIGN": None, "PIPE": None, "D": 0.16, "BASE": 0.3,
                                                "ROWS": "default", "SECTIONS": None,
                                                "PLAN": "tool_4_02:radius_50", "PLAN_LABEL": "did",
                                                "H_SCALE": 500.0, "V_SCALE": 100.0, "HORIZON": None,
                                                "GRADE_TOL": 0.02, "MIN_GAP": 3.0, "ORIGIN": None},
                                               drawing)]}
    for name, data in files.items():
        data.setdefault("generator", "tools/make_fixtures.py")
        data.setdefault("version", _version())
    return files


def _version():
    for line in open(os.path.join(ROOT, "routeliner", "metadata.txt"), encoding="utf-8"):
        if line.startswith("version="):
            return line.split("=", 1)[1].strip()
    return ""


def _clean(v):
    """NaN в JSON не бывает: пустое значение пишется null."""
    if isinstance(v, float):
        return None if v != v else v
    if isinstance(v, np.floating):
        return _clean(float(v))
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


_NUM_LIST = re.compile(r"\[(?:\s*(?:-?\d[\d.eE+-]*|null)\s*,)*\s*(?:-?\d[\d.eE+-]*|null)\s*\]")


def dump(data) -> str:
    """JSON с отступами, но список чисел (точка, вершина) пишется в строку."""
    text = json.dumps(_clean(data), ensure_ascii=False, indent=1, allow_nan=False)
    return _NUM_LIST.sub(lambda mo: re.sub(r"\s+", "", mo.group(0)).replace(",", ", "), text) + "\n"


def main(argv):
    old = i18n._LANG
    try:
        files = build_all()
    finally:
        i18n._LANG = old
    os.makedirs(OUT_DIR, exist_ok=True)
    bad = []
    for name, data in files.items():
        path = os.path.join(OUT_DIR, name)
        text = dump(data)
        if "--check" in argv:
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
                bad.append(name)
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"{name}  {len(text) // 1024} КБ")
    if "--check" in argv:
        print("фикстуры совпадают с кодом" if not bad else "устарели: " + ", ".join(bad))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
