"""Демонстрационный пример проходит через ядро и совпадает с эталоном."""
import math
import re

import numpy as np
import pytest

from routeliner.core import demo as D
from routeliner.core.assembler import RouteAssembler
from routeliner.core.chainage import ChainageSystem
from routeliner.core.errors import CoreError
from routeliner.core.events import EventLocator, EventRecord
from routeliner.core.stations import StationFormat, StationParser

TOL = 0.01


def _parts_from_wkt(wkt):
    groups = re.findall(r"\(([^()]+)\)", wkt)
    return [np.array([[float(v) for v in p.split()[:2]] for p in g.split(",")]) for g in groups]


@pytest.fixture(scope="module")
def world():
    d = D.build(seed=7)
    parts = {}
    for rid, _, wkt in d.routes:
        if rid == "R2":
            r2 = d.paths["R2"]
            ms = np.linspace(0, r2.length, 20001)
            parts["R2"] = [np.array([r2.point(m) for m in ms])]
        else:
            parts.setdefault(rid, []).extend(_parts_from_wkt(wkt))
    asm = RouteAssembler(snap_tolerance=0.01)
    routes, errors = {}, []
    for rid, ps in parts.items():
        r = asm.build(rid, ps)
        if isinstance(r, CoreError):
            errors.append(r)
        else:
            routes[rid] = r
    parser = StationParser(StationFormat.PK_PLUS)
    rows = [(parser.parse(st).value, m, parser.parse(a).value if a else None)
            for rid, _, st, m, a, _ in d.ledger]
    systems = {"R3": ChainageSystem.from_table(D.SYSTEM, rows, routes["R3"].length)}
    return d, routes, errors, EventLocator(routes, parser, systems)


def test_assembly(world):
    d, routes, errors, _ = world
    assert set(routes) == {"R1", "R2", "R3"}
    assert [e.route_id for e in errors] == ["R4"]
    assert routes["R3"].length == pytest.approx(1600, abs=1e-3)   # WKT с 4 знаками
    assert routes["R2"].length == pytest.approx(1000 + 150 * math.pi, abs=0.01)


def test_points_match_reference(world):
    d, routes, _, loc = world
    recs = [EventRecord(p["eid"], p["route_id"], p["pk"], None, p["offset"], p["section"])
            for p in d.points]
    ok, bad = loc.locate_points(recs)
    got = {r.key: r for r in ok}
    errs = {e.key: e.code.value for e in bad}
    for p in d.points:
        if p["exp_error"]:
            assert errs.get(p["eid"]) == p["exp_error"], p
        else:
            r = got[p["eid"]]
            assert r.m == pytest.approx(p["exp_m"], abs=TOL), p
            assert math.hypot(r.x - p["exp_x"], r.y - p["exp_y"]) < TOL, p


def test_lines_match_reference(world):
    d, routes, _, loc = world
    recs = [EventRecord(l["eid"], l["route_id"], l["pk_from"], l["pk_to"], l["offset"])
            for l in d.lines]
    ok, bad = loc.locate_lines(recs)
    got = {r.key: r for r in ok}
    errs = {e.key: e.code.value for e in bad}
    for l in d.lines:
        if l["exp_error"]:
            assert errs.get(l["eid"]) == l["exp_error"]
        else:
            r = got[l["eid"]]
            assert (r.m_from, r.m_to) == pytest.approx((l["exp_m_from"], l["exp_m_to"]), abs=TOL)
            x, y = d.paths[l["route_id"]].point(l["exp_m_from"], l["offset"])
            assert math.hypot(*(r.pieces[0][0, :2] - (x, y))) < TOL


def test_defects_match_reference(world):
    d, routes, _, loc = world
    for f in d.defects:
        r = loc.locate_xy(f["did"], f["x"], f["y"])
        assert not isinstance(r, CoreError), r
        assert r.route_id == f["exp_route"]
        assert r.m == pytest.approx(f["exp_m"], abs=TOL)
        assert r.station == pytest.approx(f["exp_station"], abs=TOL)
        assert r.offset == pytest.approx(f["exp_offset"], abs=TOL)


def test_whole_pickets_on_r3(world):
    *_, loc = world
    values = [s for _, s, _ in loc.system_for("R3").whole_stations(100)]
    # в зоне повтора 6+74.30..6+99.30 целых пикетов нет; 13+00 попал в прямую вставку
    assert values.count(600) == 1 and values.count(700) == 1
    assert 1300 not in values and values.count(1400) == 1
    assert values[0] == 0 and values[-1] == 1600
