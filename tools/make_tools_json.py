"""Сборка tools/tools.json - машинного описания инструментов Routeliner.

Источник - сам код модуля, ничего не переписывается руками.
- Параметры и выходы: initAlgorithm каждого инструмента вызывается
  с заглушкой qgis (tools/qgis_stub.py), записанные параметры
  переводятся в JSON.
- Поля результата: разбор processAlgorithm (ast). Поля задаются
  вызовами fld(имя, тип) внутри fields_of, слой результата -
  parameterAsSink, таблица ошибок - write_errors.
- Коды ошибок: перечисление ErrorCode и места в ядре, где код ставится.
- Постоянные ядра, от которых зависят числа результата.

Запуск из корня репозитория:
    python tools/make_tools_json.py          пересобрать tools/tools.json
    python tools/make_tools_json.py --check  сверить файл с кодом
Тест tests/core/test_tools_json.py делает то же, что --check.
"""
from __future__ import annotations

import ast
import glob
import inspect
import json
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "tools.json")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from qgis_stub import Call, Sym, stubbed_qgis  # noqa: E402

FORMAT = 1
TYPES = {"T_STR": "string", "T_DBL": "double", "T_INT": "int"}
QT_TYPES = {"QString": "string", "Double": "double", "Int": "int"}

# Порядок аргументов конструкторов параметров Processing (API QGIS)
SIGNATURES = {
    "QgsProcessingParameterFeatureSource": ("name", "description", "types", "defaultValue", "optional"),
    "QgsProcessingParameterField": ("name", "description", "defaultValue", "parentLayerParameterName",
                                    "type", "allowMultiple", "optional"),
    "QgsProcessingParameterNumber": ("name", "description", "type", "defaultValue", "optional",
                                     "minValue", "maxValue"),
    "QgsProcessingParameterBoolean": ("name", "description", "defaultValue", "optional"),
    "QgsProcessingParameterEnum": ("name", "description", "options", "allowMultiple", "defaultValue",
                                   "optional"),
    "QgsProcessingParameterString": ("name", "description", "defaultValue", "multiLine", "optional"),
    "QgsProcessingParameterFeatureSink": ("name", "description", "type", "defaultValue", "optional"),
    "QgsProcessingParameterMultipleLayers": ("name", "description", "layerType", "defaultValue",
                                             "optional"),
    "QgsProcessingParameterMatrix": ("name", "description", "numberRows", "hasFixedNumberRows",
                                     "headers", "defaultValue", "optional"),
    "QgsProcessingParameterPoint": ("name", "description", "defaultValue", "optional"),
    "QgsProcessingParameterFolderDestination": ("name", "description", "defaultValue", "optional"),
    "QgsProcessingOutputString": ("name", "description"),
    "QgsProcessingOutputBoolean": ("name", "description"),
}


def _bi(ru):
    """Строка интерфейса на двух языках: исходник и перевод из словаря."""
    from routeliner.translations import TRANSLATIONS
    return {"ru": ru, "en": TRANSLATIONS.get(ru, ru)}


def _plain(v):
    if isinstance(v, Sym):
        return v.leaf
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    return v


def _args(call):
    names = SIGNATURES[call._path]
    out = dict(zip(names, call.args))
    out.update(call.kwargs)
    return out


