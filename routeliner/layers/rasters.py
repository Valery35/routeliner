"""Значения растра в точках: окно растра читается в numpy одним блоком,
интерполяция билинейная (core.profile.bilinear)."""
from __future__ import annotations

import math

import numpy as np
from qgis.core import (Qgis, QgsCoordinateTransform, QgsPointXY, QgsRasterLayer,
                       QgsRectangle)

from ..core.profile import bilinear

_DTYPES = {
    Qgis.DataType.Byte: np.uint8, Qgis.DataType.UInt16: np.uint16,
    Qgis.DataType.Int16: np.int16, Qgis.DataType.UInt32: np.uint32,
    Qgis.DataType.Int32: np.int32, Qgis.DataType.Float32: np.float32,
    Qgis.DataType.Float64: np.float64,
}
if hasattr(Qgis.DataType, "Int8"):
    _DTYPES[Qgis.DataType.Int8] = np.int8


def sample(layer: QgsRasterLayer, xs, ys, src_crs, transform_context, band: int = 1) -> np.ndarray:
    """Значения растра в точках (xs, ys), заданных в системе координат src_crs.
    Снаружи растра и в ячейках без данных - NaN."""
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    out = np.full(len(xs), np.nan)
    if not len(xs) or layer is None or not layer.isValid():
        return out
    if src_crs != layer.crs():
        tr = QgsCoordinateTransform(src_crs, layer.crs(), transform_context)
        pts = [tr.transform(QgsPointXY(x, y)) for x, y in zip(xs, ys)]
        xs = np.array([p.x() for p in pts])
        ys = np.array([p.y() for p in pts])
    prov = layer.dataProvider()
    ext = layer.extent()
    dx, dy = layer.rasterUnitsPerPixelX(), layer.rasterUnitsPerPixelY()
    if dx <= 0 or dy <= 0:
        return out
    x0, y0 = ext.xMinimum(), ext.yMaximum()
    ncol, nrow = layer.width(), layer.height()
    c0 = max(int(math.floor((np.nanmin(xs) - x0) / dx)) - 2, 0)
    c1 = min(int(math.ceil((np.nanmax(xs) - x0) / dx)) + 2, ncol)
    r0 = max(int(math.floor((y0 - np.nanmax(ys)) / dy)) - 2, 0)
    r1 = min(int(math.ceil((y0 - np.nanmin(ys)) / dy)) + 2, nrow)
    if c1 <= c0 or r1 <= r0:
        return out
    win = QgsRectangle(x0 + c0 * dx, y0 - r1 * dy, x0 + c1 * dx, y0 - r0 * dy)
    block = prov.block(band, win, c1 - c0, r1 - r0)
    dt = _DTYPES.get(block.dataType())
    if dt is None:
        grid = np.array([[block.value(r, c) for c in range(c1 - c0)] for r in range(r1 - r0)],
                        dtype=float)
    else:
        grid = np.frombuffer(bytes(block.data()), dtype=dt).reshape(r1 - r0, c1 - c0).astype(float)
    nodata = None
    if block.hasNoDataValue():
        nodata = block.noDataValue()
    elif prov.sourceHasNoDataValue(band):
        nodata = prov.sourceNoDataValue(band)
    if nodata is not None and not math.isnan(nodata):
        grid = np.where(grid == nodata, np.nan, grid)
    return bilinear(grid, x0 + c0 * dx, y0 - r0 * dy, dx, -dy, xs, ys)
