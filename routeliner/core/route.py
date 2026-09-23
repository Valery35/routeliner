"""Геометрия маршрута без QGIS: упорядоченные части, накопленные длины (numpy).

Маршрут — последовательность частей (полилиний). Мера m идёт непрерывно
по частям; разрывы между частями в длину не входят. Дуги к этому моменту
уже сегментированы адаптером слоя с заданным допуском.

Смещение: положительное — влево по направлению маршрута.
Азимут: в градусах от севера (оси Y) по часовой стрелке.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence, Union

import numpy as np

from ..i18n import tr
from .errors import CoreError, ErrorCode

EPS = 1e-9


@dataclass(frozen=True)
class RouteGap:
    """Разрыв между частями: мера, где он стоит, и его длина по прямой."""
    m: float
    distance: float


@dataclass(frozen=True)
class LocatedPoint:
    x: float
    y: float
    z: Optional[float]
    azimuth: float


@dataclass(frozen=True)
class Projection:
    """Результат привязки точки к маршруту."""
    m: float
    offset: float          # со знаком: + влево
    x: float
    y: float
    part: int


@dataclass
class RouteGeometry:
    route_id: object
    parts: list[np.ndarray]            # (N, 2) или (N, 3), N >= 2
    use_z: bool = False
    gaps: list[RouteGap] = field(default_factory=list)

    def __post_init__(self) -> None:
        segs = []
        m = 0.0
        self._part_m: list[tuple[float, float]] = []
        for pi, c in enumerate(self.parts):
            c = np.asarray(c, dtype=float)
            self.parts[pi] = c
            d = np.diff(c[:, :3] if self.use_z and c.shape[1] > 2 else c[:, :2], axis=0)
            ln = np.sqrt((d ** 2).sum(axis=1))
            keep = ln > EPS
            a, b, ln = c[:-1][keep], c[1:][keep], ln[keep]
            m0 = m + np.concatenate(([0.0], np.cumsum(ln)[:-1])) if len(ln) else np.empty(0)
            segs.append((a, b, ln, m0, np.full(len(ln), pi)))
            self._part_m.append((m, m + float(ln.sum())))
            m += float(ln.sum())
        self.length = m
        dim = 3 if any(c.shape[1] > 2 for c in self.parts) else 2
        pad = lambda arr: arr if arr.shape[1] >= dim else np.hstack(
            [arr, np.full((len(arr), dim - arr.shape[1]), np.nan)])
        self._a = np.vstack([pad(s[0][:, :dim]) for s in segs if len(s[2])]) if m > 0 else np.zeros((0, dim))
        self._b = np.vstack([pad(s[1][:, :dim]) for s in segs if len(s[2])]) if m > 0 else np.zeros((0, dim))
        self._len = np.concatenate([s[2] for s in segs]) if segs else np.empty(0)
        self._m0 = np.concatenate([s[3] for s in segs]) if segs else np.empty(0)
        self._part = np.concatenate([s[4] for s in segs]).astype(int) if segs else np.empty(0, int)
        self._has_z = dim == 3

    # ------------------------------------------------------------ точки
    def _check(self, m: float) -> Optional[CoreError]:
        if self.length <= 0:
            return CoreError(ErrorCode.ROUTE_NOT_FOUND, tr("маршрут нулевой длины"),
                             route_id=self.route_id)
        if m < -1e-6 or m > self.length + 1e-6:
            return CoreError(ErrorCode.MEASURE_OUT_OF_RANGE,
                             tr("мера {m:.3f} вне 0..{L:.3f}").format(m=m, L=self.length),
                             route_id=self.route_id)
        return None

    def points_at(self, ms: Sequence[float], offsets=0.0) -> dict:
        """Пакетный расчёт. Возвращает массивы x, y, z, azimuth и маску ok
        (мера внутри маршрута). Основной путь для больших таблиц."""
        ms = np.asarray(ms, dtype=float)
        off = np.broadcast_to(np.asarray(offsets, dtype=float), ms.shape)
        ok = (ms >= -1e-6) & (ms <= self.length + 1e-6) & (self.length > 0)
        n = len(self._m0)
        if n == 0:
            nan = np.full(ms.shape, np.nan)
            return dict(x=nan, y=nan, z=nan, azimuth=nan, ok=ok & False)
        i = np.clip(np.searchsorted(self._m0, np.clip(ms, 0, self.length), side="right") - 1, 0, n - 1)
        t = np.clip((ms - self._m0[i]) / self._len[i], 0.0, 1.0)
        a, b = self._a[i], self._b[i]
        p = a + (b - a) * t[:, None]
        dx, dy = (b - a)[:, 0], (b - a)[:, 1]
        h = np.hypot(dx, dy)
        h = np.where(h > EPS, h, 1.0)
        nx, ny = -dy / h, dx / h                     # левая нормаль
        x = p[:, 0] + nx * off
        y = p[:, 1] + ny * off
        z = p[:, 2] if self._has_z else np.full(ms.shape, np.nan)
        az = np.degrees(np.arctan2(dx, dy)) % 360.0
        return dict(x=x, y=y, z=z, azimuth=az, ok=ok)

    def point_at(self, m: float, offset: float = 0.0) -> Union[LocatedPoint, CoreError]:
        err = self._check(m)
        if err:
            return err
        r = self.points_at([m], offset)
        z = float(r["z"][0])
        return LocatedPoint(float(r["x"][0]), float(r["y"][0]),
                            None if math.isnan(z) else z, float(r["azimuth"][0]))

    # ------------------------------------------------------------ участки
    def substring(self, m_from: float, m_to: float,
                  offset: float = 0.0) -> Union[list[np.ndarray], CoreError]:
        """Участок маршрута как список полилиний (несколько — если участок
        проходит через разрыв между частями)."""
        if m_from >= m_to:
            return CoreError(ErrorCode.FROM_GE_TO,
                             tr("начало {a:.3f} не меньше конца {b:.3f}").format(a=m_from, b=m_to),
                             route_id=self.route_id)
        for m in (m_from, m_to):
            err = self._check(m)
            if err:
                return err
        pieces = []
        for pi, (p0, p1) in enumerate(self._part_m):
            lo, hi = max(m_from, p0), min(m_to, p1)
            if hi - lo <= 1e-9:
                continue
            sel = np.nonzero((self._part == pi) & (self._m0 > lo + 1e-9)
                             & (self._m0 < hi - 1e-9))[0]
            start, end = self._in_part(lo, pi), self._in_part(hi, pi)
            coords = np.vstack([start, self._a[sel], end]) if len(sel) else np.vstack([start, end])
            if offset:
                coords = offset_polyline(coords, offset)
            pieces.append(coords)
        return pieces

    def _in_part(self, m: float, pi: int) -> np.ndarray:
        """Точка с мерой m строго внутри части pi (на стыке частей важно,
        с какой стороны разрыва её брать)."""
        idx = np.nonzero(self._part == pi)[0]
        k = int(np.clip(np.searchsorted(self._m0[idx], m, side="right") - 1, 0, len(idx) - 1))
        j = idx[k]
        t = min(max((m - self._m0[j]) / self._len[j], 0.0), 1.0)
        return self._a[j] + (self._b[j] - self._a[j]) * t

    # ------------------------------------------------------------ привязка
    def locate(self, x: float, y: float) -> Union[Projection, CoreError]:
        """Ближайшая точка маршрута: мера и смещение со знаком (+ влево)."""
        if not len(self._m0):
            return CoreError(ErrorCode.ROUTE_NOT_FOUND, tr("маршрут нулевой длины"),
                             route_id=self.route_id)
        a, b = self._a[:, :2], self._b[:, :2]
        d = b - a
        dd = (d ** 2).sum(axis=1)
        t = np.clip(((x - a[:, 0]) * d[:, 0] + (y - a[:, 1]) * d[:, 1]) / dd, 0, 1)
        px, py = a[:, 0] + d[:, 0] * t, a[:, 1] + d[:, 1] * t
        dist = np.hypot(x - px, y - py)
        i = int(np.argmin(dist))
        cross = d[i, 0] * (y - a[i, 1]) - d[i, 1] * (x - a[i, 0])
        sign = 1.0 if cross >= 0 else -1.0
        return Projection(float(self._m0[i] + t[i] * self._len[i]),
                          sign * float(dist[i]), float(px[i]), float(py[i]),
                          int(self._part[i]))


def offset_polyline(coords: np.ndarray, offset: float,
                    miter_limit: float = 4.0) -> np.ndarray:
    """Параллельная полилиния (+ влево) со срезанием острых углов.
    Простой вариант без устранения самопересечений: для больших смещений на
    крутых кривых адаптер QGIS использует offsetCurve с проверкой."""
    c = np.asarray(coords, dtype=float)
    xy = c[:, :2]
    d = np.diff(xy, axis=0)
    h = np.hypot(d[:, 0], d[:, 1])
    h[h < EPS] = 1.0
    n = np.column_stack([-d[:, 1] / h, d[:, 0] / h])      # нормаль каждого сегмента
    vn = np.vstack([n[:1], n[:-1] + n[1:], n[-1:]])       # биссектрисы в вершинах
    ln = np.hypot(vn[:, 0], vn[:, 1])
    ln[ln < EPS] = 1.0
    vn = vn / ln[:, None]
    seg_n = np.vstack([n[:1], n])
    cos_half = (vn * seg_n).sum(axis=1)
    k = np.minimum(1.0 / np.maximum(cos_half, 1.0 / miter_limit), miter_limit)
    out = c.copy()
    out[:, :2] = xy + vn * (offset * k)[:, None]
    return out
