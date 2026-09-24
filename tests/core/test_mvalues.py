import numpy as np
import pytest

from routeliner.core.assembler import RouteAssembler
from routeliner.core.chainage import ChainageSystem
from routeliner.core.errors import CoreError
from routeliner.core.route import RouteGeometry

NAN = float("nan")


def xym(pts):
    """(x, y, m) -> столбцы x, y, z=NaN, m, как их отдаёт адаптер слоя."""
    return np.array([[x, y, NAN, m] for x, y, m in pts])


def test_m_column_is_split_from_coordinates():
    r = RouteGeometry("A", [xym([(0, 0, 1000), (100, 0, 1100)])])
    assert r.parts[0].shape == (2, 2)
    assert r.has_m and r.length == pytest.approx(100)
    assert r.vertex_measures() == [(0.0, 1000.0), (100.0, 1100.0)]


def test_route_without_m():
    r = RouteGeometry("A", [np.array([[0, 0], [10, 0]])])
    assert not r.has_m and r.vertex_measures() == []


def test_z_is_kept_next_to_m():
    c = np.array([[0, 0, 5, 0], [100, 0, 6, 100]], dtype=float)
    r = RouteGeometry("A", [c])
    assert r.parts[0].shape == (2, 3) and r.measures[0][1] == 100


def test_from_measures_linear_merges_collinear_vertices():
    pairs = [(0, 500), (40, 540), (100, 600), (250, 750)]
    s = ChainageSystem.from_measures("M", pairs)
    assert len(s.sections) == 1
    assert s.to_station(100) == pytest.approx(600)


def test_from_measures_scale_and_factor():
    # одометр в километрах, масштаб 1,02 на первом отрезке
    s = ChainageSystem.from_measures("M", [(0, 0.0), (100, 0.102), (200, 0.202)], factor=1000)
    assert len(s.sections) == 2
    assert s.to_station(50) == pytest.approx(51)
    assert s.to_measure(152) == pytest.approx(150)


def test_from_measures_equation_from_duplicated_vertex():
    # в точке m=100 пикетаж перескакивает со 100 на 150 (прямая вставка)
    r = RouteGeometry("A", [xym([(0, 0, 0), (100, 0, 100), (100, 0, 150), (200, 0, 250)])])
    s = ChainageSystem.from_measures("M", r.vertex_measures(), r.length)
    assert s.equations() == [(100.0, 100.0, 150.0)]
    assert s.to_station(120) == pytest.approx(170)
    assert isinstance(s.to_measure(120), CoreError)       # ПК в прямой вставке


def test_from_measures_equation_between_parts():
    asm = RouteAssembler(allow_gaps=True)
    r = asm.build("A", [xym([(0, 0, 0), (100, 0, 100)]), xym([(105, 0, 90), (205, 0, 190)])])
    s = ChainageSystem.from_measures("M", r.vertex_measures(), r.length)
    assert s.equations() == [(100.0, 100.0, 90.0)]          # обратная вставка
    assert isinstance(s.to_measure(95), CoreError)          # ПК 95 встречается дважды
    assert s.to_measure(95, section=1) == pytest.approx(105)


def test_from_measures_missing_m_is_interpolated_and_ends_extended():
    pairs = [(0, NAN), (50, 1050), (100, NAN), (150, 1150), (200, NAN)]
    s = ChainageSystem.from_measures("M", pairs, route_length=200)
    assert s.to_station(0) == pytest.approx(1000)
    assert s.to_station(200) == pytest.approx(1200)


def test_from_measures_errors():
    assert isinstance(ChainageSystem.from_measures("M", [(0, 1)]), CoreError)
    assert isinstance(ChainageSystem.from_measures("M", [(0, 100), (50, 90)]), CoreError)


def test_substring_m():
    r = RouteGeometry("A", [np.array([[0, 0], [100, 0], [100, 100]])])
    (c, m), = r.substring_m(50, 150)
    assert m.tolist() == [50, 100, 150]
    assert c[:, :2].tolist() == [[50, 0], [100, 0], [100, 50]]


def test_stations_along_inserts_equation_vertices():
    s = ChainageSystem.from_table(
        "s", [(0, 0.0, None), (100, 100.0, 150), (250, 200.0, None)])
    c = np.array([[0, 0], [200, 0]], dtype=float)
    c2, m, st = s.stations_along(c, [0, 200])
    assert m.tolist() == [0, 100, 100, 200]
    assert st.tolist() == pytest.approx([0, 100, 150, 250])
    assert c2[1].tolist() == c2[2].tolist() == [100, 0]


def test_stations_along_equation_at_vertex_and_at_end():
    s = ChainageSystem.from_table("s", [(0, 0.0, None), (100, 100.0, 150), (250, 200.0, None)])
    c = np.array([[0, 0], [100, 0], [200, 0]], dtype=float)
    _, m, st = s.stations_along(c, [0, 100, 200])
    assert m.tolist() == [0, 100, 100, 200] and st.tolist() == pytest.approx([0, 100, 150, 250])
    _, m, st = s.stations_along(c[:2], [0, 100])
    assert st.tolist() == pytest.approx([0, 100])            # конец линии на уравнении - ПК назад


def test_round_trip_ledger_to_m_and_back():
    s = ChainageSystem.from_table("s", [(0, 0.0, None), (100, 100.0, 90), (300, 310.0, None)])
    c = np.array([[0, 0], [150, 0], [310, 0]], dtype=float)
    c2, m, st = s.stations_along(c, [0, 150, 310])
    r = RouteGeometry("A", [np.column_stack([c2, np.full(len(c2), NAN), st])])
    s2 = ChainageSystem.from_measures("M", r.vertex_measures(), r.length)
    for mm in (0, 50, 99, 101, 150, 309):
        assert s2.to_station(mm) == pytest.approx(s.to_station(mm))
    assert s2.equations() == pytest.approx(s.equations())


def test_equation_at_joint_of_two_features():
    asm = RouteAssembler()
    r = asm.build("A", [xym([(100, 0, 150), (200, 0, 250)]), xym([(0, 0, 0), (100, 0, 100)])])
    s = ChainageSystem.from_measures("M", r.vertex_measures(), r.length)
    assert r.length == pytest.approx(200)
    assert s.equations() == [(100.0, 100.0, 150.0)]
