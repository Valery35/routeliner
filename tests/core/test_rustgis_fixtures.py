"""fixtures/tools.json и fixtures/tool_runs.json совпадают с кодом.

Это граница между модулем и расширением Routeliner для RustGIS, формат
крейта rustgis-kit. Если тест упал, пересоберите файлы командами
python tools/export_tools.py и python tools/make_tool_runs.py
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(__file__))

import export_tools  # noqa: E402
import make_tool_runs  # noqa: E402
from test_fixtures import _same  # noqa: E402

KINDS = {"lines", "points", "table", "field", "string", "bool", "number", "integer", "enum",
         "sink", "raster", "matrix", "point", "folder"}


def test_tools_json_matches_code():
    with open(export_tools.OUT, encoding="utf-8") as f:
        assert f.read() == export_tools.dump(export_tools.build()), \
            "fixtures/tools.json устарел: python tools/export_tools.py"


def test_tools_json_is_kit_catalog():
    data = json.loads(export_tools.dump(export_tools.build()))
    assert data["format"] == 1 and data["module"] == "routeliner"
    assert len(data["tools"]) == 11
    for t in data["tools"]:
        assert t["code"] and t["name"] and t["title"]["ru"] and t["title"]["en"]
        assert t["help"]["ru"] and t["help"]["en"]
        for p in t["params"]:
            assert p["kind"] in KINDS, (t["code"], p)
            assert p["label"]["ru"] and p["label"]["en"]
            if p["kind"] == "field":
                assert p["parent"]


def test_tool_runs_match_code():
    from routeliner import i18n
    old = i18n._LANG
    try:
        built = json.loads(make_tool_runs.dump(make_tool_runs.build()))
    finally:
        i18n._LANG = old
    with open(make_tool_runs.OUT, encoding="utf-8") as f:
        _same(json.load(f), built, "tool_runs.json")
    names = {t["name"] for t in json.loads(export_tools.dump(export_tools.build()))["tools"]}
    ran = {r["tool"] for r in built["runs"]} | {s["tool"] for s in built["skipped"] if "case" not in s}
    assert ran == names
    for r in built["runs"]:
        for key, out in r["output"].items():
            n = len(out["fields"])
            assert all(len(f["values"]) == n for f in out["features"]), (r["tool"], r["case"], key)
