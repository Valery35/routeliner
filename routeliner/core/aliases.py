# -*- coding: utf-8 -*-
#
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
#
"""Псевдонимы полей: словари и разбор ссылок, без QGIS и без GDAL.

Имена полей от языка не зависят, иначе проект, собранный в русском QGIS,
в английском развалится: выражения, стили подписей и динамические слои
ссылаются на имена. По-русски говорят псевдонимы.

Здесь лежит то, что можно проверить без QGIS: сами словари, выбор
псевдонима по имени поля и разбор ссылки на слой GeoPackage. Установка
псевдонимов на слой и запись их в файл - в processing/common.py.
"""

# Поля результата модуля. Псевдоним ставится всегда: префикс rl_ и exp_
# занят модулем, чужого поля с таким именем не бывает.
ALIASES = {
    "rl_m": "Мера, м", "rl_pk": "Пикет", "rl_x": "X", "rl_y": "Y", "rl_azimuth": "Азимут, °",
    "rl_m_from": "Мера начала, м", "rl_m_to": "Мера конца, м", "rl_length": "Длина участка, м",
    "rl_pk_from": "Пикет начала", "rl_pk_to": "Пикет конца", "rl_swapped": "Начало и конец поменяны",
    "rl_route": "Маршрут", "rl_offset": "Смещение от оси, м", "rl_side": "Сторона",
    "rl_error": "Код ошибки", "rl_message": "Пояснение ошибки",
    "exp_m": "Эталон, мера, м", "exp_x": "Эталон, X", "exp_y": "Эталон, Y",
    "exp_error": "Эталон, код ошибки", "exp_m_from": "Эталон, мера начала, м",
    "exp_m_to": "Эталон, мера конца, м", "exp_route": "Эталон, маршрут",
    "exp_station": "Эталон, пикетаж, м", "exp_offset": "Эталон, смещение, м",
}
# Простые имена получают псевдоним только в слоях, целиком созданных модулем,
# чтобы не переименовать чужое поле с тем же именем в таблице событий.
PLAIN_ALIASES = {
    "route_id": "ID маршрута", "length": "Длина по оси, м", "parts": "Частей",
    "gaps": "Разрывов", "gap_max": "Наибольший разрыв, м", "pk": "Пикет",
    "station": "Пикетаж", "m": "Мера, м", "section": "Участок пикетажа",
    "azimuth": "Азимут, °", "km": "Целый километр", "n": "Номер точки", "kind": "Вид",
    "station_ahead": "Пикетаж вперёд", "x": "X", "y": "Y", "z_axis": "Отметка оси, м",
    "turn": "Угол поворота, °", "label": "Подпись", "row": "Строка сетки", "color": "Цвет",
    "width": "Толщина линии, мм", "text": "Текст", "rot": "Поворот, °",
    "size": "Высота текста, мм", "halign": "Выравнивание по горизонтали",
    "valign": "Выравнивание по вертикали", "name": "Название", "system": "Система пикетажа",
    "measure": "Мера, м", "note": "Примечание", "eid": "Номер события", "did": "Номер точки",
    "offset": "Смещение от оси, м", "pk_from": "Пикет начала", "pk_to": "Пикет конца",
    "st_from": "Пикетаж начала, м", "st_to": "Пикетаж конца, м",
    "sections": "Участков пикетажа", "equations": "Пикетажных уравнений",
    "source": "Источник пикетажа",
    "fid": "fid",
}

RASTER_ALIAS = "Растр {name}"       # поля z_<имя растра> в таблице профиля


def is_raster_field(name):
    """Поле отметки растра в таблице профиля: z_<имя>, кроме z_axis."""
    return name.startswith("z_") and name != "z_axis"


def layer_is_ours(names):
    """Слой целиком создан модулем: все имена полей известны."""
    return all(n in ALIASES or n in PLAIN_ALIASES or n.startswith("z_") for n in names)


def alias_source(name, own):
    """Русский исходник псевдонима для поля или None.

    `own` - слой целиком создан модулем. Простые имена вроде `name` или
    `offset` получают псевдоним только в таком слое: в чужой таблице
    событий поле с тем же именем принадлежит человеку, и подписывать
    его своим текстом нельзя.
    """
    if name in ALIASES:
        return ALIASES[name]
    if not own:
        return None
    if name in PLAIN_ALIASES:
        return None if name == "fid" else PLAIN_ALIASES[name]
    if is_raster_field(name):
        return RASTER_ALIAS
    return None


def all_alias_sources():
    """Все русские исходники псевдонимов, для сверки «свой или чужой»."""
    return set(ALIASES.values()) | set(PLAIN_ALIASES.values()) | {RASTER_ALIAS}


def split_gpkg_ref(ref):
    """(путь, имя слоя или None) для ссылки на GeoPackage, иначе None.

    Ссылка приходит двумя видами. От загрузки в проект - с именем слоя,
    `C:/путь/файл.gpkg|layername=x`. От приёмника результата - одним
    путём, и тогда имя слоя разбирает тот, кто открывает файл. Память,
    shapefile и прочее сюда не попадают: псевдоним в файл умеет только
    GeoPackage.
    """
    if not isinstance(ref, str) or not ref:
        return None
    path, sep, tail = ref.partition("|layername=")
    if not path.lower().endswith(".gpkg"):
        return None
    if not sep:
        return (path, None)
    name = tail.split("|")[0].strip()
    return (path, name or None)
