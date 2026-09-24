"""Геометрия маршрута без QGIS: упорядоченные части, накопленные длины (numpy).

Маршрут — последовательность частей (полилиний). Мера m идёт непрерывно
по частям; разрывы между частями в длину не входят. Дуги к этому моменту
уже сегментированы адаптером слоя с заданным допуском.

Части могут нести четвёртый столбец M (мера вершины из геометрии LineStringM).
Он отделяется от координат при построении и хранится в measures: координаты
остаются (N, 2) или (N, 3), чтобы M не путался с Z.

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
    measures: Optional[list] = None     # M вершин по частям или None

    def __post_init__(self) -> None:
        self._split_m()
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

        def pad(arr):
            if arr.shape[1] >= dim:
                return arr
            return np.hstack([arr, np.full((len(arr), dim - arr.shape[1]), np.nan)])
        self._a = np.vstack([pad(s[0][:, :dim]) for s in segs if len(s[2])]) if m > 0 else np.zeros((0, dim))
        self._b = np.vstack([pad(s[1][:, :dim]) for s in segs if len(s[2])]) if m > 0 else np.zeros((0, dim))
        self._len = np.concatenate([s[2] for s in segs]) if segs else np.empty(0)
        self._m0 = np.concatenate([s[3] for s in segs]) if segs else np.empty(0)
        self._part = np.concatenate([s[4] for s in segs]).astype(int) if segs else np.empty(0, int)
        self._has_z = dim == 3

    def _split_m(self) -> None:
        """Отделяет столбец M: (x, y, z, m), где z может быть NaN."""
        if not any(np.asarray(c).ndim == 2 and np.asarray(c).shape[1] >= 4 for c in self.parts):
            return
        ms, parts = [], []
        for c in self.parts:
            c = np.asarray(c, dtype=float)
            if c.shape[1] >= 4:
                ms.append(c[:, 3].copy())
                c = c[:, :3] if not np.isnan(c[:, 2]).all() else c[:, :2]
            else:
                ms.append(np.full(len(c), np.nan))
            parts.append(c)
        self.parts = parts
        self.measures = ms if any(np.isfinite(m).any() for m in ms) else None

    @property
    def has_m(self) -> bool:
        return self.measures is not None

    def vertex_measures(self) -> list[tuple[float, float]]:
        """(мера по оси, M) для всех вершин по ходу маршрута, включая вершины
        с нулевым отрезком между ними: две такие вершины с разным M - это
        пикетажное уравнение. Пустой список, если у маршрута нет M."""
        if not self.has_m:
            return []
        out = []
        for pi, c in enumerate(self.parts):
            d = np.diff(c[:, :3] if self.use_z and c.shape[1] > 2 else c[:, :2], axis=0)
            ln = np.sqrt((d ** 2).sum(axis=1))
            m = self._part_m[pi][0] + np.concatenate(([0.0], np.cumsum(ln)))
            out.extend(zip(m.tolist(), self.measures[pi].tolist()))
        return out

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

    def vertices(self) -> dict:
        """Вершины маршрута по частям: мера, координаты и угол поворота в плане
        (градусы, плюс влево), а также изменение уклона по Z (безразмерное)."""
        ms, xs, ys, zs, turn, dgrade = [], [], [], [], [], []
        for pi in range(len(self._part_m)):
            idx = np.nonzero(self._part == pi)[0]
            if not len(idx):
                continue
            a, b = self._a[idx], self._b[idx]
            pts = np.vstack([a, b[-1:]])
            m = np.concatenate([self._m0[idx], [self._m0[idx[-1]] + self._len[idx[-1]]]])
            d = b[:, :2] - a[:, :2]
            az = np.arctan2(d[:, 1], d[:, 0])
            t = np.zeros(len(pts))
            if len(az) > 1:
                t[1:-1] = np.degrees((az[1:] - az[:-1] + np.pi) % (2 * np.pi) - np.pi)
            g = np.zeros(len(pts))
            if self._has_z and len(idx) > 1:
                h = np.maximum(np.hypot(d[:, 0], d[:, 1]), EPS)
                gr = (b[:, 2] - a[:, 2]) / h
                g[1:-1] = gr[1:] - gr[:-1]
            ms.append(m)
            xs.append(pts[:, 0])
            ys.append(pts[:, 1])
            zs.append(pts[:, 2] if self._has_z else np.full(len(pts), np.nan))
            turn.append(t)
            dgrade.append(np.nan_to_num(g))
        if not ms:
            e = np.empty(0)
            return dict(m=e, x=e, y=e, z=e, turn=e, dgrade=e)
        return dict(m=np.concatenate(ms), x=np.concatenate(xs), y=np.concatenate(ys),
                    z=np.concatenate(zs), turn=np.concatenate(turn), dgrade=np.concatenate(dgrade))

    # ------------------------------------------------------------ участки
    def substring(self, m_from: float, m_to: float,
                  offset: float = 0.0) -> Union[list[np.ndarray], CoreError]:
        """Участок маршрута как список полилиний (несколько — если участок
        проходит через разрыв между частями)."""
        r = self.substring_m(m_from, m_to, offset)
        return r if isinstance(r, CoreError) else [c for c, _ in r]

    def substring_m(self, m_from: float, m_to: float, offset: float = 0.0
                    ) -> Union[list[tuple[np.ndarray, np.ndarray]], CoreError]:
        """То же, что substring, и мера по оси каждой вершины куска."""
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
            ms = np.concatenate(([lo], self._m0[sel], [hi]))
            if offset:
                coords = offset_polyline(coords, offset)
            pieces.append((coords, ms))
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
