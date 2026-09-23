"""Сборка маршрута из частей.

На вход — полилинии (массивы вершин) всех объектов с одним ID маршрута,
в порядке хранения. Мультилинии адаптер слоя уже разложил на части,
дуги уже сегментировал. Порядок хранения ничего не значит: части
упорядочиваются по топологии (совпадению концов в пределах допуска).

Направление маршрута: то, при котором большая по длине доля частей
сохраняет своё направление оцифровки; reverse=True переворачивает итог.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union

import numpy as np

from ..i18n import tr
from .errors import CoreError, ErrorCode
from .route import RouteGap, RouteGeometry


@dataclass
class _Part:
    coords: np.ndarray
    length: float


class RouteAssembler:
    def __init__(self, snap_tolerance: float = 0.01, allow_gaps: bool = False,
                 use_z: bool = False, reverse: bool = False) -> None:
        self.tol = float(snap_tolerance)
        self.allow_gaps = allow_gaps
        self.use_z = use_z
        self.reverse = reverse

    def build(self, route_id: object, parts: Sequence[Sequence[Sequence[float]]],
              geographic_crs: bool = False) -> Union[RouteGeometry, CoreError]:
        if geographic_crs:
            return self._err(ErrorCode.GEOGRAPHIC_CRS, route_id,
                             tr("длины в географической системе координат считаются в "
                                "градусах. Перепроецируйте маршруты в метрическую СК"))
        ps = []
        for c in parts:
            c = np.asarray(c, dtype=float)
            if c.ndim != 2 or len(c) < 2:
                continue
            ln = float(np.hypot(*np.diff(c[:, :2], axis=0).T).sum())
            if ln > 0:
                ps.append(_Part(c, ln))
        if not ps:
            return self._err(ErrorCode.ROUTE_NOT_FOUND, route_id, tr("нет геометрии"))

        chains = self._chains(ps, route_id)
        if isinstance(chains, CoreError):
            return chains
        if len(chains) > 1 and not self.allow_gaps:
            d = self._nearest_gap(chains)
            return self._err(ErrorCode.ROUTE_GAP, route_id,
                             tr("маршрут распадается на {n} куска, ближайший разрыв {d:.3f} "
                                "больше допуска {t:g}").format(n=len(chains), d=d, t=self.tol))
        chains = [self._orient(ch) for ch in chains]
        chains = self._order_chains(chains)
        coords = [self._merge(ch) for ch in chains]
        if self.reverse:
            coords = [c[::-1] for c in coords[::-1]]
        gaps, m = [], 0.0
        for a, b in zip(coords, coords[1:]):
            m += float(np.hypot(*np.diff(a[:, :2], axis=0).T).sum())
            gaps.append(RouteGap(m, float(np.hypot(*(b[0, :2] - a[-1, :2])))))
        return RouteGeometry(route_id, coords, use_z=self.use_z, gaps=gaps)

    # ------------------------------------------------------------ топология
    def _chains(self, ps: list[_Part], route_id) -> Union[list[list[tuple[int, bool]]], CoreError]:
        """Цепочки частей: список (индекс части, перевёрнута ли) по порядку."""
        ends = np.array([[p.coords[0, :2], p.coords[-1, :2]] for p in ps]).reshape(-1, 2)
        # узлы: кластеризация концов по допуску
        node = -np.ones(len(ends), int)
        centers = []
        for i, e in enumerate(ends):
            for k, c in enumerate(centers):
                if np.hypot(*(e - c)) <= self.tol:
                    node[i] = k
                    break
            else:
                node[i] = len(centers)
                centers.append(e)
        deg = np.bincount(node, minlength=len(centers))
        if (deg > 2).any():
            k = int(np.argmax(deg))
            x, y = centers[k]
            return self._err(ErrorCode.ROUTE_BRANCHING, route_id,
                             tr("в точке ({x:.2f}, {y:.2f}) сходятся {n} конца частей").format(
                                 x=x, y=y, n=deg[k]))
        adj: dict[int, list[tuple[int, int]]] = {}
        for pi in range(len(ps)):
            a, b = node[2 * pi], node[2 * pi + 1]
            adj.setdefault(a, []).append((pi, b))
            adj.setdefault(b, []).append((pi, a))
        used = [False] * len(ps)
        chains = []
        # сначала цепочки от висячих концов, затем замкнутые кольца
        starts = [n for n in range(len(centers)) if deg[n] == 1] + list(range(len(centers)))
        for s in starts:
            for pi, _ in adj.get(s, []):
                if used[pi]:
                    continue
                chain, cur = [], s
                while True:
                    nxt = [(q, other) for q, other in adj.get(cur, []) if not used[q]]
                    if not nxt:
                        break
                    q, other = nxt[0]
                    used[q] = True
                    chain.append((q, node[2 * q] != cur))   # перевёрнута, если входим с конца
                    cur = other
                chains.append(chain)
        self._ps = ps
        return chains

    def _orient(self, chain):
        keep = sum(self._ps[q].length for q, rev in chain if not rev)
        flip = sum(self._ps[q].length for q, rev in chain if rev)
        if flip > keep:
            chain = [(q, not rev) for q, rev in reversed(chain)]
        return chain

    def _endpoints(self, chain):
        q0, r0 = chain[0]
        q1, r1 = chain[-1]
        c0, c1 = self._ps[q0].coords, self._ps[q1].coords
        return (c0[-1] if r0 else c0[0])[:2], (c1[0] if r1 else c1[-1])[:2]

    def _order_chains(self, chains):
        """Куски при разрывах: начинаем с куска, содержащего первую часть в
        порядке хранения, дальше жадно к ближайшему началу; куски,
        оказавшиеся «позади», ставятся в начало."""
        if len(chains) == 1:
            return chains
        first = next(i for i, ch in enumerate(chains) if any(q == 0 for q, _ in ch))
        order = [first]
        rest = [i for i in range(len(chains)) if i != first]
        while rest:
            head, tail = self._endpoints(chains[order[0]])[0], self._endpoints(chains[order[-1]])[1]
            fwd = min(rest, key=lambda i: np.hypot(*(self._endpoints(chains[i])[0] - tail)))
            back = min(rest, key=lambda i: np.hypot(*(self._endpoints(chains[i])[1] - head)))
            dfwd = np.hypot(*(self._endpoints(chains[fwd])[0] - tail))
            dback = np.hypot(*(self._endpoints(chains[back])[1] - head))
            if dfwd <= dback:
                order.append(fwd); rest.remove(fwd)
            else:
                order.insert(0, back); rest.remove(back)
        return [chains[i] for i in order]

    def _merge(self, chain) -> np.ndarray:
        out = []
        for q, rev in chain:
            c = self._ps[q].coords
            c = c[::-1] if rev else c
            out.append(c if not out else c[1:])     # общий узел не дублируем
        return np.vstack(out)

    def _nearest_gap(self, chains) -> float:
        pts = [p for ch in chains for p in self._endpoints(ch)]
        best = np.inf
        for i in range(0, len(pts), 2):
            for j in range(0, len(pts), 2):
                if i != j:
                    for a in pts[i:i + 2]:
                        for b in pts[j:j + 2]:
                            best = min(best, float(np.hypot(*(a - b))))
        return best

    @staticmethod
    def _err(code, route_id, msg) -> CoreError:
        return CoreError(code, msg, route_id=route_id)
