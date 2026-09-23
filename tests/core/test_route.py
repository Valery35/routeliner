import math

import numpy as np
import pytest

from routeliner.core.assembler import RouteAssembler
from routeliner.core.errors import CoreError, ErrorCode
from routeliner.core.route import RouteGeometry


def ok(x):
    assert not isinstance(x, CoreError), x
    return x


def code(x):
    assert isinstance(x, CoreError), x
    return x.code


# Г-образная трасса: 100 м на восток, затем 100 м на север
L = [[0, 0], [100, 0], [100, 100]]


# ------------------------------------------------------------ RouteGeometry
def test_length_and_points():
    r = RouteGeometry(1, [np.array(L)])
    assert r.length == pytest.approx(200)
    p = ok(r.point_at(50))
    assert (p.x, p.y, p.azimuth) == pytest.approx((50, 0, 90))
    p = ok(r.point_at(150))
    assert (p.x, p.y, p.azimuth) == pytest.approx((100, 50, 0))


def test_offset_left_is_positive():
    r = RouteGeometry(1, [np.array(L)])
    p = ok(r.point_at(50, offset=5))       # идём на восток, лево — север
    assert (p.x, p.y) == pytest.approx((50, 5))
    p = ok(r.point_at(50, offset=-5))
    assert (p.x, p.y) == pytest.approx((50, -5))


def test_out_of_range():
    r = RouteGeometry(1, [np.array(L)])
    assert code(r.point_at(200.5)) is ErrorCode.MEASURE_OUT_OF_RANGE


def test_batch_matches_single():
    r = RouteGeometry(1, [np.array(L)])
    ms = np.linspace(0, 200, 41)
    b = r.points_at(ms)
    for i, m in enumerate(ms):
        p = ok(r.point_at(m))
        assert (b["x"][i], b["y"][i]) == pytest.approx((p.x, p.y))
    assert b["ok"].all()


def test_substring_keeps_corner():
    r = RouteGeometry(1, [np.array(L)])
    pieces = ok(r.substring(50, 150))
    assert len(pieces) == 1
    assert np.allclose(pieces[0][:, :2], [[50, 0], [100, 0], [100, 50]])


def test_substring_from_ge_to():
    r = RouteGeometry(1, [np.array(L)])
    assert code(r.substring(100, 100)) is ErrorCode.FROM_GE_TO


def test_locate_sign_and_measure():
    r = RouteGeometry(1, [np.array(L)])
    pr = ok(r.locate(30, 4))
    assert (pr.m, pr.offset) == pytest.approx((30, 4))
    pr = ok(r.locate(103, 60))            # справа от участка на север
    assert (pr.m, pr.offset) == pytest.approx((160, -3))


def test_3d_length():
    r = RouteGeometry(1, [np.array([[0, 0, 0], [30, 0, 40]])], use_z=True)
    assert r.length == pytest.approx(50)
    r2 = RouteGeometry(1, [np.array([[0, 0, 0], [30, 0, 40]])], use_z=False)
    assert r2.length == pytest.approx(30)
    assert ok(r.point_at(25)).z == pytest.approx(20)


# ------------------------------------------------------------ сборка
def test_parts_in_wrong_order_and_direction():
    # три куска одной трассы, в хранении перепутаны порядок и направление
    parts = [
        [[100, 0], [100, 100]],            # середина, правильно
        [[200, 100], [100, 100]],          # конец, перевёрнут
        [[0, 0], [100, 0]],                # начало, правильно
    ]
    r = ok(RouteAssembler().build("A", parts))
    assert r.length == pytest.approx(300)
    assert ok(r.point_at(0)).x == pytest.approx(0)
    assert (ok(r.point_at(300)).x, ok(r.point_at(300)).y) == pytest.approx((200, 100))
    assert r.gaps == []


def test_direction_follows_majority_of_digitizing():
    # две части оцифрованы с востока на запад, одна короткая — наоборот
    parts = [[[300, 0], [200, 0]], [[200, 0], [100, 0]], [[90, 0], [100, 0]]]
    r = ok(RouteAssembler(snap_tolerance=0.01, allow_gaps=True).build("A", parts))
    assert ok(r.point_at(0)).x == pytest.approx(300)


def test_reverse_flag():
    r = ok(RouteAssembler(reverse=True).build("A", [L]))
    assert ok(r.point_at(0)).y == pytest.approx(100)


def test_snap_within_tolerance():
    parts = [[[0, 0], [100, 0]], [[100.004, 0.003], [200, 0]]]
    r = ok(RouteAssembler(snap_tolerance=0.01).build("A", parts))
    assert r.length == pytest.approx(200, abs=0.01)


def test_gap_is_error_by_default():
    parts = [[[0, 0], [100, 0]], [[105, 0], [200, 0]]]
    err = RouteAssembler().build("A", parts)
    assert code(err) is ErrorCode.ROUTE_GAP
    assert "5.000" in err.message


def test_gap_allowed_gives_multipart_substring():
    parts = [[[105, 0], [200, 0]], [[0, 0], [100, 0]]]
    r = ok(RouteAssembler(allow_gaps=True).build("A", parts))
    assert r.length == pytest.approx(195)            # разрыв в длину не входит
    assert [(g.m, g.distance) for g in r.gaps] == [pytest.approx((100, 5))]
    p = ok(r.point_at(100.5))
    assert p.x == pytest.approx(105.5)
    pieces = ok(r.substring(90, 110))
    assert len(pieces) == 2
    assert pieces[0][-1, 0] == pytest.approx(100) and pieces[1][0, 0] == pytest.approx(105)


def test_branching():
    parts = [[[0, 0], [100, 0]], [[100, 0], [200, 0]], [[100, 0], [100, 100]]]
    assert code(RouteAssembler().build("A", parts)) is ErrorCode.ROUTE_BRANCHING


def test_geographic_crs_rejected():
    assert code(RouteAssembler().build("A", [L], geographic_crs=True)) is ErrorCode.GEOGRAPHIC_CRS


def test_ring_route():
    ring = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]
    r = ok(RouteAssembler().build("A", [ring]))
    assert r.length == pytest.approx(400)


def test_empty_and_degenerate():
    assert code(RouteAssembler().build("A", [])) is ErrorCode.ROUTE_NOT_FOUND
    assert code(RouteAssembler().build("A", [[[1, 1], [1, 1]]])) is ErrorCode.ROUTE_NOT_FOUND


def test_arc_segmented_length_close_to_true():
    # четверть окружности R=100, сегментированная по 1 градусу
    a = np.radians(np.arange(0, 91))
    arc = np.column_stack([100 * np.cos(a), 100 * np.sin(a)])
    r = ok(RouteAssembler().build("A", [arc]))
    assert r.length == pytest.approx(math.pi * 50, rel=1e-4)


def test_batch_100k_is_fast():
    import time
    a = np.radians(np.linspace(0, 3600, 20001))
    line = np.column_stack([np.linspace(0, 50000, 20001), 200 * np.sin(a)])
    r = ok(RouteAssembler().build("A", [line]))
    ms = np.random.default_rng(1).uniform(0, r.length, 100_000)
    t = time.perf_counter()
    res = r.points_at(ms, 2.0)
    assert time.perf_counter() - t < 1.0
    assert res["ok"].all()
