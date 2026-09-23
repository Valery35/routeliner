import pytest

from routeliner.core.errors import CoreError, ErrorCode
from routeliner.core.stations import Station, StationFormat as F, StationParser


def val(parser, raw, prev=None):
    r = parser.parse(raw, prev)
    assert not isinstance(r, CoreError), r
    return r.value


@pytest.mark.parametrize("raw,expected", [
    ("ПК 15+35", 1535.0),
    ("пк15+35", 1535.0),
    ("15+35", 1535.0),
    ("15 + 35", 1535.0),
    ("ПК15+35.5", 1535.5),
    ("15+35,5", 1535.5),
    ("ПК 0+00", 0.0),
    ("ПК 15", 1500.0),
    ("ПК -1+50", -50.0),
    ("ПК 25+114.3", 2614.3),      # домер: плюс больше длины пикета
    ("PK 3+05", 305.0),
    ("ПК 12+40", 1240.0),
])
def test_pk_plus(raw, expected):
    assert val(StationParser(F.PK_PLUS), raw) == pytest.approx(expected)


def test_pk_plus_rejects_bare_number():
    r = StationParser(F.PK_PLUS).parse("1535")
    assert isinstance(r, CoreError) and r.code is ErrorCode.STATION_PARSE_FAILED


def test_pk_plus_rejects_number_type():
    assert isinstance(StationParser(F.PK_PLUS).parse(1535), CoreError)


def test_relative_plus():
    p = StationParser(F.PK_PLUS)
    prev = Station(1535.0)
    assert val(p, "+72", prev) == pytest.approx(1572.0)
    assert isinstance(p.parse("+72"), CoreError)


def test_picket_length_20():
    assert val(StationParser(F.PK_PLUS, picket_length=20), "ПК 3+5") == pytest.approx(65.0)


@pytest.mark.parametrize("raw,expected", [
    ("км 1+535", 1535.0), ("1+535.2", 1535.2), ("KM 12+005", 12005.0),
])
def test_km_plus(raw, expected):
    assert val(StationParser(F.KM_PLUS), raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw,expected", [
    ("км 1 ПК 1", 0.0),
    ("км 12 ПК 3+45", 11245.0),
    ("км 12, пк 10+99.9", 11999.9),
])
def test_rail(raw, expected):
    assert val(StationParser(F.RAIL), raw) == pytest.approx(expected)


def test_rail_rejects_picket_11():
    assert isinstance(StationParser(F.RAIL).parse("км 2 ПК 11"), CoreError)


@pytest.mark.parametrize("raw,expected", [
    ("1535", 1535.0), ("1535,5", 1535.5), ("1 535,5", 1535.5), (1535.5, 1535.5), ("-20", -20.0),
])
def test_meters(raw, expected):
    assert val(StationParser(F.METERS), raw) == pytest.approx(expected)


def test_km_decimal():
    assert val(StationParser(F.KM), "1,535") == pytest.approx(1535.0)
    assert val(StationParser(F.KM), 2.5) == pytest.approx(2500.0)


@pytest.mark.parametrize("raw", [None, "", "abc", "ПК 15+", float("nan")])
def test_garbage(raw):
    assert isinstance(StationParser(F.PK_PLUS).parse(raw), CoreError)


@pytest.mark.parametrize("fmt,value,text", [
    (F.PK_PLUS, 1535.0, "ПК 15+35.00"),
    (F.PK_PLUS, -50.0, "ПК -1+50.00"),
    (F.PK_PLUS, 1599.999, "ПК 16+00.00"),
    (F.KM_PLUS, 1535.2, "км 1+535.20"),
    (F.RAIL, 11245.0, "км 12 ПК 3+45.00"),
    (F.METERS, 1535.5, "1535.50"),
])
def test_format(fmt, value, text):
    assert StationParser(fmt).format(value) == text


@pytest.mark.parametrize("fmt", [F.PK_PLUS, F.KM_PLUS, F.RAIL, F.METERS])
@pytest.mark.parametrize("value", [0.0, 35.5, 1535.25, 11999.9])
def test_round_trip(fmt, value):
    p = StationParser(fmt)
    assert val(p, p.format(value)) == pytest.approx(value)
