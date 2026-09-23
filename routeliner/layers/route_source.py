"""Адаптер: объекты слоя маршрутов QGIS -> части для RouteAssembler.

Единственное место, где геометрия QGIS превращается в массивы numpy.
Мультилинии раскладываются на части, дуги (CircularString, CompoundCurve)
сегментируются по углу хорды (см. CURVE_ANGLE_DEG).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, Optional

import numpy as np
from qgis.core import (QgsAbstractGeometry, QgsCurve, QgsFeatureRequest,
                       QgsGeometry, QgsVectorLayer, QgsWkbTypes)

from ..core.assembler import RouteAssembler
from ..core.errors import CoreError
from .tables import _key

# В QGIS 4 перечисления стали вложенными (scoped); в 3.40 доступны оба вида.
_MAX_ANGLE = getattr(getattr(QgsAbstractGeometry, "SegmentationToleranceType", QgsAbstractGeometry),
                     "MaximumAngle")
# Дуги режутся по углу, а не по стреле прогиба: при смещении от оси ошибку
# даёт направление нормали, а не сама хорда. 0.02° на хорду — ошибка
# положения точки со смещением 15 м около 3 мм.
CURVE_ANGLE_DEG = 0.02


def geometry_parts(geom: QgsGeometry, curve_angle_deg: float = CURVE_ANGLE_DEG) -> list[np.ndarray]:
    """Все линейные части геометрии как массивы (N,2) или (N,3)."""
    if geom is None or geom.isEmpty():
        return []
    g: QgsAbstractGeometry = geom.constGet()
    has_z = QgsWkbTypes.hasZ(g.wkbType())
    out = []
    for part in _curves(g):
        if part.hasCurvedSegments():
            part = part.curveToLine(math.radians(curve_angle_deg), _MAX_ANGLE)
        n = part.numPoints()
        if n < 2:
            continue
        xs = [part.xAt(i) for i in range(n)]
        ys = [part.yAt(i) for i in range(n)]
        if has_z:
            zs = [part.zAt(i) for i in range(n)]
            out.append(np.column_stack([xs, ys, zs]))
        else:
            out.append(np.column_stack([xs, ys]))
    return out


def _curves(g: QgsAbstractGeometry) -> Iterable[QgsCurve]:
    if isinstance(g, QgsCurve):
        yield g
        return
    n = g.numGeometries() if hasattr(g, "numGeometries") else 0
    for i in range(n):
        sub = g.geometryN(i)
        if isinstance(sub, QgsCurve):
            yield sub


def read_routes(layer, id_field: str,
                curve_angle_deg: float = CURVE_ANGLE_DEG,
                route_ids: Optional[set] = None) -> dict[object, list[np.ndarray]]:
    """route_id -> части всех объектов с этим ID в порядке хранения."""
    fields = layer.fields()
    req = QgsFeatureRequest().setSubsetOfAttributes([fields.indexOf(id_field)])
    parts: dict[object, list[np.ndarray]] = defaultdict(list)
    for f in layer.getFeatures(req):
        rid = _key(f[id_field])
        if route_ids is not None and rid not in route_ids:
            continue
        parts[rid].extend(geometry_parts(f.geometry(), curve_angle_deg))
    return parts


def build_routes(source, id_field: str, assembler: RouteAssembler,
                 curve_angle_deg: float = CURVE_ANGLE_DEG, crs=None):
    """Собирает все маршруты источника (слой или QgsFeatureSource).
    Возвращает (маршруты, ошибки)."""
    crs = crs if crs is not None else (source.crs() if hasattr(source, "crs") else source.sourceCrs())
    geographic = crs.isGeographic()
    routes, errors = {}, []
    for rid, parts in read_routes(source, id_field, curve_angle_deg).items():
        if rid is None:
            continue
        r = assembler.build(rid, parts, geographic_crs=geographic)
        if isinstance(r, CoreError):
            errors.append(r)
        else:
            routes[rid] = r
    return routes, errors
