"""Сборщик эталонов режет дугу R2 так же, как QGIS.

Эталон qgis_arc_r2.json снят в QGIS 4.2.3 (curveToLine с наибольшим углом
0,02° на хорду). QGIS делит угол дуги на целое число равных шагов. Прежняя
нарезка шла постоянным шагом с коротким остатком, вершины уходили от QGIS
до 0,23 мм, и эталон 1.01 давал 1,6 мм расхождения вместо 2,0 мм у QGIS.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

import make_fixtures as F  # noqa: E402
from routeliner.core import demo as D  # noqa: E402


def test_arc_like_qgis():
    with open(os.path.join(HERE, "qgis_arc_r2.json"), encoding="utf-8") as f:
        ref = json.load(f)
    d = D.build(n_points=F.N_POINTS, n_defects=F.N_DEFECTS, seed=F.SEED)
    wkt = next(w for rid, _, w in d.routes if rid == "R2")
    old = F.ARC_ANGLE_DEG
    F.ARC_ANGLE_DEG = ref["angle_deg"]
    try:
        part = F.wkt_parts(wkt)[0]
    finally:
        F.ARC_ANGLE_DEG = old
    assert len(part) == ref["n_vertices"]
    worst = max(math.hypot(part[int(i)][0] - x, part[int(i)][1] - y)
                for i, (x, y) in ref["vertices"].items())
    assert worst < 1e-6, worst
