"""Система пикетажа маршрута.

Опорная величина — геометрическая мера m (длина по оси от начала маршрута).
Пикетаж задан кусочно-линейно: участки между реперами ведомости и точками
пикетажных уравнений. Внутри участка пикет растёт линейно по m, между
участками возможен скачок:
  прямая вставка  (ПК назад < ПК вперёд) — часть значений пикетажа пропущена;
  обратная вставка (ПК назад > ПК вперёд) — часть значений встречается дважды.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union

import numpy as np

from ..i18n import tr
from .errors import CoreError, ErrorCode

EPS = 1e-6
SCALE_TOL = 0.02   # допустимое отклонение масштаба участка от 1 при выборе стороны вставки


@dataclass(frozen=True)
class LedgerPoint:
    """Репер ведомости. У точки уравнения два пикета: назад и вперёд."""
    m: float
    station: float
    station_ahead: Optional[float] = None

    @property
    def ahead(self) -> float:
        return self.station if self.station_ahead is None else self.station_ahead

    @property
    def is_equation(self) -> bool:
        return self.station_ahead is not None and abs(self.station_ahead - self.station) > EPS


@dataclass(frozen=True)
class ChainageSection:
    index: int
    m_from: float
    m_to: float
    st_from: float
    st_to: float

    @property
    def scale(self) -> float:
        """Метры пикетажа на метр геометрии. Отклонение от 1 — невязка ведомости."""
        dm = self.m_to - self.m_from
        return (self.st_to - self.st_from) / dm if dm > 0 else 1.0

    def station_at(self, m: float) -> float:
        return self.st_from + (m - self.m_from) * self.scale

    def measure_at(self, st: float) -> float:
        k = self.scale
        return self.m_from + (st - self.st_from) / k if k else self.m_from

    def contains_station(self, st: float, tol: float = EPS) -> bool:
        return self.st_from - tol <= st <= self.st_to + tol


@dataclass
class ChainageSystem:
    name: str
    sections: list[ChainageSection] = field(default_factory=list)

    # ------------------------------------------------------------ построение
    @classmethod
    def from_length(cls, name: str, length: float,
                    start_station: float = 0.0) -> "ChainageSystem":
        return cls(name, [ChainageSection(0, 0.0, float(length),
                                          start_station, start_station + length)])

    @classmethod
    def from_points(cls, name: str, points: Iterable[LedgerPoint],
                    route_length: Optional[float] = None
                    ) -> Union["ChainageSystem", CoreError]:
        """Ведомость как список реперов с известной мерой m.
        route_length: если задан, участки до первого и после последнего репера
        достраиваются с масштабом 1 (иначе мера вне реперов — ошибка)."""
        pts = sorted(points, key=lambda p: p.m)
        if len(pts) < 2 and route_length is None:
            return _bad(name, tr("нужно не меньше двух реперов"))
        if not pts:
            return _bad(name, tr("ведомость пуста"))
        for a, b in zip(pts, pts[1:]):
            if b.m - a.m <= EPS:
                return _bad(name, tr("два репера с одной мерой m={m:.3f}").format(m=a.m))
        if route_length is not None:
            if pts[0].m > EPS:
                p = pts[0]
                pts.insert(0, LedgerPoint(0.0, p.station - p.m))
            if pts[-1].m < route_length - EPS:
                p = pts[-1]
                pts.append(LedgerPoint(route_length, p.ahead + (route_length - p.m)))
        sections = []
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = ChainageSection(i, a.m, b.m, a.ahead, b.station)
            if s.st_to - s.st_from <= EPS:
                return _bad(name, tr("пикетаж не растёт на участке m {a:.2f}..{b:.2f}, "
                                     "от {s0:.2f} до {s1:.2f}").format(
                    a=a.m, b=b.m, s0=s.st_from, s1=s.st_to))
            sections.append(s)
        return cls(name, sections)

    @classmethod
    def from_measures(cls, name: str, pairs: Sequence[tuple[float, float]],
                      route_length: Optional[float] = None, factor: float = 1.0
                      ) -> Union["ChainageSystem", CoreError]:
        """Пикетаж из M-значений вершин: pairs - (мера по оси, M) по ходу
        маршрута. factor переводит единицы M в метры (1000 для километров).

        Две вершины с одной мерой и разным M дают уравнение: первая - пикет
        назад, вторая - пикет вперёд. Вершины без M пропускаются, пикет
        между соседними вершинами с M идёт линейно. Вершины, лежащие на
        одной прямой пикетажа, склеиваются, чтобы участки пикетажа
        начинались только там, где меняется масштаб или стоит уравнение."""
        pts: list[LedgerPoint] = []
        for mg, mv in pairs:
            if mv is None or mv != mv:
                continue
            mv = float(mv) * factor
            if pts and mg - pts[-1].m <= EPS:
                last = pts[-1]
                if abs(mv - last.ahead) > EPS:
                    pts[-1] = LedgerPoint(last.m, last.station, mv)
                continue
            pts.append(LedgerPoint(float(mg), mv))
        if len(pts) < 2:
            return _bad(name, tr("у маршрута меньше двух вершин с M"))
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            p, q, a = pts[i], pts[i + 1], out[-1]
            if not p.is_equation:
                k1 = (p.station - a.ahead) / (p.m - a.m)
                k2 = (q.station - p.station) / (q.m - p.m)
                if abs(k1 - k2) <= 1e-9 * max(1.0, abs(k1)):
                    continue
            out.append(p)
        out.append(pts[-1])
        return cls.from_points(name, out, route_length)

    @classmethod
    def from_ledger(cls, name: str, rows: Sequence[tuple[float, float]],
                    equations: Sequence[tuple[float, float]] = (),
                    route_length: Optional[float] = None
                    ) -> Union["ChainageSystem", CoreError]:
        """rows: (пикет, m) — реперы с измеренной мерой.
        equations: (ПК назад, ПК вперёд) — положение уравнения находится
        интерполяцией ПК назад по реперам, стоящим перед ним.

        Пикет каждого репера отсчитан в системе участка, где репер стоит.
        Уравнения применяются по порядку вдоль трассы."""
        rows = sorted(rows, key=lambda r: r[1])
        eqs = list(equations)
        points: list[LedgerPoint] = []
        pending = [LedgerPoint(m, st) for st, m in rows]
        # Идём по реперам; уравнение ставим между последним репером с пикетом
        # <= ПК назад и следующим за ним, если следующий уже «после» уравнения.
        for p in pending:
            force_after = False
            if eqs and points and points[-1].ahead <= eqs[0][0] + EPS:
                back, ahead = eqs[0]
                if ahead < back and ahead - EPS <= p.station <= back + EPS:
                    # Пикет репера есть по обе стороны обратной вставки.
                    # Выбираем сторону, при которой масштаб участка ближе к 1.
                    a = points[-1]
                    dm = p.m - a.m
                    k_before = (p.station - a.ahead) / dm
                    k_after = (p.station + (back - ahead) - a.ahead) / dm
                    d_before = abs(k_before - 1) if k_before > 0 else float("inf")
                    d_after = abs(k_after - 1)
                    if min(d_before, d_after) > SCALE_TOL or \
                            abs(d_before - d_after) < SCALE_TOL:
                        return _bad(name, tr("репер ПК {st:.2f} (m={m:.2f}) лежит в обратной "
                                             "вставке {b}={a}, и его сторона неизвестна. "
                                             "Задайте мерой положение уравнения").format(
                            st=p.station, m=p.m, b=back, a=ahead))
                    force_after = d_after < d_before
            while eqs and points and (p.station > eqs[0][0] + EPS or force_after) \
                    and points[-1].ahead <= eqs[0][0] + EPS:
                force_after = False
                back, ahead = eqs.pop(0)
                a = points[-1]
                # Следующий репер отсчитан уже от ПК вперёд: восстанавливаем его
                # значение в системе «назад», чтобы найти m уравнения.
                st_b_equiv = p.station - (ahead - back)
                if st_b_equiv - a.ahead <= EPS:
                    return _bad(name, tr("уравнение {b}={a} не помещается между реперами "
                                         "m {m0:.2f} и {m1:.2f}").format(
                        b=back, a=ahead, m0=a.m, m1=p.m))
                k = (p.m - a.m) / (st_b_equiv - a.ahead)
                m_eq = a.m + (back - a.ahead) * k
                points.append(LedgerPoint(m_eq, back, ahead))
            points.append(p)
        if eqs:
            return _bad(name, tr("не удалось разместить уравнения {eqs}").format(eqs=eqs))
        return cls.from_points(name, points, route_length)

    @classmethod
    def from_table(cls, name: str,
                   rows: Sequence[tuple[float, Optional[float], Optional[float]]],
                   route_length: Optional[float] = None
                   ) -> Union["ChainageSystem", CoreError]:
        """Строки ведомости: (пикет, мера или None, пикет вперёд или None).
        Репер — пикет с мерой; уравнение — строка с пикетом вперёд, мера у
        уравнения может быть известна (тогда берётся) или нет (вычисляется)."""
        reps, eqs = [], []
        for st, m, ahead in rows:
            if ahead is not None and abs(ahead - st) > EPS:
                eqs.append((st, m, ahead))
            elif m is not None:
                reps.append((st, m))
            else:
                return _bad(name, tr("у репера ПК {st:.2f} не задана мера").format(st=st))
        if all(m is not None for _, m, _ in eqs):
            pts = [LedgerPoint(m, st) for st, m in reps] + \
                  [LedgerPoint(m, st, a) for st, m, a in eqs]
            return cls.from_points(name, pts, route_length)
        return cls.from_ledger(name, reps, [(st, a) for st, _, a in eqs], route_length)

    # ------------------------------------------------------------ запросы
    @property
    def m_start(self) -> float:
        return self.sections[0].m_from

    @property
    def m_end(self) -> float:
        return self.sections[-1].m_to

    @property
    def is_monotonic(self) -> bool:
        return all(b.st_from >= a.st_to - EPS
                   for a, b in zip(self.sections, self.sections[1:]))

    def equations(self) -> list[tuple[float, float, float]]:
        """(m, ПК назад, ПК вперёд) для всех скачков пикетажа."""
        return [(b.m_from, a.st_to, b.st_from)
                for a, b in zip(self.sections, self.sections[1:])
                if abs(b.st_from - a.st_to) > EPS]

    def whole_stations(self, step: float = 100.0) -> list[tuple[float, float, int]]:
        """Целые пикеты (кратные step) по всем участкам: (m, пикет, участок).
        В зоне обратной вставки одно значение даёт две точки, в прямой — ни одной."""
        out = []
        for s in self.sections:
            k0 = int(-(-(s.st_from - EPS) // step))       # ceil
            k1 = int((s.st_to + EPS) // step)
            for k in range(k0, k1 + 1):
                st = k * step
                if s is not self.sections[-1] and abs(st - s.st_to) <= EPS:
                    nxt = self.sections[s.index + 1]
                    if abs(nxt.st_from - s.st_to) <= EPS:
                        continue          # стык без уравнения: точку даст следующий участок
                out.append((s.measure_at(st), st, s.index))
        return out

    def to_station(self, m: float) -> Union[float, CoreError]:
        if m < self.m_start - EPS or m > self.m_end + EPS:
            return CoreError(ErrorCode.MEASURE_OUT_OF_RANGE,
                             tr("мера {m:.3f} вне {a:.3f}..{b:.3f}").format(
                                 m=m, a=self.m_start, b=self.m_end))
        starts = [s.m_from for s in self.sections]
        i = max(0, bisect.bisect_right(starts, m + EPS) - 1)
        return self.sections[i].station_at(m)

    def to_station_back(self, m: float) -> Union[float, CoreError]:
        """Пикет в точке m со стороны «назад»: на уравнении это ПК назад,
        в остальных точках то же, что to_station."""
        if m < self.m_start - EPS or m > self.m_end + EPS:
            return self.to_station(m)
        starts = [s.m_from for s in self.sections]
        i = max(0, bisect.bisect_left(starts, m - EPS) - 1)
        return self.sections[i].station_at(m)

    def stations_along(self, coords, ms) -> tuple:
        """M для вершин линии: вершины (coords) с мерами ms по возрастанию.
        Внутрь линии вставляются вершины уравнений, по две на уравнение с
        одинаковыми координатами (ПК назад и ПК вперёд). Возвращает новые
        coords, меры и пикеты."""
        c = np.asarray(coords, dtype=float)
        m = np.asarray(ms, dtype=float)
        if len(m) < 2:
            return c, m, np.array([self.to_station(float(v)) for v in m], dtype=float)
        for me, back, ahead in self.equations():
            if not m[0] + EPS < me < m[-1] - EPS:
                continue
            k = int(np.searchsorted(m, me))
            if abs(m[k] - me) <= EPS:
                p = c[k]
            else:
                t = (me - m[k - 1]) / (m[k] - m[k - 1])
                p = c[k - 1] + (c[k] - c[k - 1]) * t
                c = np.insert(c, k, p, axis=0)
                m = np.insert(m, k, me)
            c = np.insert(c, k, p, axis=0)
            m = np.insert(m, k, me)
        st = np.empty(len(m))
        for i, v in enumerate(m):
            back_side = i == len(m) - 1 or (i + 1 < len(m) and abs(m[i + 1] - v) <= EPS)
            st[i] = self.to_station_back(float(v)) if back_side else self.to_station(float(v))
        return c, m, st

    def to_measure(self, station: float,
                   section: Optional[int] = None) -> Union[float, CoreError]:
        """Пикет -> m. section — номер участка (с 0), нужен только когда
        пикет попадает в обратную вставку."""
        if section is not None:
            if not 0 <= section < len(self.sections):
                return CoreError(ErrorCode.STATION_OUT_OF_RANGE,
                                 tr("нет участка {n}").format(n=section))
            s = self.sections[section]
            if not s.contains_station(station):
                return CoreError(ErrorCode.STATION_OUT_OF_RANGE,
                                 tr("ПК {st:.2f} вне участка {n} ({a:.2f}..{b:.2f})").format(
                                     st=station, n=section, a=s.st_from, b=s.st_to))
            return s.measure_at(station)
        hits: list[float] = []
        for s in self.sections:
            if s.contains_station(station):
                m = s.measure_at(station)
                if not hits or abs(hits[-1] - m) > 1e-3:
                    hits.append(m)
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return CoreError(ErrorCode.STATION_AMBIGUOUS,
                             tr("ПК {st:.2f} встречается {n} раза (обратная вставка), "
                                "укажите участок").format(st=station, n=len(hits)))
        for a, b in zip(self.sections, self.sections[1:]):
            if a.st_to < station < b.st_from:
                return CoreError(ErrorCode.STATION_IN_GAP,
                                 tr("ПК {st:.2f} попал в прямую вставку {a:.2f}={b:.2f}").format(
                                     st=station, a=a.st_to, b=b.st_from))
        return CoreError(ErrorCode.STATION_OUT_OF_RANGE,
                         tr("ПК {st:.2f} вне пикетажа маршрута").format(st=station))


def convert(station: float, source: ChainageSystem, target: ChainageSystem,
            section: Optional[int] = None) -> Union[float, CoreError]:
    """Пересчёт пикета из одной системы в другую через меру m."""
    m = source.to_measure(station, section)
    if isinstance(m, CoreError):
        return m
    return target.to_station(m)


def _bad(name: str, why: str) -> CoreError:
    return CoreError(ErrorCode.LEDGER_INVALID, tr("система «{name}»: {why}").format(name=name, why=why))
