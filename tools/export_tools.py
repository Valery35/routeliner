"""Описания инструментов в формате rustgis-kit: fixtures/tools.json.

Формат тот же, что у Isoliner3D (toolspec.py, export_tools.py), его
читает catalog крейта rustgis-kit. Источник - tools/tools.json модуля
(make_tools_json.build), то есть сам код инструментов.

Вид поля (kind) по параметру Processing.
- слой линий - lines, слой точек - points, слой любой геометрии или
  таблица - table;
- поле - field (numeric у числового поля), число Double - number,
  Integer - integer, флажок - bool, список - enum, строка - string;
- выход - sink, у него поля результата в fields;
- растры 5.01 - raster с multiple, таблица строк 5.02 - matrix,
  точка 5.02 - point, папка 1.01 - folder. Этих видов у крейта нет,
  крейт предлагает инструмент, только если такое поле необязательно.

Справка - текст справки Processing без подвала. Сообщения (messages) -
строки tr() расчёта и ядра, в том числе пояснения ошибок rl_message.
Подстановки в них в фигурных скобках, как в модуле.

Запуск из корня репозитория.
    python tools/export_tools.py          пересобрать fixtures/tools.json
    python tools/export_tools.py --check  сверить с кодом
"""
from __future__ import annotations

import ast
import glob
import inspect
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "fixtures", "tools.json")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import make_tools_json as M  # noqa: E402
from qgis_stub import stubbed_qgis  # noqa: E402

FORMAT = 1


def _kind(p):
    t = p["type"]
    if t == "featureSource":
        g = p.get("geometry") or []
        return "lines" if g == ["VectorLine"] else "points" if g == ["VectorPoint"] else "table"
    if t == "number":
        return "integer" if p.get("number_type") == "Integer" else "number"
    return {"field": "field", "boolean": "bool", "enum": "enum", "string": "string",
            "multipleLayers": "raster", "matrix": "matrix", "point": "point",
            "folderDestination": "folder"}[t]


def _param(p):
    kind = _kind(p)
    out = {"key": p["name"], "kind": kind, "label": p["description"]}
    d = p.get("default")
    if isinstance(d, dict) and "ru" in d:
        d = d["ru"]
    if d is not None:
        out["default"] = d
    if kind == "enum":
        out["options"] = p["options"]
        if "values" in p:
            out["values"] = p["values"]
    if kind == "field":
        out["parent"] = p["parent"]
        if p.get("field_type") == "Numeric":
            out["numeric"] = True
    if "minValue" in p:
        out["minimum"] = p["minValue"]
    if "maxValue" in p:
        out["maximum"] = p["maxValue"]
    if kind == "raster":
        out["multiple"] = True
    if kind == "matrix":
        out["headers"] = p["headers"]
    if p.get("optional"):
        out["optional"] = True
    if p.get("advanced"):
        out["advanced"] = True
    return out


def _sink(s):
    out = {"key": s["name"], "kind": "sink", "label": s["description"]}
    if s.get("optional"):
        out["optional"] = True
    out["geometry"] = s["geometry"][0]
    out["fields"] = [[f["name"], f["type"]] if "name" in f else
                     ["@" + f["source_fields"], "copy"] if "source_fields" in f else
                     ["z_*", f["type"]] for f in s["fields"]]
    return out


def _tr_strings(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "tr" and n.args \
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            out.append(n.args[0].value)
    return out


def _core_messages():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "routeliner", "core", "*.py"))):
        out += _tr_strings(ast.parse(open(path, encoding="utf-8").read()))
    return out


def _class_messages(cls):
    """tr() из методов инструмента, его баз до RoutelinerAlgorithm
    и помощников модуля, которые методы вызывают."""
    from routeliner.processing import common
    out = []
    for k in cls.__mro__:
        if k.__module__.startswith("routeliner.processing") and k is not common.RoutelinerAlgorithm:
            out += _tr_strings(ast.parse(textwrap.dedent(inspect.getsource(k))))
    base = ast.parse(textwrap.dedent(inspect.getsource(common.RoutelinerAlgorithm)))
    for fn in base.body[0].body:
        if isinstance(fn, ast.FunctionDef) and fn.name in ("routes", "locator", "m_systems"):
            out += _tr_strings(fn)
    return out


def _help(cls, tr_table):
    from routeliner.processing import algorithms
    if getattr(cls, "TARGET", ""):
        src = {"point_events": "2.01", "line_events": "2.02"}[cls.TARGET]
        ru = algorithms.LIVE_HELP.format(src=src)
        en = tr_table.get(algorithms.LIVE_HELP, algorithms.LIVE_HELP).format(src=src)
        return {"ru": ru, "en": en}
    parts = (cls.HELP, *cls.HELP_TAIL)
    return {"ru": "\n\n".join(parts), "en": "\n\n".join(tr_table.get(t, t) for t in parts)}


def build() -> dict:
    spec = M.build()
    from routeliner import i18n
    from routeliner.translations import TRANSLATIONS
    old = i18n._LANG
    i18n.set_language("ru")
    try:
        with stubbed_qgis():
            from routeliner.processing.provider import RoutelinerProvider
            prov = RoutelinerProvider()
            prov.loadAlgorithms()
            classes = {type(a).NUMBER: type(a) for a in prov.algs}
            core = _core_messages()
            tools = []
            for t in spec["tools"]:
                cls = classes[t["number"]]
                params = [_param(p) for p in t["parameters"]] + \
                    [_sink(s) for s in t.get("sinks", [])]
                shown = {t["title"]["ru"]}
                for p in params:
                    shown.add(p["label"]["ru"])
                    shown |= {o["ru"] for o in p.get("options", [])}
                msgs = []
                for m in _class_messages(cls) + core:
                    if m not in shown and m not in msgs:
                        msgs.append(m)
                item = {"code": t["number"], "name": t["id"], "title": t["title"],
                        "group": t["number"].split(".")[0], "help": _help(cls, TRANSLATIONS),
                        "params": params,
                        "messages": [{"ru": m, "en": TRANSLATIONS.get(m, m)} for m in msgs]}
                if t.get("computes_like"):
                    item["computes_like"] = t["computes_like"]
                if t.get("outputs"):
                    item["outputs"] = t["outputs"]
                tools.append(item)
    finally:
        i18n._LANG = old
    return {"format": FORMAT, "module": "routeliner", "version": spec["version"],
            "error_codes": [c["value"] for c in spec["error_codes"]], "tools": tools}


def dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    text = dump(build())
    if "--check" in argv:
        same = os.path.exists(OUT) and open(OUT, encoding="utf-8").read() == text
        print("fixtures/tools.json совпадает с кодом" if same else "fixtures/tools.json устарел")
        return 0 if same else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"записан {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
