"""Демонстрационный пример с эталонным ответом.

Геометрия задаётся аналитически (прямые и дуги окружности), поэтому
истинные координаты любой меры известны без участия модуля. Модуль
проверяется против этих значений, а не против самого себя.

Маршруты (СК EPSG:32640, район Перми):
  R1  прямая 2000 м на восток, с отметками Z (длина считается в плане)
  R2  прямая 500 м, дуга R=300 м на 90° влево, прямая 500 м; хранится
      настоящей дугой (CompoundCurve)
  R3  ломаная 4 x 400 м, хранится тремя объектами с произвольным порядком
      частей и одной перевёрнутой частью; для неё задана исполнительная
      ведомость с масштабом, обратной вставкой 25 м и прямой вставкой 40 м
  R4  две части с разрывом 15 м, должен попасть в ошибки сборки
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..i18n import tr

X0, Y0 = 455000.0, 6428000.0
CRS = "EPSG:32640"
SYSTEM = "исполнительная"

# Рельеф примера - наклонная плоскость. Билинейная интерполяция на плоскости
# точна, поэтому отметки профиля сверяются с формулой, а не с растром.
DEM_EXTENT = (X0 - 200.0, Y0 - 300.0, X0 + 3000.0, Y0 + 2100.0)   # xmin, ymin, xmax, ymax
DEM_CELL = 5.0


def dem_z(x: float, y: float) -> float:
    return 120.0 + 0.01 * (x - X0) + 0.02 * (y - Y0)


def r1_z(m: float) -> float:
    """Отметка оси R1 по Z вершин: 150 в начале, 170 в конце, линейно."""
    return 150.0 + m / 100.0


# ------------------------------------------------------------ аналитическая ось
@dataclass
class _Line:
    length: float


@dataclass
class _Arc:
    radius: float
    angle: float          # градусы, + влево


@dataclass
class Path:
    x: float
    y: float
    azimuth: float        # градусы от севера по часовой
    items: list = field(default_factory=list)

    @property
    def length(self) -> float:
        return sum(i.length if isinstance(i, _Line) else i.radius * math.radians(abs(i.angle))
                   for i in self.items)

    def at(self, m: float) -> tuple[float, float, float]:
        """(x, y, азимут) на мере m."""
        x, y, az = self.x, self.y, self.azimuth
        for it in self.items:
            if isinstance(it, _Line):
                d = min(m, it.length)
                x += d * math.sin(math.radians(az))
                y += d * math.cos(math.radians(az))
                if m <= it.length:
                    return x, y, az
                m -= it.length
            else:
                L = it.radius * math.radians(abs(it.angle))
                d = min(m, L)
                s = 1 if it.angle > 0 else -1           # влево = против часовой
                # центр слева (s=1) или справа от направления
                cx = x + it.radius * math.sin(math.radians(az - 90 * s))
                cy = y + it.radius * math.cos(math.radians(az - 90 * s))
                turn = math.degrees(d / it.radius) * s
                a0 = math.atan2(x - cx, y - cy)          # азимут из центра на точку
                a1 = a0 - math.radians(turn)
                x, y = cx + it.radius * math.sin(a1), cy + it.radius * math.cos(a1)
                az = (az - turn) % 360
                if m <= L:
                    return x, y, az
                m -= L
        return x, y, az

    def point(self, m: float, offset: float = 0.0) -> tuple[float, float]:
        x, y, az = self.at(m)
        # левая нормаль к направлению с азимутом az
        return (x - offset * math.cos(math.radians(az)),
                y + offset * math.sin(math.radians(az)))

    def vertices_m(self) -> list[float]:
        out, m = [0.0], 0.0
        for it in self.items:
            m += it.length if isinstance(it, _Line) else it.radius * math.radians(abs(it.angle))
            out.append(m)
        return out


def _xy(p: tuple[float, float]) -> str:
    return f"{p[0]:.4f} {p[1]:.4f}"


# ------------------------------------------------------------ пикетаж R3
# участки: (m_from, m_to, st_from, st_to) — то же, что должна построить ведомость
R3_SECTIONS = [
    (0.0, 400.0, 0.0, 399.6),
    (400.0, 700.0, 399.6, 699.3),
    (700.0, 1300.0, 674.3, 1274.3),        # обратная вставка 6+99.30 = 6+74.30
    (1300.0, 1600.0, 1314.3, 1614.3),      # прямая вставка 12+74.30 = 13+14.30
]


def r3_station(m: float) -> tuple[float, int]:
    for i, (m0, m1, s0, s1) in enumerate(R3_SECTIONS):
        if m0 <= m < m1 or (i == len(R3_SECTIONS) - 1 and m <= m1):
            return s0 + (m - m0) * (s1 - s0) / (m1 - m0), i
    raise ValueError(m)


def r3_measures(st: float) -> list[tuple[float, int]]:
    out = []
    for i, (m0, m1, s0, s1) in enumerate(R3_SECTIONS):
        if s0 <= st <= s1:
            out.append((m0 + (st - s0) * (m1 - m0) / (s1 - s0), i))
    return out


def pk(st: float, style: int = 0) -> str:
    n = math.floor(st / 100 + 1e-9)
    plus = st - n * 100
    if style == 1:
        return f"{n}+{plus:05.2f}".replace(".", ",")
    if style == 2:
        return f"пк{n}+{plus:.2f}"
    return f"ПК {n}+{plus:05.2f}"


# ------------------------------------------------------------ сборка примера
@dataclass
class Demo:
    paths: dict
    routes: list            # (route_id, name, wkt)
    ledger: list            # (route_id, system, station, measure, station_ahead, note)
    points: list            # dict
    lines: list             # dict
    defects: list           # dict


def build(n_points: int = 60, n_defects: int = 30, seed: int = 1) -> Demo:
    rnd = random.Random(seed)  # nosec B311
    P = {
        "R1": Path(X0, Y0, 90, [_Line(2000)]),
        "R2": Path(X0, Y0 + 500, 90, [_Line(500), _Arc(300, 90), _Line(500)]),
    }
    routes = []

    # R1 с Z: отметка растёт от 150 до 170
    a, b = P["R1"].point(0), P["R1"].point(2000)
    routes.append(("R1", tr("Прямая с отметками"),
                   f"LineStringZ({_xy(a)} 150, {_xy(P['R1'].point(1000))} 160, {_xy(b)} 170)"))

    # R2 — настоящая дуга
    r2 = P["R2"]
    s, e1, e2, end = r2.point(0), r2.point(500), r2.point(500 + 300 * math.pi / 2), r2.point(r2.length)
    mid = r2.point(500 + 300 * math.pi / 4)
    routes.append(("R2", tr("Кривая R=300"),
                   f"CompoundCurve(({_xy(s)}, {_xy(e1)}), CircularString({_xy(e1)}, {_xy(mid)}, "
                   f"{_xy(e2)}), ({_xy(e2)}, {_xy(end)}))"))

    # R3 — ломаная; своя функция точки, т.к. азимут меняется скачком
    r3v = [(X0, Y0 + 1500)]
    for az in (60, 120, 60, 120):
        x, y = r3v[-1]
        r3v.append((x + 400 * math.sin(math.radians(az)), y + 400 * math.cos(math.radians(az))))
    P["R3"] = _Polyline(r3v)
    v = [_xy(p) for p in r3v]
    routes.append(("R3", tr("Части в произвольном порядке"), f"MultiLineString(({v[3]}, {v[2]}), ({v[1]}, {v[2]}))"))
    routes.append(("R3", tr("Части в произвольном порядке"), f"LineString({v[3]}, {v[4]})"))
    routes.append(("R3", tr("Части в произвольном порядке"), f"LineString({v[0]}, {v[1]})"))

    # R4 — разрыв 15 м
    routes.append(("R4", tr("С разрывом"), f"LineString({X0 + 2500} {Y0}, {X0 + 2500} {Y0 + 300})"))
    routes.append(("R4", tr("С разрывом"), f"LineString({X0 + 2500} {Y0 + 315}, {X0 + 2500} {Y0 + 615})"))

    # ведомость R3: реперы с мерой и уравнения (у уравнений мера тоже известна)
    ledger = [
        ("R3", SYSTEM, "ПК 0+00", 0.0, None, tr("начало")),
        ("R3", SYSTEM, "ПК 3+99.60", 400.0, None, tr("репер, невязка -0.40")),
        ("R3", SYSTEM, "ПК 6+99.30", 700.0, "ПК 6+74.30", tr("обратная вставка 25 м")),
        ("R3", SYSTEM, "ПК 9+74.30", 1000.0, None, tr("репер")),
        ("R3", SYSTEM, "ПК 12+74.30", 1300.0, "ПК 13+14.30", tr("прямая вставка 40 м")),
        ("R3", SYSTEM, "ПК 16+14.30", 1600.0, None, tr("конец")),
    ]

    lengths = {"R1": 2000.0, "R2": r2.length, "R3": 1600.0}
    points = []

    def add_point(rid, text, m=None, offset=0.0, section=None, err="", note=""):
        ex = ey = None
        if m is not None and not err:
            ex, ey = P[rid].point(m, offset)
        points.append(dict(eid=len(points) + 1, route_id=rid, pk=text, offset=offset,
                           section=section, exp_m=m if not err else None,
                           exp_x=ex, exp_y=ey, exp_error=err, note=note))

    for i in range(n_points):
        rid = ("R1", "R2", "R3")[i % 3]
        m = rnd.uniform(0, lengths[rid])
        off = rnd.choice([0.0, 0.0, rnd.uniform(-15, 15)])
        # пикет в таблице записан с точностью 0.01 м — эталонная мера от него
        if rid == "R3":
            st, sec = r3_station(m)
            st = round(st, 2)
            cands = r3_measures(st)
            m = next(mm for mm, si in cands if si == sec) if any(si == sec for _, si in cands) \
                else cands[0][0]
            hint = sec if len(cands) > 1 else None
            add_point(rid, pk(st, i % 3), m, off, hint,
                      note=tr("в обратной вставке, указан участок") if hint is not None else "")
        else:
            m = round(m, 2)
            add_point(rid, pk(m, i % 3), m, off)

    add_point("R1", "ПК 7+10", 710.0, note=tr("опорный для относительной записи"))
    add_point("R1", "+55", 755.0, note=tr("относительная запись: тот же пикет"))
    add_point("R3", "ПК 6+80", err="station_ambiguous", note=tr("обратная вставка без участка"))
    add_point("R3", "ПК 12+90", err="station_in_gap", note=tr("попал в прямую вставку"))
    add_point("R1", "ПК 25+00", err="station_out_of_range", note=tr("за концом маршрута"))
    add_point("R1", "ПК 5+", err="station_parse_failed", note=tr("испорченная запись"))
    add_point("R9", "ПК 1+00", err="route_not_found", note=tr("нет такого маршрута"))
    add_point("R4", "ПК 1+00", err="route_not_found", note=tr("маршрут не собран: разрыв"))

    lines = []

    def add_line(rid, a, b, m0=None, m1=None, offset=0.0, err="", note=""):
        lines.append(dict(eid=len(lines) + 1, route_id=rid, pk_from=a, pk_to=b, offset=offset,
                          exp_m_from=m0, exp_m_to=m1, exp_error=err, note=note))

    add_line("R1", "ПК 2+00", "ПК 7+50", 200, 750, note=tr("простой участок"))
    add_line("R1", "ПК 9+00", "ПК 3+00", 300, 900, note=tr("записан против хода, меняется местами"))
    add_line("R2", "ПК 4+00", "ПК 11+00", 400, 1100, offset=10, note=tr("через дугу, смещение 10 м влево"))
    add_line("R3", "ПК 6+00", "ПК 8+00", r3_measures(600)[0][0], r3_measures(800)[0][0],
             note=tr("через обратную вставку"))
    add_line("R3", "ПК 2+00", "ПК 14+00", r3_measures(200)[0][0], r3_measures(1400)[0][0],
             note=tr("через обе вставки и изломы"))
    add_line("R1", "ПК 3+00", "ПК 3+00", err="from_ge_to", note=tr("нулевая длина"))

    defects = []
    for i in range(n_defects):
        rid = ("R1", "R2", "R3")[i % 3]
        verts = P[rid].vertices_m()
        while True:
            m = rnd.uniform(20, lengths[rid] - 20)
            if all(abs(m - v) > 40 for v in verts[1:-1]):
                break
        off = rnd.choice([-1, 1]) * rnd.uniform(1, 15)
        x, y = P[rid].point(m, off)
        st = r3_station(m)[0] if rid == "R3" else m
        defects.append(dict(did=i + 1, x=x, y=y, exp_route=rid, exp_m=m,
                            exp_station=st, exp_offset=off))

    return Demo(P, routes, ledger, points, lines, defects)


class _Polyline:
    """Аналитическая ломаная (точные координаты вершин)."""

    def __init__(self, verts):
        self.v = verts
        self.seg = [math.dist(a, b) for a, b in zip(verts, verts[1:])]

    @property
    def length(self):
        return sum(self.seg)

    def vertices_m(self):
        out = [0.0]
        for s in self.seg:
            out.append(out[-1] + s)
        return out

    def point(self, m, offset=0.0):
        for (a, b), s in zip(zip(self.v, self.v[1:]), self.seg):
            if m <= s + 1e-9:
                dx, dy = (b[0] - a[0]) / s, (b[1] - a[1]) / s
                return a[0] + dx * m - dy * offset, a[1] + dy * m + dx * offset
            m -= s
        a, b = self.v[-2], self.v[-1]
        s = self.seg[-1]
        dx, dy = (b[0] - a[0]) / s, (b[1] - a[1]) / s
        return b[0] - dy * offset, b[1] + dx * offset
