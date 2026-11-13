"""tools/tools.json совпадает с кодом модуля.

Файл описывает инструменты для расширения Routeliner в RustGIS. Если тест
упал, код инструментов поменялся, и файл надо пересобрать командой
python tools/make_tools_json.py
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_tools_json as M  # noqa: E402


def test_tools_json_matches_code():
    with open(M.OUT, encoding="utf-8") as f:
        on_disk = f.read()
    assert on_disk == M.dump(M.build()), "tools.json устарел: python tools/make_tools_json.py"


def test_all_tools_described():
    data = json.loads(M.dump(M.build()))
    numbers = [t["number"] for t in data["tools"]]
    assert numbers == ["1.01", "1.02", "1.03", "2.01", "2.02", "3.01", "3.02",
                       "4.01", "4.02", "5.01", "5.02"]
    for t in data["tools"]:
        assert t["parameters"], t["number"]
        names = [p["name"] for p in t["parameters"]]
        assert len(names) == len(set(names)), t["number"]


def test_result_fields_and_codes():
    data = json.loads(M.dump(M.build()))
    tools = {t["number"]: t for t in data["tools"]}
    out = {s["name"]: s for s in tools["2.01"]["sinks"]}
    names = [f.get("name") for f in out["OUTPUT"]["fields"]]
    assert names == [None, "rl_m", "rl_pk", "rl_x", "rl_y", "rl_azimuth"]
    assert out["OUTPUT"]["fields"][0] == {"source_fields": "EVENTS"}
    assert [f["name"] for f in out["ERRORS"]["fields"][1:]] == ["rl_route", "rl_error", "rl_message"]
    from routeliner.core.errors import ErrorCode
    assert [c["value"] for c in data["error_codes"]] == [c.value for c in ErrorCode]
    assert all(c["raised_in"] for c in data["error_codes"])
