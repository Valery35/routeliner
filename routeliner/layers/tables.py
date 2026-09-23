"""Чтение таблиц событий и ведомостей из любого источника QGIS
(слой, CSV, Excel, GeoPackage, PostGIS — всё, что открывается как QgsFeatureSource)."""
from __future__ import annotations

from typing import Optional

from qgis.core import QgsFeatureSource

from ..core.chainage import ChainageSystem
from ..core.errors import CoreError, ErrorCode
from ..core.events import EventRecord
from ..core.stations import StationParser


def _null(v) -> bool:
    return v is None or (hasattr(v, "isNull") and v.isNull()) or str(v) == "NULL"


def _num(v) -> Optional[float]:
    if _null(v) or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def _key(v):
    """ID маршрута как ключ: '12', 12 и 12.0 из Excel должны совпадать."""
    if _null(v):
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def read_events(source: QgsFeatureSource, route_field: str, from_field: str,
                to_field: Optional[str] = None, offset_field: Optional[str] = None,
                section_field: Optional[str] = None, offset_sign: float = 1.0):
    """Записи событий в порядке таблицы и словарь объектов по ключу записи."""
    records, feats = [], {}
    for f in source.getFeatures():
        off = _num(f[offset_field]) if offset_field else None
        sec = _num(f[section_field]) if section_field else None
        records.append(EventRecord(
            f.id(), _key(f[route_field]),
            None if _null(f[from_field]) else f[from_field],
            (None if _null(f[to_field]) else f[to_field]) if to_field else None,
            offset_sign * (off or 0.0),
            int(sec) if sec is not None else None))
        feats[f.id()] = f
    return records, feats


def read_ledger(source: QgsFeatureSource, parser: StationParser, route_field: str,
                station_field: str, measure_field: Optional[str],
                ahead_field: Optional[str] = None, system_field: Optional[str] = None,
                system_name: Optional[str] = None,
                route_lengths: Optional[dict] = None):
    """Системы пикетажа по маршрутам из ведомости. Возвращает (системы, ошибки)."""
    rows: dict = {}
    errors = []
    for f in source.getFeatures():
        if system_field and system_name and str(f[system_field]).strip() != system_name:
            continue
        rid = _key(f[route_field])
        st = parser.parse(f[station_field])
        if isinstance(st, CoreError):
            errors.append(st.with_key(f.id(), rid))
            continue
        ahead = None
        if ahead_field and not _null(f[ahead_field]) and str(f[ahead_field]).strip():
            a = parser.parse(f[ahead_field])
            if isinstance(a, CoreError):
                errors.append(a.with_key(f.id(), rid))
                continue
            ahead = a.value
        m = _num(f[measure_field]) if measure_field else None
        rows.setdefault(rid, []).append((st.value, m, ahead))
    systems = {}
    for rid, rr in rows.items():
        length = (route_lengths or {}).get(rid)
        s = ChainageSystem.from_table(system_name or "ведомость", rr, length)
        if isinstance(s, CoreError):
            errors.append(s.with_key(None, rid))
        else:
            systems[rid] = s
    return systems, errors
