import math

import numpy as np
import pytest

from routeliner.core.chainage import ChainageSystem
from routeliner.core.profile import (ProfileDrawer, Row, bilinear, collect_points,
                                     grade_segments, thin)
from routeliner.core.route import RouteGeometry


def plane(x, y):
    return 120.0 + 0.01 * x + 0.02 * y


def grid_of(fn, x0=0.0, y0=1000.0, dx=5.0, dy=-5.0, cols=200, rows=200):
    xc = x0 + (np.arange(cols) + 0.5) * dx
    yc = y0 + (np.arange(rows) + 0.5) * dy
    return fn(xc[None, :], yc[:, None])


# ------------------------------------------------------------ растр
def test_bilinear_exact_on_plane():
    g = grid_of(plane)
    xs = np.array([3.0, 101.7, 512.25, 997.4])
    ys = np.array([999.0, 403.3, 12.8, 555.5])
    assert bilinear(g, 0, 1000, 5, -5, xs, ys) == pytest.approx(plane(xs, ys), abs=1e-9)


def test_bilinear_outside_and_nodata():
    g = grid_of(plane)
    g[100, 100] = -9999
    out = bilinear(g, 0, 1000, 5, -5, [-10, 1100, 503.5], [500, 500, 497.5], nodata=-9999)
    assert math.isnan(out[0]) and math.isnan(out[1])
    assert np.isfinite(out[2])        # три соседние ячейки с данными


# ------------------------------------------------------------ уклоны
def test_grade_segments_find_breaks():
    m = np.arange(0, 301, 10.0)
    z = np.where(m <= 100, 10 + m * 0.02, np.where(m <= 200, 12.0, 12 - (m - 200) * 0.005))
    segs = grade_segments(m, z, 0.01)
    assert [(s.m0, s.m1) for s in segs] == [(0, 100), (100, 200), (200, 300)]
    assert [round(s.grade, 3) for s in segs] == [20.0, 0.0, -5.0]


def test_grade_segments_break_on_nan():
    m = np.arange(0, 50, 10.0)
    z = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    assert [(s.m0, s.m1) for s in grade_segments(m, z)] == [(0, 10), (30, 40)]


# ------------------------------------------------------------ подписи
def test_thin_keeps_priority():
    xs = [0.0, 1.0, 2.0, 4.5, 10.0]
    pr = [1, 5, 1, 1, 6]
    assert list(thin(xs, pr, 3.0)) == [False, True, False, True, True]


# ------------------------------------------------------------ точки профиля
def test_collect_points_pickets_vertices_equations():
    r = RouteGeometry("A", [np.array([[0, 0], [150, 0], [150, 150]])])
    sys = ChainageSystem.from_length("s", r.length)
    pts = collect_points(r, sys, picket_step=100, step=0, events=[(40.0, "кабель")])
    kinds = {round(p.m, 3): p.kind for p in pts}
    assert kinds[0.0] == "start" and kinds[300.0] == "end"
    assert kinds[150.0] == "vertex" and kinds[40.0] == "event"
    assert kinds[100.0] == "picket" and kinds[200.0] == "picket"
    v = [p for p in pts if p.kind == "vertex"][0]
    assert v.turn == pytest.approx(90.0)           # поворот налево
    assert [p.station for p in pts] == pytest.approx([p.m for p in pts])


def test_collect_points_merge_keeps_higher_priority():
    r = RouteGeometry("A", [np.array([[0, 0], [100, 0], [100, 100]])])
    sys = ChainageSystem.from_length("s", r.length)
    pts = collect_points(r, sys, picket_step=100, step=50)
    at100 = [p for p in pts if abs(p.m - 100) < 1e-6]
    assert len(at100) == 1 and at100[0].kind == "picket" and at100[0].turn == pytest.approx(90)


# ------------------------------------------------------------ чертёж
def test_drawer_geometry_in_paper_mm():
    r = RouteGeometry("A", [np.array([[0, 0, 10.0], [200, 0, 12.0]])])
    sys = ChainageSystem.from_length("s", r.length)
    pts = collect_points(r, sys, picket_step=100)
    ms = np.array([p.m for p in pts])
    z = 10 + ms / 100
    dr = ProfileDrawer(pts, [f"{p.m:.0f}" for p in pts], h_scale=500, v_scale=100, horizon=9.0)
    sheet = dr.build([Row("z", "value", 15, draw=True, values=z),
                      Row("i", "grade", 15, values=z, decimals=0),
                      Row("d", "distance", 10, decimals=0),
                      Row("pk", "station", 20),
                      Row("empty", "value", 15, values=np.full(len(ms), np.nan))])
    assert sheet.width == pytest.approx(400.0)                   # 200 м при 1:500
    surf = [c for c, k, *_ in sheet.lines if k == "surface"][0]
    assert surf[0] == pytest.approx((0.0, 10.0)) and surf[-1] == pytest.approx((400.0, 30.0))
    titles = [t[2] for t in sheet.texts if t[7] == "title"]
    assert titles == ["z", "i", "d", "pk"]                        # пустая строка не выводится
    grades = [t[2] for t in sheet.texts if t[7] == "grade"]
    assert "10" in grades and "200" in grades
    assert [t[2] for t in sheet.texts if t[7] == "distance"] == ["100", "100"]
