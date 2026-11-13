"""Эталонные прогоны tests/fixtures совпадают с тем, что считает ядро сейчас.

По этим файлам сверяется расширение Routeliner для RustGIS. Если тест упал
после правки ядра, проверьте, что расчёт поменялся намеренно, и пересоберите
файлы командой python tools/make_fixtures.py

Числа сравниваются с допуском 1e-6 м: другая сборка NumPy может дать
расхождение в последнем знаке.
"""
import json
import math
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_fixtures as F  # noqa: E402

TOL = 1e-6


@pytest.fixture(scope="module")
def built():
    from routeliner import i18n
    old = i18n._LANG
    try:
        return {k: json.loads(F.dump(v)) for k, v in F.build_all().items()}
    finally:
        i18n._LANG = old


def _same(a, b, path="$"):
    if isinstance(a, float) or isinstance(b, float):
        assert isinstance(a, (int, float)) and isinstance(b, (int, float)), path
        assert math.isclose(a, b, rel_tol=1e-9, abs_tol=TOL), (path, a, b)
    elif isinstance(a, dict):
        assert isinstance(b, dict) and list(a) == list(b), path
        for k in a:
            _same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), (path, len(a), len(b) if isinstance(b, list) else b)
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]")
    else:
        assert a == b, (path, a, b)


def test_files_match_core(built):
    names = sorted(n for n in os.listdir(F.OUT_DIR) if n.endswith(".json"))
    assert names == sorted(built)
    for name, data in built.items():
        with open(os.path.join(F.OUT_DIR, name), encoding="utf-8") as f:
            _same(json.load(f), data, name)


def test_demo_check_passes(built):
    """Итог проверки 1.01 по ядру тот же, что даёт модуль в QGIS."""
    c = built["tool_1_01.json"]["cases"][0]["expected"]["check"]
    assert c["routes_not_built"] == ["R4"]
    assert c["points_matched"] == c["points_total"] > 0
    assert c["point_errors_recognized"] == c["point_errors_expected"]
    assert c["calibration"] == {"R1": ["length", 0], "R2": ["length", 0], "R3": ["ledger", 2]}
    assert c["points_by_m_matched"] == c["points_by_m_total"] > 0
    assert c["lines_matched"] == c["lines_total"] and c["line_errors_recognized"] == 1
    assert c["defects_matched"] == c["defects_total"]
    assert c["profile_ground_matched"] == c["profile_ground_total"] == c["profile_points"]
    assert c["profile_axis_r1_matched"] == c["profile_axis_r1_total"] > 0
    assert c["profile_equations_r3"] == 2


def test_every_tool_has_fixture(built):
    numbers = {d["tool"] for d in built.values() if "tool" in d}
    assert numbers == {"1.01", "1.02", "1.03", "2.01", "2.02", "3.01", "3.02",
                       "4.01", "4.02", "5.01", "5.02"}