# ============================================================ параметры
def param_json(call, extra_values):
    a = _args(call)
    kind = call._path.replace("QgsProcessingParameter", "").replace("QgsProcessingOutput", "")
    p = {"name": a["name"], "type": kind[0].lower() + kind[1:], "description": _bi(a["description"])}
    if kind == "Number":
        p["number_type"] = _plain(a.get("type", "Integer")) or "Integer"
        for k in ("minValue", "maxValue"):
            if a.get(k) is not None:
                p[k] = a[k]
    elif kind == "Enum":
        p["options"] = [_bi(o) for o in a["options"]]
        if a["name"] in extra_values:
            p["values"] = extra_values[a["name"]]
    elif kind == "Field":
        p["parent"] = a.get("parentLayerParameterName")
        p["field_type"] = _plain(a.get("type", "Any"))
    elif kind == "FeatureSource":
        p["geometry"] = _plain(a.get("types", []))
    elif kind == "FeatureSink":
        p["geometry"] = _plain(a.get("type"))
    elif kind == "MultipleLayers":
        p["layer_type"] = _plain(a.get("layerType"))
    elif kind == "Matrix":
        p["headers"] = [_bi(h) for h in a.get("headers", [])]
        p["fixed_rows"] = bool(a.get("hasFixedNumberRows"))
        n = len(p["headers"])
        rows = a.get("defaultValue") or []
        p["default"] = [rows[k:k + n] for k in range(0, len(rows), n)]
    if call._path.startswith("QgsProcessingParameter"):
        if kind != "Matrix":
            d = a.get("defaultValue")
            # строковое значение по умолчанию у NAME - слово интерфейса
            p["default"] = _bi(d) if kind == "String" and isinstance(d, str) and d else d
        p["optional"] = bool(a.get("optional", False))
        p["advanced"] = "Advanced" in call.flag_text
    return p


# ============================================================ поля результата
class _Line(ast.NodeTransformer):
    """Оставляет ветку if self.LINE, нужную этому классу."""

    def __init__(self, line):
        self.line = line

    def _test(self, node):
        t = node.test
        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self" \
                and t.attr == "LINE":
            return self.line
        return None

    def visit_If(self, node):
        v = self._test(node)
        self.generic_visit(node)
        if v is None:
            return node
        return (node.body if v else node.orelse) or ast.Pass()

    def visit_IfExp(self, node):
        v = self._test(node)
        self.generic_visit(node)
        if v is None:
            return node
        return node.body if v else node.orelse


def _method_tree(cls, name):
    for k in cls.__mro__:
        if name in k.__dict__:
            fn = inspect.unwrap(k.__dict__[name])
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
            return _Line(bool(getattr(cls, "LINE", False))).visit(tree)
    return None


def _assigns(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            out.setdefault(node.targets[0].id, []).append(node.value)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple):
            for t in node.targets[0].elts:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(None)
    return out


def _fname(node):
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _source_param(node, assigns):
    """X.fields(), где X = self.parameterAsSource(parameters, "ИМЯ", context)."""
    if isinstance(node, ast.Call) and _fname(node) == "fields" and isinstance(node.func.value, ast.Name):
        for v in assigns.get(node.func.value.id, []):
            if isinstance(v, ast.Call) and _fname(v) == "parameterAsSource":
                return v.args[1].value
    return None


def _field(call):
    return {"name": call.args[0].value, "type": TYPES[call.args[1].id]}


def _const_list(name, assigns):
    for v in assigns.get(name, []):
        if isinstance(v, ast.List):
            return [e.value if isinstance(e, ast.Constant) else e.id for e in v.elts]
    raise ValueError(name)


def _expand(node, assigns):
    """Список полей из выражения: fields_of(...), имя переменной, X.fields()."""
    if node is None:
        return []
    if isinstance(node, ast.Call) and _fname(node) == "fields_of":
        out = []
        for a in node.args:
            out += _expand(a, assigns)
        return out
    if isinstance(node, ast.Call) and _fname(node) == "fld":
        return [_field(node)]
    if isinstance(node, ast.Starred):
        return _expand(node.value, assigns)
    if isinstance(node, ast.List):
        out = []
        for e in node.elts:
            out += _expand(e, assigns)
        return out
    if isinstance(node, ast.ListComp):
        it = node.generators[0].iter
        if isinstance(it, ast.Call) and _fname(it) == "zip":
            names = _const_list(it.args[0].id, assigns)
            types_ = _const_list(it.args[1].id, assigns)
            return [{"name": n, "type": TYPES[t]} for n, t in zip(names, types_)]
        return [{"dynamic": ast.unparse(node), "type": TYPES[node.elt.args[1].id]}]
    src = _source_param(node, assigns)
    if src:
        return [{"source_fields": src}]
    if isinstance(node, ast.Name):
        for v in assigns.get(node.id, []):
            if v is not None:
                return _expand(v, assigns)
    raise ValueError(ast.unparse(node))


