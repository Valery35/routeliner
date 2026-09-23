"""Продольный профиль без QGIS: точки профиля, значения растров, уклоны и
раскладка чертежа.

Чертёж строится в миллиметрах бумаги. По горизонтали X = (m - m0) * 1000 / H,
где H - знаменатель горизонтального масштаба, по вертикали над сеткой
Y = (z - горизонт) * 1000 / V. Строки сетки идут вниз от Y = 0. В компоновке
QGIS такой чертёж печатается в натуральную величину при масштабе карты 1:1000,
потому что одна единица карты (метр) равна миллиметру бумаги.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from ..i18n import tr

PRIORITY = {"start": 6, "end": 6, "equation": 5, "event": 4, "picket": 3, "vertex": 2, "step": 1}
MERGE_TOL = 0.01          # точки ближе этого по мере сливаются, м


# ============================================================ точки профиля
@dataclass
class ProfilePoint:
    m: float
    kind: str
    label: str = ""
    turn: float = 0.0             # угол поворота трассы в вершине, градусы, + влево
    station: float = math.nan
    station_ahead: float = math.nan   # только для уравнения
    section: int = 0

    @property
    def priority(self) -> int:
        return PRIORITY.get(self.kind, 0)


def collect_points(route, system, picket_step: float = 100.0, step: float = 0.0,
                   vertices: str = "significant", turn_tol: float = 1.0,
                   grade_tol: float = 0.001, events: Sequence[tuple[float, str]] = ()
                   ) -> list[ProfilePoint]:
    """Точки профиля одного маршрута: начало и конец, пикетажные уравнения,
    события, целые пикеты, вершины оси и точки с постоянным шагом.

    vertices: "all" - все вершины, "significant" - только с поворотом в плане
    больше turn_tol градусов или с изломом уклона больше grade_tol,
    "none" - без вершин. Вершины нарезанных дуг поворачивают на сотые доли
    градуса и в режиме significant не попадают в профиль."""
    L = route.length
    pts = [ProfilePoint(0.0, "start"), ProfilePoint(L, "end")]
    for m, back, ahead in system.equations():
        pts.append(ProfilePoint(m, "equation", station=back, station_ahead=ahead))
    for m, label in events:
        if -MERGE_TOL <= m <= L + MERGE_TOL:
            pts.append(ProfilePoint(min(max(m, 0.0), L), "event", label=label or ""))
    if picket_step > 0:
        for m, _, _ in system.whole_stations(picket_step):
            if 0 <= m <= L:
                pts.append(ProfilePoint(m, "picket"))
    if vertices != "none":
        v = route.vertices()
        for m, t, g in zip(v["m"], v["turn"], v["dgrade"]):
            if vertices == "all" or abs(t) > turn_tol or abs(g) > grade_tol:
                pts.append(ProfilePoint(float(m), "vertex", turn=float(t)))
    if step > 0:
        for k in range(1, int(L // step) + 1):
            pts.append(ProfilePoint(k * step, "step"))

    pts.sort(key=lambda p: (p.m, -p.priority))
    merged: list[ProfilePoint] = []
    for p in pts:
        if merged and p.m - merged[-1].m <= MERGE_TOL:
            q = merged[-1]
            if p.priority > q.priority:
                p.label = p.label or q.label
                p.turn = p.turn or q.turn
                merged[-1] = p
            else:
                q.label = q.label or p.label
                q.turn = q.turn or p.turn
            continue
        merged.append(p)

    starts = [s.m_from for s in system.sections]
    for p in merged:
        if p.kind == "equation":
            p.section = max(0, bisect.bisect_right(starts, p.m + 1e-9) - 1)
            continue
        i = max(0, bisect.bisect_right(starts, p.m + 1e-9) - 1)
        p.section = i
        p.station = system.sections[i].station_at(p.m)
    return merged


# ============================================================ растры
def bilinear(grid: np.ndarray, x0: float, y0: float, dx: float, dy: float,
             xs, ys, nodata: Optional[float] = None) -> np.ndarray:
    """Билинейная интерполяция по центрам ячеек растра.

    x0, y0 - левый верхний угол растра, dx > 0, dy < 0 (как в GDAL).
    Снаружи растра и в ячейках без данных результат NaN. Если без данных
    только часть из четырёх соседних ячеек, вес делится между остальными."""
    g = np.asarray(grid, dtype=float)
    if nodata is not None and not math.isnan(nodata):
        g = np.where(g == nodata, np.nan, g)
    rows, cols = g.shape
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    fc = (xs - x0) / dx - 0.5
    fr = (ys - y0) / dy - 0.5
    inside = (fc >= -0.5) & (fc <= cols - 0.5) & (fr >= -0.5) & (fr <= rows - 0.5)
    # у края растра (пол-ячейки) линейная экстраполяция по двум крайним ячейкам
    c0 = np.clip(np.floor(fc).astype(int), 0, max(cols - 2, 0))
    r0 = np.clip(np.floor(fr).astype(int), 0, max(rows - 2, 0))
    c1, r1 = np.minimum(c0 + 1, cols - 1), np.minimum(r0 + 1, rows - 1)
    tc, tr_ = fc - c0, fr - r0
    vals = np.stack([g[r0, c0], g[r0, c1], g[r1, c0], g[r1, c1]])
    w = np.stack([(1 - tc) * (1 - tr_), tc * (1 - tr_), (1 - tc) * tr_, tc * tr_])
    ok = ~np.isnan(vals)
    w = np.where(ok, w, 0.0)
    ws = w.sum(axis=0)
    out = np.where(ws > 1e-12, (np.where(ok, vals, 0.0) * w).sum(axis=0) / np.where(ws > 1e-12, ws, 1), np.nan)
    return np.where(inside, out, np.nan)


# ============================================================ уклоны
@dataclass
class GradeSegment:
    m0: float
    m1: float
    z0: float
    z1: float

    @property
    def length(self) -> float:
        return self.m1 - self.m0

    @property
    def grade(self) -> float:
        """Уклон в промилле, плюс - подъём по ходу маршрута."""
        return (self.z1 - self.z0) / self.length * 1000.0 if self.length > 0 else 0.0


def grade_segments(ms, zs, tolerance: float = 0.02) -> list[GradeSegment]:
    """Разбивает линию (m, z) на участки постоянного уклона упрощением
    Дугласа - Пекера по вертикали с допуском tolerance (м). Точки без
    значения разрывают линию."""
    ms, zs = np.asarray(ms, dtype=float), np.asarray(zs, dtype=float)
    out: list[GradeSegment] = []
    ok = ~np.isnan(zs)
    i = 0
    n = len(ms)
    while i < n:
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and ok[j + 1]:
            j += 1
        if j > i:
            keep = _dp(ms[i:j + 1], zs[i:j + 1], tolerance)
            idx = [i + k for k in keep]
            for a, b in zip(idx, idx[1:]):
                if ms[b] - ms[a] > 1e-9:
                    out.append(GradeSegment(float(ms[a]), float(ms[b]), float(zs[a]), float(zs[b])))
        i = j + 1
    return out


def _dp(x: np.ndarray, y: np.ndarray, tol: float) -> list[int]:
    keep = {0, len(x) - 1}
    stack = [(0, len(x) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        xa, ya, xb, yb = x[a], y[a], x[b], y[b]
        seg = x[a + 1:b]
        yl = ya + (yb - ya) * (seg - xa) / (xb - xa) if xb != xa else np.full(len(seg), ya)
        d = np.abs(y[a + 1:b] - yl)
        k = int(np.argmax(d))
        if d[k] > tol:
            c = a + 1 + k
            keep.add(c)
            stack += [(a, c), (c, b)]
    return sorted(keep)


# ============================================================ подписи
def thin(xs_mm: Sequence[float], priorities: Sequence[int], min_gap: float) -> np.ndarray:
    """Выбирает точки, подписи которых не налезают друг на друга: сначала
    берутся точки с большим приоритетом, затем остальные, если до уже
    выбранных не меньше min_gap мм."""
    xs = np.asarray(xs_mm, dtype=float)
    order = sorted(range(len(xs)), key=lambda i: (-priorities[i], xs[i]))
    taken: list[float] = []
    mask = np.zeros(len(xs), dtype=bool)
    for i in order:
        k = bisect.bisect_left(taken, xs[i])
        if (k > 0 and xs[i] - taken[k - 1] < min_gap - 1e-9) or \
                (k < len(taken) and taken[k] - xs[i] < min_gap - 1e-9):
            continue
        taken.insert(k, xs[i])
        mask[i] = True
    return mask


def text_width(text: str, size: float) -> float:
    """Оценка ширины подписи в мм для решения, помещается ли она."""
    return 0.62 * size * max(len(t) for t in str(text).split("\n")) + 0.5


# ============================================================ чертёж
ROW_TYPES = ("value", "text", "grade", "distance", "station", "plan")
PALETTE = ["#8c6d1f", "#2e7d32", "#000000", "#1f4fbf", "#b23b3b", "#6a3d9a", "#e08000"]


@dataclass
class Row:
    title: str
    kind: str                       # один из ROW_TYPES
    height: float = 15.0            # мм, 0 - строка не выводится в сетку
    decimals: int = 2
    draw: bool = False              # рисовать линию над сеткой (для value)
    values: Optional[np.ndarray] = None               # value, grade: по всем точкам
    segments: list = field(default_factory=list)      # text: (m0, m1, текст)
    tolerance: float = 0.02         # grade: допуск упрощения, м
    color: str = ""


@dataclass
class Sheet:
    lines: list = field(default_factory=list)   # (coords, kind, row, color, width)
    texts: list = field(default_factory=list)   # (x, y, text, rot, size, halign, valign, kind)
    marks: list = field(default_factory=list)   # (x, y, kind, label)
    horizon: float = 0.0
    width: float = 0.0


class ProfileDrawer:
    HEADER = 60.0         # ширина колонки заголовков, мм
    GAP = 5.0             # промежуток между заголовками и сеткой, мм
    TEXT = 2.5            # высота подписи, мм
    TITLE = 3.0

    def __init__(self, points: list[ProfilePoint], station_labels: Sequence[str],
                 h_scale: float = 500.0, v_scale: float = 100.0,
                 horizon: Optional[float] = None, min_gap: float = 3.0,
                 plan_points: Sequence[tuple[float, float, str]] = ()):
        self.p = points
        self.ms = np.array([p.m for p in points], dtype=float)
        self.m0 = float(self.ms[0]) if len(self.ms) else 0.0
        self.labels = list(station_labels)
        self.H, self.V = float(h_scale), float(v_scale)
        self.horizon = horizon
        self.min_gap = min_gap
        self.plan_points = list(plan_points)
        self.xs = self.x(self.ms)
        self.take = thin(self.xs, [p.priority for p in points], min_gap)

    def x(self, m):
        return (np.asarray(m, dtype=float) - self.m0) * 1000.0 / self.H

    def y(self, z):
        return (np.asarray(z, dtype=float) - self.sheet.horizon) * 1000.0 / self.V

    # ------------------------------------------------------------ основа
    def build(self, rows: list[Row]) -> Sheet:
        s = self.sheet = Sheet()
        s.width = float(self.xs[-1]) if len(self.xs) else 0.0
        drawn = [r for r in rows if r.kind == "value" and r.draw and r.values is not None
                 and np.isfinite(r.values).any()]
        zmin = min((np.nanmin(r.values) for r in drawn), default=0.0)
        zmax = max((np.nanmax(r.values) for r in drawn), default=zmin + 1.0)
        s.horizon = float(self.horizon) if self.horizon is not None else math.floor(zmin) - 1.0

        grid = [r for r in rows if r.height > 0 and self._has_content(r)]
        y = 0.0
        W = s.width
        xl = -self.HEADER - self.GAP
        self._line([(xl, 0), (-self.GAP, 0)], "frame")
        self._line([(0, 0), (W, 0)], "frame")
        for r in grid:
            top, bottom = y, y - r.height
            self._text(xl + 1.5, (top + bottom) / 2, r.title, 0, self.TITLE, "Left", "Half", "title")
            getattr(self, "_row_" + r.kind)(r, top, bottom)
            self._line([(xl, bottom), (-self.GAP, bottom)], "frame")
            self._line([(0, bottom), (W, bottom)], "frame")
            y = bottom
        for xx in (xl, -self.GAP):
            self._line([(xx, 0), (xx, y)], "frame")
        for xx in (0.0, W):
            self._line([(xx, 0), (xx, y)], "frame")

        top_y = np.full(len(self.ms), -np.inf)
        for i, r in enumerate(drawn):
            color = r.color or PALETTE[i % len(PALETTE)]
            yy = self.y(r.values)
            for chunk in _chunks(self.xs, yy):
                self._line(chunk, "surface", r.title, color, 0.35)
            top_y = np.fmax(top_y, np.where(np.isfinite(yy), yy, -np.inf))
        for i in np.nonzero(self.take)[0]:
            if np.isfinite(top_y[i]):
                self._line([(self.xs[i], 0), (self.xs[i], top_y[i])], "ordinate")
        self._events(top_y)
        self._scale_bar(zmax)
        return s

    def _has_content(self, r: Row) -> bool:
        if r.kind in ("value", "grade"):
            return r.values is not None and bool(np.isfinite(r.values).any())
        if r.kind == "text":
            return bool(r.segments)
        return True

    def _line(self, coords, kind, row="", color="#000000", width=0.1):
        self.sheet.lines.append(([(float(a), float(b)) for a, b in coords], kind, row, color, width))

    def _text(self, x, y, text, rot=0, size=None, halign="Center", valign="Half", kind="text"):
        self.sheet.texts.append((float(x), float(y), text, float(rot), size or self.TEXT,
                                 halign, valign, kind))

    def _vtext(self, x, top, bottom, text, kind):
        """Вертикальная подпись по центру строки. Длинная подпись (пикетажное
        уравнение) уменьшается, чтобы уместиться в высоту строки."""
        size = self.TEXT
        room = top - bottom - 1.0
        need = text_width(text, size)
        if need > room > 0:
            size = max(1.2, size * room / need)
        self._text(x, (top + bottom) / 2, text, 270, size, "Center", "Half", kind)

    # ------------------------------------------------------------ строки
    def _row_value(self, r: Row, top, bottom):
        for i in np.nonzero(self.take)[0]:
            v = r.values[i]
            if np.isfinite(v):
                self._vtext(self.xs[i], top, bottom, f"{v:.{r.decimals}f}", "value")

    def _row_station(self, r: Row, top, bottom):
        for i in np.nonzero(self.take)[0]:
            self._line([(self.xs[i], top), (self.xs[i], top - 1.5)], "tick")
            # пикетажное уравнение пишется в две строки: ПК назад = / ПК вперёд
            self._vtext(self.xs[i], top - 1.5, bottom, self.labels[i].replace(" = ", " =\n"), "station")

    def _row_distance(self, r: Row, top, bottom):
        idx = np.nonzero(self.take)[0]
        for i in idx:
            self._line([(self.xs[i], top), (self.xs[i], bottom)], "tick")
        for a, b in zip(idx, idx[1:]):
            d = self.ms[b] - self.ms[a]
            text = f"{d:.{r.decimals}f}".rstrip("0").rstrip(".") if r.decimals else f"{d:.0f}"
            if self.xs[b] - self.xs[a] >= text_width(text, self.TEXT):
                self._text((self.xs[a] + self.xs[b]) / 2, (top + bottom) / 2, text, kind="distance")

    def _row_text(self, r: Row, top, bottom):
        lo, hi = self.ms[0], self.ms[-1]
        for m0, m1, text in r.segments:
            a, b = max(min(m0, m1), lo), min(max(m0, m1), hi)
            if b <= a:
                continue
            xa, xb = self.x(a), self.x(b)
            for xx in (xa, xb):
                self._line([(xx, top), (xx, bottom)], "tick")
            text = str(text or "")
            if text and xb - xa >= text_width(text, self.TEXT):
                self._text((xa + xb) / 2, (top + bottom) / 2, text, kind="section")

    def _row_grade(self, r: Row, top, bottom):
        for g in grade_segments(self.ms, r.values, r.tolerance):
            xa, xb = float(self.x(g.m0)), float(self.x(g.m1))
            for xx in (xa, xb):
                self._line([(xx, top), (xx, bottom)], "tick")
            gr = g.grade
            if abs(gr) < 0.05:
                self._line([(xa, (top + bottom) / 2), (xb, (top + bottom) / 2)], "grade")
            elif gr > 0:
                self._line([(xa, bottom), (xb, top)], "grade")
            else:
                self._line([(xa, top), (xb, bottom)], "grade")
            gt = f"{abs(gr):.{r.decimals}f}" if r.decimals else f"{abs(gr):.0f}"
            lt = f"{g.length:.0f}" if g.length >= 10 else f"{g.length:.1f}"
            w = xb - xa
            if w >= max(text_width(gt, self.TEXT), text_width(lt, self.TEXT)) + 2:
                h = top - bottom
                if gr >= 0:
                    self._text(xa + 1, top - h * 0.25, gt, 0, self.TEXT, "Left", "Half", "grade")
                    self._text(xb - 1, bottom + h * 0.25, lt, 0, self.TEXT, "Right", "Half", "grade")
                else:
                    self._text(xb - 1, top - h * 0.25, gt, 0, self.TEXT, "Right", "Half", "grade")
                    self._text(xa + 1, bottom + h * 0.25, lt, 0, self.TEXT, "Left", "Half", "grade")

    def _row_plan(self, r: Row, top, bottom):
        mid = (top + bottom) / 2
        half = (top - bottom) / 2 - 1.0
        self._line([(0, mid), (self.sheet.width, mid)], "plan_axis", r.title, "#000000", 0.35)
        # план схематичный: смещения сжимаются, чтобы самая дальняя точка
        # поместилась в строку, но не растягиваются сверх масштаба чертежа
        inside = [abs(off) for m, off, _ in self.plan_points if self.ms[0] <= m <= self.ms[-1]]
        k_off = 1000.0 / self.H
        if inside and max(inside) * k_off > half:
            k_off = half / max(inside)
        k = 0
        for i, p in enumerate(self.p):
            if p.kind == "vertex" and abs(p.turn) >= 1.0:
                k += 1
                side = tr("влево") if p.turn > 0 else tr("вправо")
                self._line([(self.xs[i], mid - 1.5), (self.xs[i], mid + 1.5)], "plan_turn")
                self._text(self.xs[i] + 0.8, mid - 1.0,
                           tr("ВУ{n} {a:.1f}° {side}").format(n=k, a=abs(p.turn), side=side),
                           0, self.TEXT, "Left", "Top", "plan_turn")
        for m, off, label in self.plan_points:
            if not (self.ms[0] - 1e-6 <= m <= self.ms[-1] + 1e-6):
                continue
            xx = float(self.x(m))
            yy = mid + off * k_off
            self.sheet.marks.append((xx, yy, "plan_point", label or ""))
            if label:
                self._text(xx + 1.0, yy, str(label), 0, self.TEXT, "Left", "Half", "plan_label")

    # ------------------------------------------------------------ верх
    def _events(self, top_y):
        for i, p in enumerate(self.p):
            if p.kind != "event" or not p.label:
                continue
            base = top_y[i] if np.isfinite(top_y[i]) else 0.0
            self._line([(self.xs[i], base), (self.xs[i], base + 4.0)], "leader")
            self._text(self.xs[i], base + 5.0, p.label, 270, self.TEXT, "Left", "Half", "event")

    def _scale_bar(self, zmax):
        xb = -self.GAP - 2.0
        z0 = self.sheet.horizon
        z1 = math.ceil(max(zmax, z0 + 1.0))
        step = next(s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)
                    if s * 1000.0 / self.V >= 5.0)
        z = z0
        ytop = float(self.y(z1))
        self._line([(xb, 0), (xb, ytop)], "scale")
        while z <= z1 + 1e-9:
            yy = float(self.y(z))
            self._line([(xb - 1.5, yy), (xb, yy)], "scale")
            self._text(xb - 2.0, yy, f"{z:.2f}", 0, self.TEXT, "Right", "Half", "scale")
            z += step
        xl = -self.HEADER - self.GAP + 1.5
        for k, t in enumerate((tr("Условный горизонт {z:.2f}").format(z=z0),
                               tr("М 1:{v:g} по вертикали").format(v=self.V),
                               tr("М 1:{h:g} по горизонтали").format(h=self.H))):
            self._text(xl, 3.0 + k * 6.0, t, 0, self.TEXT, "Left", "Half", "caption")


def _chunks(xs, ys):
    """Непрерывные куски линии без NaN."""
    cur = []
    for x, y in zip(xs, ys):
        if np.isfinite(y):
            cur.append((x, y))
        else:
            if len(cur) > 1:
                yield cur
            cur = []
    if len(cur) > 1:
        yield cur
