import pytest

from routeliner.core.chainage import ChainageSystem, LedgerPoint, convert
from routeliner.core.errors import CoreError, ErrorCode


def ok(x):
    assert not isinstance(x, CoreError), x
    return x


def code(x):
    assert isinstance(x, CoreError), x
    return x.code


# ------------------------------------------------------------ по длине
def test_from_length():
    s = ChainageSystem.from_length("проект", 1000.0, start_station=200.0)
    assert ok(s.to_station(0.0)) == pytest.approx(200.0)
    assert ok(s.to_measure(1200.0)) == pytest.approx(1000.0)
    assert code(s.to_station(1000.5)) is ErrorCode.MEASURE_OUT_OF_RANGE
    assert code(s.to_measure(100.0)) is ErrorCode.STATION_OUT_OF_RANGE


# ------------------------------------------------------------ невязка ведомости
def test_ledger_scale():
    # геометрия короче пикетажа на 1 м на 500 м (масштаб проекции)
    s = ok(ChainageSystem.from_ledger("исп", [(0, 0), (500, 499), (1000, 998)]))
    assert s.sections[0].scale == pytest.approx(500 / 499)
    assert ok(s.to_measure(250.0)) == pytest.approx(249.5)
    assert ok(s.to_station(998.0)) == pytest.approx(1000.0)


# ------------------------------------------------------------ прямая вставка
@pytest.fixture
def forward():
    # на m=550 уравнение ПК 5+50 = ПК 6+00, значения 550..600 пропущены
    return ok(ChainageSystem.from_ledger(
        "fwd", [(0, 0), (500, 500), (1050, 1000)], equations=[(550, 600)]))


def test_forward_equation_located(forward):
    assert forward.equations() == [(pytest.approx(550.0), 550.0, 600.0)]
    assert forward.is_monotonic


def test_forward_before_and_after(forward):
    assert ok(forward.to_measure(540.0)) == pytest.approx(540.0)
    assert ok(forward.to_measure(610.0)) == pytest.approx(560.0)
    assert ok(forward.to_station(560.0)) == pytest.approx(610.0)


def test_forward_gap(forward):
    assert code(forward.to_measure(575.0)) is ErrorCode.STATION_IN_GAP


# ------------------------------------------------------------ обратная вставка
@pytest.fixture
def backward():
    # на m=550 уравнение ПК 5+50 = ПК 5+00, значения 500..550 встречаются дважды
    return ok(ChainageSystem.from_ledger(
        "bwd", [(0, 0), (500, 500), (950, 1000)], equations=[(550, 500)]))


def test_backward_equation_located(backward):
    assert backward.equations() == [(pytest.approx(550.0), 550.0, 500.0)]
    assert not backward.is_monotonic


def test_backward_ambiguous(backward):
    assert code(backward.to_measure(520.0)) is ErrorCode.STATION_AMBIGUOUS


def test_backward_with_section_hint(backward):
    first = [s.index for s in backward.sections if s.contains_station(520.0)]
    assert len(first) == 2
    assert ok(backward.to_measure(520.0, section=first[0])) == pytest.approx(520.0)
    assert ok(backward.to_measure(520.0, section=first[-1])) == pytest.approx(570.0)


def test_backward_unique_outside_zone(backward):
    assert ok(backward.to_measure(400.0)) == pytest.approx(400.0)
    assert ok(backward.to_measure(700.0)) == pytest.approx(750.0)


def test_backward_station_at_equation_point(backward):
    # в самой точке уравнения меру отдаём по пикету «вперёд»
    assert ok(backward.to_station(550.0)) == pytest.approx(500.0)
    assert ok(backward.to_station(549.999)) == pytest.approx(549.999)


def test_backward_reper_inside_zone_resolved_by_scale():
    # ПК 5+20 на m=570 может быть только после уравнения: иначе масштаб 20/70
    s = ok(ChainageSystem.from_ledger("x", [(0, 0), (500, 500), (520, 570)],
                                      equations=[(550, 500)]))
    assert s.equations() == [(pytest.approx(550.0), 550.0, 500.0)]


def test_backward_reper_inside_zone_really_ambiguous():
    # обратная вставка 0.2 м: обе стороны дают масштаб около 1
    r = ChainageSystem.from_ledger("x", [(0, 0), (500, 500), (549.9, 549.9)],
                                   equations=[(550, 549.8)])
    assert code(r) is ErrorCode.LEDGER_INVALID


# ------------------------------------------------------------ разное
def test_extend_to_route_length():
    s = ok(ChainageSystem.from_points(
        "x", [LedgerPoint(100, 1100), LedgerPoint(200, 1200)], route_length=300))
    assert ok(s.to_station(0.0)) == pytest.approx(1000.0)
    assert ok(s.to_station(300.0)) == pytest.approx(1300.0)


def test_decreasing_ledger_rejected():
    assert code(ChainageSystem.from_ledger("x", [(0, 0), (500, 500), (400, 800)])) \
        is ErrorCode.LEDGER_INVALID


def test_duplicate_measure_rejected():
    assert code(ChainageSystem.from_points(
        "x", [LedgerPoint(0, 0), LedgerPoint(0, 10)])) is ErrorCode.LEDGER_INVALID


def test_convert_between_systems(backward):
    old = ChainageSystem.from_length("старый", 1000.0, start_station=10000.0)
    # новый ПК 7+00 -> m=750 -> старый ПК 107+50
    assert ok(convert(700.0, backward, old)) == pytest.approx(10750.0)
    assert code(convert(520.0, backward, old)) is ErrorCode.STATION_AMBIGUOUS
