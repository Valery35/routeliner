"""Коды и записи ошибок ядра. Ошибки возвращаются как значения, а не исключения:
каждая запись события либо ставится на карту, либо попадает в слой ошибок."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    ROUTE_NOT_FOUND = "route_not_found"
    ROUTE_GAP = "route_gap"
    ROUTE_BRANCHING = "route_branching"
    GEOGRAPHIC_CRS = "geographic_crs"
    MEASURE_OUT_OF_RANGE = "measure_out_of_range"
    STATION_PARSE_FAILED = "station_parse_failed"
    STATION_OUT_OF_RANGE = "station_out_of_range"
    STATION_IN_GAP = "station_in_gap"          # пикет попал в прямую вставку
    STATION_AMBIGUOUS = "station_ambiguous"    # пикет попал в обратную вставку
    LEDGER_INVALID = "ledger_invalid"
    FROM_GE_TO = "from_ge_to"


@dataclass(frozen=True)
class CoreError:
    code: ErrorCode
    message: str
    key: object = None
    route_id: Optional[object] = None

    def with_key(self, key: object, route_id: object = None) -> "CoreError":
        return CoreError(self.code, self.message, key,
                         route_id if route_id is not None else self.route_id)


def is_error(value: object) -> bool:
    return isinstance(value, CoreError)
