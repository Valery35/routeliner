"""Постановка событий на маршруты без QGIS.

Запись события несёт сырые значения из таблицы (текст пикета или число).
Цепочка: разбор записи -> пикет -> мера через систему пикетажа маршрута ->
координаты через геометрию маршрута. На каждом шаге возможна ошибка,
она уходит в список ошибок с ключом записи.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union

import numpy as np

from .chainage import ChainageSystem
from ..i18n import tr
from .errors import CoreError, ErrorCode
from .route import RouteGeometry
from .stations import Station, StationParser


@dataclass(frozen=True)
class EventRecord:
    key: object
    route_id: object
    raw_from: object
    raw_to: object = None
    offset: float = 0.0
    section: Optional[int] = None


@dataclass(frozen=True)
class PointResult:
    key: object
    route_id: object
    m: float
    station: float
    x: float
    y: float
    z: Optional[float]
    azimuth: float


@dataclass(frozen=True)
class LineResult:
    key: object
    route_id: object
    m_from: float
    m_to: float
    st_from: float
    st_to: float
    pieces: list
    swapped: bool          # «от» и «до» шли против направления маршрута


@dataclass(frozen=True)
class LocateResult:
    key: object
    route_id: object
    m: float
    station: float
    offset: float          # со знаком: + влево
    distance: float


@dataclass
class EventLocator:
    routes: dict
    parser: StationParser
    systems: dict = field(default_factory=dict)    # route_id -> ChainageSystem
    start_station: float = 0.0                     # для маршрутов без ведомости

    def system_for(self, rid) -> Optional[ChainageSystem]:
        sys_ = self.systems.get(rid)
        if sys_ is None and rid in self.routes:
            sys_ = ChainageSystem.from_length("по длине", self.routes[rid].length,
                                              self.start_station)
            self.systems[rid] = sys_
        return sys_

    # ------------------------------------------------------------ мера
    def _measure(self, raw, rid, section, prev: dict) -> Union[tuple[float, float], CoreError]:
        route = self.routes.get(rid)
        if route is None:
            return CoreError(ErrorCode.ROUTE_NOT_FOUND, tr("маршрут «{rid}» не найден").format(rid=rid))
        st = self.parser.parse(raw, prev.get(rid))
        if isinstance(st, CoreError):
            return st
        prev[rid] = st
        m = self.system_for(rid).to_measure(st.value, section)
        if isinstance(m, CoreError):
            return m
        if m < -1e-6 or m > route.length + 1e-6:
            return CoreError(ErrorCode.MEASURE_OUT_OF_RANGE,
                             tr("пикет {pk} даёт меру {m:.2f} при длине маршрута {L:.2f}").format(
                                 pk=self.parser.format(st.value), m=m, L=route.length))
        return min(max(m, 0.0), route.length), st.value

    # ------------------------------------------------------------ точки
    def locate_points(self, records: Iterable[EventRecord]
                      ) -> tuple[list[PointResult], list[CoreError]]:
        errors, prev = [], {}
        by_route: dict = {}
        for r in records:
            res = self._measure(r.raw_from, r.route_id, r.section, prev)
            if isinstance(res, CoreError):
                errors.append(res.with_key(r.key, r.route_id))
                continue
            by_route.setdefault(r.route_id, []).append((r, *res))
        out = []
        for rid, items in by_route.items():
            route = self.routes[rid]
            ms = np.array([m for _, m, _ in items])
            offs = np.array([float(r.offset or 0.0) for r, _, _ in items])
            p = route.points_at(ms, offs)
            for i, (r, m, st) in enumerate(items):
                z = float(p["z"][i])
                out.append(PointResult(r.key, rid, m, st, float(p["x"][i]), float(p["y"][i]),
                                       None if np.isnan(z) else z, float(p["azimuth"][i])))
        return out, errors

    # ------------------------------------------------------------ участки
    def locate_lines(self, records: Iterable[EventRecord]
                     ) -> tuple[list[LineResult], list[CoreError]]:
        out, errors, prev = [], [], {}
        for r in records:
            a = self._measure(r.raw_from, r.route_id, r.section, prev)
            b = self._measure(r.raw_to, r.route_id, r.section, prev) \
                if not isinstance(a, CoreError) else a
            if isinstance(b, CoreError):
                errors.append(b.with_key(r.key, r.route_id))
                continue
            (m0, s0), (m1, s1) = a, b
            swapped = m0 > m1
            if swapped:
                (m0, s0), (m1, s1) = (m1, s1), (m0, s0)
            if m1 - m0 <= 1e-6:
                errors.append(CoreError(ErrorCode.FROM_GE_TO, tr("участок нулевой длины"),
                                        r.key, r.route_id))
                continue
            pieces = self.routes[r.route_id].substring(m0, m1, float(r.offset or 0.0))
            if isinstance(pieces, CoreError):
                errors.append(pieces.with_key(r.key, r.route_id))
                continue
            out.append(LineResult(r.key, r.route_id, m0, m1, s0, s1, pieces, swapped))
        return out, errors

    # ------------------------------------------------------------ обратная задача
    def locate_xy(self, key, x: float, y: float, route_ids: Optional[Sequence] = None,
                  max_distance: Optional[float] = None) -> Union[LocateResult, CoreError]:
        best = None
        for rid in (route_ids if route_ids is not None else self.routes):
            route = self.routes.get(rid)
            if route is None:
                continue
            pr = route.locate(x, y)
            if isinstance(pr, CoreError):
                continue
            if best is None or abs(pr.offset) < abs(best[1].offset):
                best = (rid, pr)
        if best is None:
            return CoreError(ErrorCode.ROUTE_NOT_FOUND, tr("нет маршрута для привязки"), key)
        rid, pr = best
        if max_distance is not None and abs(pr.offset) > max_distance:
            return CoreError(ErrorCode.MEASURE_OUT_OF_RANGE,
                             tr("ближайший маршрут «{rid}» в {d:.2f} м, дальше радиуса {r:g}").format(
                                 rid=rid, d=abs(pr.offset), r=max_distance), key, rid)
        st = self.system_for(rid).to_station(pr.m)
        if isinstance(st, CoreError):
            return st.with_key(key, rid)
        return LocateResult(key, rid, pr.m, st, pr.offset, abs(pr.offset))
