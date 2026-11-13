"""Прогоны инструментов в формате rustgis-kit: fixtures/tool_runs.json.

Граница между модулем и расширением RustGIS. Формат тот же, что у
Isoliner3D (tools/make_fixtures.py там), README крейта rustgis-kit.

Прогон - {"tool", "case", "values", "input", "output", "report",
"tolerance"}.
- values - значения полей, не слоёв, со значениями по умолчанию из
  fixtures/tools.json, и сведения о слоях "@КЛЮЧ" = {"name", "geometry",
  "hasz", "fields", "numeric"}.
- input - слои. Линии - [{"id", "parts": [[[x, y, z]]], "attrs"}],
  точки и таблицы - [{"id", "xyz": [x, y, z] | null, "attrs"}]. id - номер
  объекта в GeoPackage примера, Z нет - null.
- output - выход по ключу: {"geometry", "keep_source", "fields":
  [[имя, тип]], "features": [{"source", "values", "geometry"}]}.
  Геометрия точки - {"xyz"}, линии - {"points"}, мультилинии (участок
  через разрыв при ALLOW_GAPS) - {"parts": [точки куска]}, объекта входа -
  {"source": id}, строки таблицы - null. M-значения результата (OUT_M)
  идут членом "measure" - число у точки, список у линии, у мультилинии
  список по кускам. Имя "m" занято крейтом, там он хранит метры UTM.
  Слой RustGIS держит только X и Y, поэтому M в проект не попадает.

Расчёт - тот же, что в tools/make_fixtures.py (ядро без QGIS), только
геометрия пишется целиком. Чего нет в прогонах и почему - в "skipped".

Запуск из корня репозитория.
    python tools/make_tool_runs.py          пересобрать
    python tools/make_tool_runs.py --check  сверить с кодом
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "fixtures", "tool_runs.json")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import export_tools  # noqa: E402
import make_fixtures as F  # noqa: E402

TOL = {"xy": 1e-6, "m": 1e-6, "fields": 1e-9}
# Дуга R2 здесь режется через 0,5° на хорду (181 вершина вместо 4501 у QGIS
# при 0,02°): иначе одна дуга в каждом прогоне дала бы файл в 7 МБ. Расширение
# сверяется с ядром на том же входе, поэтому нарезка на сверку не влияет.
ARC_ANGLE_DEG = 0.5
SKIPPED = [
    {"tool": "demo", "why": "1.01 пишет папку с GeoPackage и растром, у крейта нет поля папки "
                            "и выхода набором слоёв. Итог проверки примера лежит в "
                            "tests/fixtures/tool_1_01.json"},
    {"tool": "live_point_events", "why": "3.01 - динамический слой проекта QGIS, считается "
                                         "инструментом 2.01, его прогоны те же"},
    {"tool": "live_line_events", "why": "3.02 - динамический слой проекта QGIS, считается "
                                        "инструментом 2.02, его прогоны те же"},
    {"tool": "point_events", "case": "by_m", "why": "Пикетаж из M, у слоя крейта M нет. "
                                                    "Прогон лежит в tests/fixtures/tool_2_01.json"},
    {"tool": "profile_table", "case": "demo", "why": "Растр на входе, у крейта нет вида raster. "
                                                     "Прогон с растром лежит в tests/fixtures/tool_5_01.json, "
                                                     "здесь тот же случай без растра"},
]


# ============================================================ слои входа
def _z(v):
    return None if v is None or v != v else float(v)


def layer_routes(w):
    return [{"id": r["fid"], "attrs": {"route_id": r["route_id"], "name": r["name"]},
             "parts": [[[p[0], p[1], _z(p[2])] for p in part] for part in r["parts"]]}
            for r in w.tables["routes"]]


def layer_table(rows, id_key=None, xy=False):
    out = []
    for i, r in enumerate(rows, 1):
        attrs = {k: v for k, v in r.items() if k not in ("x", "y", "geometry", "key")}
        xyz = [r["x"], r["y"], None] if xy else None
        if "geometry" in r:
            xyz = [r["geometry"][0], r["geometry"][1], None]
        out.append({"id": r[id_key] if id_key else i, "xyz": xyz, "attrs": attrs})
    return out


def info(name, geometry, items, hasz=False):
    fields = list(items[0]["attrs"]) if items else []
    numeric = [k for k in fields if any(isinstance(it["attrs"].get(k), (int, float))
                                        and not isinstance(it["attrs"].get(k), bool) for it in items)]
    return {"name": name, "geometry": geometry, "hasz": hasz, "fields": fields, "numeric": numeric}


# ============================================================ выходы
def _line_geom(g):
    """g - куски [[x, y(, m)]] из make_fixtures.geom_line."""
    pts = [[[p[0], p[1], None] for p in piece] for piece in g]
    ms = [[p[2] for p in piece] for piece in g] if g and g[0] and len(g[0][0]) > 2 else None
    out = {"points": pts[0]} if len(pts) == 1 else {"parts": pts}
    if ms is not None:
        out["measure"] = ms[0] if len(ms) == 1 else ms
    return out


def _point_geom(g):
    out = {"xyz": [g[0], g[1], None]}
    if len(g) > 2:
        out["measure"] = g[2]
    return out


def sink(tool_sinks, key, rows, kind, keep=None, source_geom=False):
    # поля записи источника (@КЛЮЧ) даёт keep_source, полей растров z_* без растров нет
    fields = [f for f in tool_sinks[key]["fields"] if not f[0].startswith("@") and f[0] != "z_*"]
    names = [f[0] for f in fields]
    feats = []
    for r in rows:
        vals = [r.get(n) for n in names]
        if kind == "none":
            g = None
        elif source_geom:
            g = {"source": r["key"]}
        elif kind == "line":
            g = _line_geom(r["geometry"])
        else:
            g = _point_geom(r["geometry"])
        f = {"values": vals, "geometry": g}
        if keep and r.get("key") is not None:
            f = {"source": r["key"], **f}
        feats.append(f)
    out = {"geometry": "source" if source_geom else kind, "fields": fields, "features": feats}
    if keep:
        out = {"keep_source": keep, **out}
    return out


def errors_sink(rows, keep=None):
    fields = [["rl_route", "string"], ["rl_error", "string"], ["rl_message", "string"]]
    feats = []
    for e in rows:
        f = {"values": [e["rl_route"], e["rl_error"], e["rl_message"]], "geometry": None}
        if keep and e["key"] is not None:
            f = {"source": e["key"], **f}
        feats.append(f)
    out = {"geometry": "none", "fields": fields, "features": feats}
    return {"keep_source": keep, **out} if keep else out


# ============================================================ сборка
def build() -> dict:
    F.GEOM_FULL = 10 ** 9            # геометрия целиком
    F._load_helpers()
    F.i18n.set_language("ru")
    F.ARC_ANGLE_DEG = ARC_ANGLE_DEG
    try:
        w = F.World()
    finally:
        F.ARC_ANGLE_DEG = F.CURVE_ANGLE_DEG
    cat = {t["name"]: t for t in export_tools.build()["tools"]}
    routes_in = layer_routes(w)
    layers = {
        "demo:routes": ("routes", "line", routes_in, True),
        "demo:ledger": ("ledger", "none", layer_table(w.tables["ledger"]), False),
        "demo:events_points": ("events_points", "none",
                               layer_table(w.tables["events_points"], "eid"), False),
        "demo:events_lines": ("events_lines", "none", layer_table(w.tables["events_lines"], "eid"), False),
        "demo:defects": ("defects", "point", layer_table(w.tables["defects"], "did", xy=True), False),
    }
    runs = []

    def run(tool, case, params, outputs):
        t = cat[tool]
        sinks = {p["key"]: p for p in t["params"] if p["kind"] == "sink"}
        values, inputs = {}, {}
        for p in t["params"]:
            k = p["key"]
            v = params.get(k, p.get("default"))
            if p["kind"] in ("lines", "points", "table"):
                if v is None:
                    continue
                name, geom, data, hasz = layers[v] if isinstance(v, str) else v
                inputs[k] = data
                values["@" + k] = info(name, geom, data, hasz)
            elif p["kind"] == "sink":
                if p.get("optional"):
                    values[k] = k in outputs
            elif p["kind"] == "field":
                values[k] = v or ""
            elif p["kind"] == "raster":
                continue
            elif v is not None:
                values[k] = v
        out = {}
        for key, (rows, kind, keep, src) in outputs.items():
            out[key] = errors_sink(rows, keep) if key == "ERRORS" else \
                sink(sinks, key, rows, kind, keep, src)
        runs.append({"tool": tool, "case": case, "values": values, "input": inputs,
                     "output": out, "report": [], "tolerance": TOL})

    common = {**F.ROUTE_PARAMS, **F.CHAIN_PARAMS, **F.LEDGER_PARAMS}
    # 1.02
    for case, kw, params in (("default", {}, {}), ("allow_gaps", {"allow_gaps": True}, {"ALLOW_GAPS": True}),
                             ("reverse", {"reverse": True}, {"REVERSE": True})):
        r = F.run_check_routes(w, **kw)
        run("check_routes", case, {**F.ROUTE_PARAMS, **params},
            {"OUTPUT": (r["OUTPUT"], "line", None, False), "ERRORS": (r["ERRORS"], "none", None, False)})
    # 1.03
    routes, rerr = w.routes()
    for case, kw, params in (("ledger_station", {}, {"OUT_M": 2}), ("ledger_measure", {"out_m": 1}, {"OUT_M": 1})):
        r, _ = F.calibrate(w, routes, rerr, **kw)
        run("calibrate_routes", case, {**common, **params},
            {"OUTPUT": (r["OUTPUT"], "line", None, False), "ERRORS": (r["ERRORS"], "none", None, False)})
    control = [{"key": f["did"], "x": f["x"], "y": f["y"], "station": f["exp_station"]}
               for f in w.tables["defects"]]
    r, _ = F.calibrate(w, routes, rerr, ledger=False, fmt=3, control=control, radius=10.0)
    run("calibrate_routes", "control_points",
        {**F.ROUTE_PARAMS, **F.CHAIN_PARAMS, "FORMAT": 3, "CONTROL": "demo:defects",
         "CT_STATION": "exp_station", "CT_RADIUS": 10.0, "OUT_M": 2},
        {"OUTPUT": (r["OUTPUT"], "line", None, False), "ERRORS": (r["ERRORS"], "none", None, False)})
    # 2.01
    ev_p = dict(EVENTS="demo:events_points", EV_ROUTE="route_id", EV_FROM="pk", EV_OFFSET="offset",
                EV_SECTION="section")
    for case, kw, params in (("ledger", {}, {}), ("ledger_out_m_station", {"out_m": 2}, {"OUT_M": 2}),
                             ("offset_right", {"offset_right": True}, {"OFFSET_RIGHT": True})):
        r = F._strip(F.run_events(w, False, **kw))
        run("point_events", case, {**common, **ev_p, **params},
            {"OUTPUT": (r["OUTPUT"], "point", "EVENTS", False), "ERRORS": (r["ERRORS"], "none", "EVENTS", False)})
    # 2.02
    ev_l = dict(EVENTS="demo:events_lines", EV_ROUTE="route_id", EV_FROM="pk_from", EV_TO="pk_to",
                EV_OFFSET="offset")
    for case, kw, params in (("ledger", {}, {}), ("ledger_out_m_station", {"out_m": 2}, {"OUT_M": 2}),
                             ("ledger_out_m_measure", {"out_m": 1}, {"OUT_M": 1})):
        r = F.run_events(w, True, **kw)
        run("line_events", case, {**common, **ev_l, **params},
            {"OUTPUT": (r["OUTPUT"], "line", "EVENTS", False), "ERRORS": (r["ERRORS"], "none", "EVENTS", False)})
    # 4.01
    for case, kw, params, base in (("ledger_100", {}, {"STEP": 100.0}, common),
                                   ("ledger_500_station", {"step": 500.0, "out_m": 2},
                                    {"STEP": 500.0, "OUT_M": 2}, common),
                                   ("length_100", {"ledger": False}, {"STEP": 100.0},
                                    {**F.ROUTE_PARAMS, **F.CHAIN_PARAMS})):
        r = F.run_pickets(w, **kw)
        run("pickets", case, {**base, **params}, {"OUTPUT": (r["OUTPUT"], "point", None, False)})
    # 4.02
    located = None
    for case, radius in (("radius_50", 50.0), ("radius_5", 5.0)):
        r = F.run_locate(w, radius)
        located = located or r["OUTPUT"]
        run("locate_points", case, {**common, "POINTS": "demo:defects", "RADIUS": radius},
            {"OUTPUT": (r["OUTPUT"], "point", "POINTS", True), "ERRORS": (r["ERRORS"], "none", "POINTS", False)})
    # 5.01 без растра
    p51 = {**common, "PICKET_STEP": 100.0, "STEP": 50.0, "VERTICES": 0, "POIS": "demo:defects",
           "POI_LABEL": "did", "CORRIDOR": 5.0}
    t_plain, _ = F.run_profile_table(w, rasters=False)
    run("profile_table", "demo_no_raster", p51, {"OUTPUT": (t_plain["OUTPUT"], "point", None, False)})
    t_vert, _ = F.run_profile_table(w, picket_step=0.0, step=0.0, vertices=1, rasters=False, pois=False,
                                    route_list=["R1", "R3"])
    run("profile_table", "all_vertices", {**common, "ROUTE_LIST": "R1,R3", "PICKET_STEP": 0.0, "STEP": 0.0,
                                          "VERTICES": 1}, {"OUTPUT": (t_vert["OUTPUT"], "point", None, False)})
    # 5.02: таблица 5.01 с растром рельефа - таблица на входе, растр в ней уже снят
    table, zf = F.run_profile_table(w)
    d = F.run_profile_drawing(table["OUTPUT"], zf, located)
    ox, oy = d["origin"]
    tab_in = layer_table(table["OUTPUT"])
    plan_in = [{"id": p["key"], "xyz": [p["geometry"][0], p["geometry"][1], None],
                "attrs": {"did": p["key"], **{k: v for k, v in p.items() if k.startswith("rl_")}}}
               for p in located]
    lines = [{"values": [ln["kind"], ln["row"], ln["color"], ln["width"]],
              "geometry": {"points": [[ox + x, oy + y, None] for x, y in ln["geometry"]]}}
             for ln in d["LINES"]]
    texts = [{"values": [t["text"], t["kind"], t["rot"], t["size"], t["halign"], t["valign"]],
              "geometry": {"xyz": [ox + t["geometry"][0], oy + t["geometry"][1], None]}} for t in d["TEXTS"]]
    t52 = cat["profile_drawing"]
    s52 = {p["key"]: p for p in t52["params"] if p["kind"] == "sink"}
    values = {p["key"]: p.get("default") for p in t52["params"]
              if p["kind"] not in ("table", "points", "sink") and p.get("default") is not None}
    values.update({"ROUTE": "R1", "GROUND": zf, "DESIGN": "", "PIPE": "", "SEC_ROUTE": "", "SEC_FROM": "rl_m_from",
                   "SEC_TO": "rl_m_to", "PLAN_LABEL": "did",
                   "@TABLE": info("profile_table", "point", tab_in), "@PLAN": info("located", "point", plan_in)})
    runs.append({"tool": "profile_drawing", "case": "demo_r1", "values": values,
                 "input": {"TABLE": tab_in, "PLAN": plan_in},
                 "output": {"LINES": {"geometry": "line", "fields": s52["LINES"]["fields"], "features": lines},
                            "TEXTS": {"geometry": "point", "fields": s52["TEXTS"]["fields"], "features": texts}},
                 "returns": {"WIDTH_MM": d["WIDTH_MM"], "HORIZON": d["HORIZON"], "origin": d["origin"]},
                 "report": [], "tolerance": TOL})
    return {"format": 1, "module": "routeliner", "version": F._version(),
            "about": "Пример 1.01 при зерне 1, СК EPSG:32640 (зона UTM 40N), ядро без QGIS. "
                     f"Дуга R2 нарезана через {ARC_ANGLE_DEG} градуса на хорду, поэтому числа "
                     "по R2 расходятся с эталоном примера на миллиметры. Прогоны с нарезкой "
                     "QGIS - tests/fixtures",
            "skipped": SKIPPED, "runs": runs}


def dump(data) -> str:
    return F.dump(data)


def main(argv):
    old = F.i18n._LANG
    try:
        text = dump(build())
    finally:
        F.i18n._LANG = old
    if "--check" in argv:
        same = os.path.exists(OUT) and open(OUT, encoding="utf-8").read() == text
        print("fixtures/tool_runs.json совпадает с кодом" if same else "fixtures/tool_runs.json устарел")
        return 0 if same else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"записан {OUT}, прогонов {len(json.loads(text)['runs'])}, {len(text) // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