def _wkb(node, assigns):
    """Типы геометрии слоя, первым - тип при параметрах по умолчанию."""
    if isinstance(node, ast.IfExp):
        return list(dict.fromkeys(_wkb(node.orelse, assigns) + _wkb(node.body, assigns)))
    names = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in assigns and n is node:
            for v in assigns[n.id]:
                names += _wkb(v, assigns)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) and n.value.attr == "WkbType":
            names.append(n.attr)
    return list(dict.fromkeys(names))


def _alias(name, own):
    from routeliner.core.aliases import alias_source, is_raster_field
    src = alias_source(name, own)
    if src is None:
        return None
    a = _bi(src)
    if is_raster_field(name):
        a = {k: v.format(name=name[2:]) for k, v in a.items()}
    return a


def _decorate(fields):
    own = not any("source_fields" in f for f in fields)
    for f in fields:
        if "name" in f:
            a = _alias(f["name"], own)
            if a:
                f["alias"] = a
    return fields


def sinks_of(cls):
    from routeliner.processing.common import ERROR_FIELDS
    tree = _method_tree(cls, "processAlgorithm")
    assigns = _assigns(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _fname(node)
        if name == "parameterAsSink":
            sink = node.args[1].value
            fields = _expand(node.args[3], assigns)
            out.append({"name": sink, "geometry": _wkb(node.args[4], assigns),
                        "fields": _decorate(fields)})
        elif name == "write_errors":
            fields = _expand(node.args[2], assigns) + \
                [{"name": n, "type": QT_TYPES[t.leaf]} for n, t in ERROR_FIELDS]
            out.append({"name": "ERRORS", "geometry": ["NoGeometry"], "fields": _decorate(fields)})
    order = {"OUTPUT": 0, "LINES": 1, "TEXTS": 2, "ERRORS": 9}
    return sorted(out, key=lambda s: order.get(s["name"], 5))


def demo_layers(cls):
    """Слои GeoPackage примера 1.01: _memory(геометрия, поля, имя) и _write."""
    tree = _method_tree(cls, "processAlgorithm")
    assigns = _assigns(tree)
    mem = {}
    for var, vals in assigns.items():
        for v in vals:
            if isinstance(v, ast.Call) and _fname(v) == "_memory":
                mem[var] = v
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _fname(node) == "_write":
            m = mem[node.args[0].id]
            out.append({"layer": node.args[2].value, "geometry": m.args[0].value,
                        "fields": _decorate(_expand(m.args[1], assigns))})
    return out


def returns_of(cls):
    tree = _method_tree(cls, "processAlgorithm")
    keys = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            keys += [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    return list(dict.fromkeys(keys))


# ============================================================ коды ошибок
def error_codes():
    from routeliner.core.errors import ErrorCode
    where = {c.name: [] for c in ErrorCode}
    for path in sorted(glob.glob(os.path.join(ROOT, "routeliner", "core", "*.py"))):
        tree = ast.parse(open(path, encoding="utf-8").read())
        mod = os.path.splitext(os.path.basename(path))[0]
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                        and n.value.id == "ErrorCode" and n.attr in where:
                    ref = f"core/{mod}.py:{fn.name}"
                    if ref not in where[n.attr]:
                        where[n.attr].append(ref)
    return [{"name": c.name, "value": c.value, "raised_in": where[c.name]} for c in ErrorCode]


# ============================================================ постоянные
def constants():
    from routeliner.core import assembler, chainage, demo, profile, route
    from routeliner.layers import route_source
    from routeliner.processing import common
    from routeliner.processing.alg_profile import MATRIX_HEADERS, TEMPLATE_PIPE  # noqa: F401
    asm = inspect.signature(assembler.RouteAssembler.__init__).parameters
    pd = profile.ProfileDrawer
    return {
        "rounding": {"meters_decimals": common.DEC_M, "degrees_decimals": common.DEC_DEG},
        "route_eps": route.EPS,
        "chainage_eps": chainage.EPS,
        "chainage_scale_tol": chainage.SCALE_TOL,
        "assembler_defaults": {k: v.default for k, v in asm.items() if k != "self"},
        "curve_segmentation_max_angle_deg": route_source.CURVE_ANGLE_DEG,
        "offset_miter_limit": inspect.signature(route.offset_polyline).parameters["miter_limit"].default,
        "station_formats": [{"value": f.value, "label": _bi(d)} for f, d in common.FORMATS],
        "out_m": [_bi(d) for d in common.OUT_M],
        "profile": {
            "point_priority": profile.PRIORITY,
            "merge_tol": profile.MERGE_TOL,
            "row_types": list(profile.ROW_TYPES),
            "palette": profile.PALETTE,
            "drawer": {k: getattr(pd, k) for k in ("HEADER", "GAP", "TEXT", "TITLE", "GRADE_FULL")},
        },
        "demo": {"crs": demo.CRS, "origin": [demo.X0, demo.Y0], "system": demo.SYSTEM,
                 "dem_extent": list(demo.DEM_EXTENT), "dem_cell": demo.DEM_CELL},
        "groups": {k: _bi(v) for k, v in common.GROUPS.items()},
    }


# ============================================================ сборка
def build() -> dict:
    from routeliner import i18n
    old = i18n._LANG
    i18n.set_language("ru")
    try:
        with stubbed_qgis():
            return _build()
    finally:
        i18n._LANG = old


def _build() -> dict:
    from routeliner.processing import common
    from routeliner.processing.alg_profile import VERTEX_MODES
    from routeliner.processing.provider import RoutelinerProvider

    prov = RoutelinerProvider()
    prov.loadAlgorithms()
    extra = {"FORMAT": [f.value for f, _ in common.FORMATS],
             "VERTICES": [k for k, _ in VERTEX_MODES]}
    tools = []
    for alg in prov.algs:
        cls = type(alg)
        alg.initAlgorithm()
        params = [param_json(p, extra) for p in alg._params]
        t = {
            "number": cls.NUMBER,
            "id": alg.name(),
            "processing_id": "routeliner:" + alg.name(),
            "group": cls.GROUP,
            "title": _bi(cls.TITLE),
            "no_threading": "NoThreading" in repr(alg.flags()),
            "parameters": [p for p in params if p["type"] != "featureSink"],
            "outputs": [{"name": o.args[0], "type": o._path.replace("QgsProcessingOutput", "").lower(),
                         "description": _bi(o.args[1])} for o in alg._outputs],
        }
        target = getattr(cls, "TARGET", "")
        if target:
            t["computes_like"] = next(type(a).NUMBER for a in prov.algs if a.name() == target)
            t["result"] = "Динамический слой в памяти проекта с полями инструмента " + t["computes_like"]
        elif cls.NUMBER == "1.01":
            from routeliner.processing import alg_demo
            t["result_files"] = {"gpkg": alg_demo.GPKG, "dem": alg_demo.DEM,
                                 "csv": "events_points.csv"}
            t["layers"] = demo_layers(cls)
            t["returns"] = returns_of(cls)
        else:
            sinks = {p["name"]: p for p in params if p["type"] == "featureSink"}
            t["sinks"] = []
            for s in sinks_of(cls):
                d = sinks.get(s["name"], {})
                t["sinks"].append({"name": s["name"], "description": d.get("description"),
                                   "optional": d.get("optional", False), **s})
            t["returns"] = returns_of(cls)
        tools.append(t)
    return {
        "format": FORMAT,
        "plugin": "Routeliner",
        "version": common.version(),
        "provider": prov.id(),
        "note": "Собрано tools/make_tools_json.py из кода модуля, после правки инструментов пересобрать.",
        "error_codes": error_codes(),
        "constants": constants(),
        "tools": tools,
    }


def dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    text = dump(build())
    if "--check" in argv:
        with open(OUT, encoding="utf-8") as f:
            same = f.read() == text
        print("tools.json совпадает с кодом" if same else "tools.json устарел, пересоберите")
        return 0 if same else 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"записан {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
