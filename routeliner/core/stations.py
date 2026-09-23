"""Разбор и форматирование записей пикетажа.

Режим разбора задаётся явно. Значение пикета всегда в метрах пикетажа
(это ещё не геометрическая мера: перевод в меру делает ChainageSystem).

Режимы:
  PK_PLUS  'ПК 15+35', '15+35', 'ПК15+35.5', '15+35,5', 'ПК -1+50', 'ПК 15',
           '+35' (тот же пикет, что у предыдущей записи)
  KM_PLUS  'км 1+535', '1+535.2' (километр + метры, дорожная запись)
  RAIL     'км 12 ПК 3+45' (километры и пикеты 1..10 нумеруются с единицы)
  METERS   '1535', '1535,5', числа из таблицы
  KM       '1,535' или 1.535 (километры десятичной дробью)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from ..i18n import tr
from .errors import CoreError, ErrorCode


class StationFormat(Enum):
    PK_PLUS = "pk_plus"
    KM_PLUS = "km_plus"
    RAIL = "rail"
    METERS = "meters"
    KM = "km"


@dataclass(frozen=True)
class Station:
    value: float          # метры пикетажа
    raw: str = ""


_NUM = r"\d+(?:[.,]\d+)?"
_RE_PK_PLUS = re.compile(
    rf"^(?:пк|pk)?\s*(?P<sign>[-−–])?\s*(?P<pk>\d+)\s*(?:\+\s*(?P<plus>{_NUM}))?$")
_RE_REL = re.compile(rf"^\+\s*(?P<plus>{_NUM})$")
_RE_KM_PLUS = re.compile(
    rf"^(?:км|km)?\s*(?P<sign>[-−–])?\s*(?P<km>\d+)\s*\+\s*(?P<plus>{_NUM})$")
_RE_RAIL = re.compile(
    rf"^(?:км|km)\s*(?P<km>\d+)\s*[,;]?\s*(?:пк|pk)\s*(?P<pk>\d+)"
    rf"\s*(?:\+\s*(?P<plus>{_NUM}))?$")
_RE_NUM = re.compile(rf"^(?P<sign>[-−–])?\s*(?P<v>{_NUM})$")


def _f(text: str) -> float:
    return float(text.replace(",", "."))


def _norm(raw: str) -> str:
    s = str(raw).strip().lower().replace(" ", " ")
    return re.sub(r"\s+", " ", s)


class StationParser:
    def __init__(self, fmt: StationFormat, picket_length: float = 100.0,
                 decimals: int = 2) -> None:
        if picket_length <= 0:
            raise ValueError("picket_length must be positive")
        self.fmt = fmt
        self.picket_length = float(picket_length)
        self.decimals = decimals

    # ------------------------------------------------------------ разбор
    def parse(self, raw: Union[str, float, int, None],
              previous: Optional[Station] = None) -> Union[Station, CoreError]:
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            return self._fail(raw, tr("пустое значение"))
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            if self.fmt is StationFormat.METERS:
                return Station(float(raw), str(raw))
            if self.fmt is StationFormat.KM:
                return Station(float(raw) * 1000.0, str(raw))
            return self._fail(raw, tr("число без «+» в режиме записи с плюсом"))
        s = _norm(raw)
        if not s:
            return self._fail(raw, tr("пустое значение"))
        method = getattr(self, "_parse_" + self.fmt.value)
        value = method(s, previous)
        if value is None:
            return self._fail(raw, tr("не соответствует формату {fmt}").format(fmt=self.fmt.value))
        if isinstance(value, CoreError):
            return value
        return Station(value, str(raw))

    def _parse_pk_plus(self, s: str, previous: Optional[Station]):
        m = _RE_REL.match(s)
        if m:
            if previous is None:
                return CoreError(ErrorCode.STATION_PARSE_FAILED,
                                 tr("«{s}»: относительная запись без предыдущего пикета").format(s=s))
            pk = math.floor(previous.value / self.picket_length + 1e-9)
            return pk * self.picket_length + _f(m["plus"])
        m = _RE_PK_PLUS.match(s)
        if not m or (m["plus"] is None and not s.startswith(("пк", "pk"))):
            return None  # '1535' без 'ПК' и без '+' неоднозначно
        pk = int(m["pk"])
        plus = _f(m["plus"]) if m["plus"] else 0.0
        if m["sign"]:
            pk = -pk
        return pk * self.picket_length + plus

    def _parse_km_plus(self, s: str, previous: Optional[Station]):
        m = _RE_KM_PLUS.match(s)
        if not m:
            return None
        km = int(m["km"])
        if m["sign"]:
            km = -km
        return km * 1000.0 + _f(m["plus"])

    def _parse_rail(self, s: str, previous: Optional[Station]):
        m = _RE_RAIL.match(s)
        if not m:
            return None
        km, pk = int(m["km"]), int(m["pk"])
        if km < 1 or not 1 <= pk <= 10:
            return CoreError(ErrorCode.STATION_PARSE_FAILED,
                             tr("«{s}»: километр с 1, пикет от 1 до 10").format(s=s))
        plus = _f(m["plus"]) if m["plus"] else 0.0
        return (km - 1) * 1000.0 + (pk - 1) * 100.0 + plus

    def _parse_meters(self, s: str, previous: Optional[Station]):
        m = _RE_NUM.match(s.replace(" ", ""))
        if not m:
            return None
        v = _f(m["v"])
        return -v if m["sign"] else v

    def _parse_km(self, s: str, previous: Optional[Station]):
        v = self._parse_meters(s.replace("км", "").replace("km", ""), previous)
        return None if v is None else v * 1000.0

    def _fail(self, raw, why: str) -> CoreError:
        return CoreError(ErrorCode.STATION_PARSE_FAILED, f"«{raw}»: {why}")

    # ------------------------------------------------------ форматирование
    def format(self, value: float) -> str:
        d = self.decimals
        if self.fmt is StationFormat.PK_PLUS:
            pk, plus = self._split(value, self.picket_length)
            return f"ПК {pk}+{plus:0{3 + d if d else 2}.{d}f}"
        if self.fmt is StationFormat.KM_PLUS:
            km, plus = self._split(value, 1000.0)
            return f"км {km}+{plus:0{4 + d if d else 3}.{d}f}"
        if self.fmt is StationFormat.RAIL:
            km, rest = self._split(value, 1000.0)
            pk, plus = self._split(rest, 100.0)
            return f"км {km + 1} ПК {pk + 1}+{plus:0{3 + d if d else 2}.{d}f}"
        if self.fmt is StationFormat.KM:
            return f"{value / 1000.0:.{d + 3}f}"
        return f"{value:.{d}f}"

    def _split(self, value: float, unit: float) -> tuple[int, float]:
        """Целая часть вниз (ПК -1+50 = -50 м), остаток неотрицателен.
        Округление остатка не должно давать '+100.00'."""
        q = round(value, self.decimals)
        n = math.floor(q / unit + 1e-12)
        rest = round(q - n * unit, self.decimals)
        if rest >= unit:
            n, rest = n + 1, round(rest - unit, self.decimals)
        return n, rest
