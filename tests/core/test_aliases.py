# -*- coding: utf-8 -*-
"""Псевдонимы полей: словари и разбор ссылок, без QGIS.

Проверяется то, что можно проверить headless. Сама запись псевдонима
в GeoPackage требует GDAL и QGIS, её закрывает живой прогон 1.01 из
раздела «Проверка перед выпуском».
"""
import ast
import glob
import os
import re

from routeliner.core.aliases import (ALIASES, PLAIN_ALIASES, alias_source,
                                     all_alias_sources, is_raster_field,
                                     layer_is_ours, split_gpkg_ref)
from routeliner.translations import TRANSLATIONS

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "routeliner")


def _written_fields():
    """Имена полей, которые модуль создаёт: fld(...) и QgsField(...)."""
    out = {}
    for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            if fn not in ("fld", "QgsField") or not node.args:
                continue
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.setdefault(a.value, os.path.basename(path))
    return out


def test_every_written_field_has_an_alias():
    """У каждого поля, которое пишет модуль, есть русская подпись.

    Поле без псевдонима видно в таблице атрибутов латиницей, и в русском
    QGIS это заметно сразу. Список полей собирается из исходников, чтобы
    новое поле без псевдонима не проходило тест.
    """
    written = _written_fields()
    assert len(written) > 30, "полей подозрительно мало: %d" % len(written)
    bad = [n for n in written if alias_source(n, True) is None and n != "fid"]
    assert not bad, "нет псевдонима: %s" % sorted(bad)


def test_plain_names_are_left_alone_in_foreign_layers():
    """Простое имя подписывается только в слое, созданном модулем.

    В чужой таблице событий поле `offset` или `name` принадлежит человеку,
    и своей подписью его накрывать нельзя. А поля с префиксом rl_ и exp_
    наши в любом слое.
    """
    assert alias_source("offset", True) == "Смещение от оси, м"
    assert alias_source("offset", False) is None
    assert alias_source("name", False) is None
    assert alias_source("rl_m", False) == "Мера, м"
    assert alias_source("exp_m", False) == "Эталон, мера, м"
    assert alias_source("совсем чужое поле", True) is None


def test_fid_stays_without_an_alias():
    """Служебный ключ GeoPackage подписывать нечем и незачем."""
    assert alias_source("fid", True) is None
    assert layer_is_ours(["fid", "route_id", "pk"])
    assert not layer_is_ours(["fid", "route_id", "своё поле"])


def test_raster_fields_are_recognised():
    """Отметка растра в таблице профиля: z_<имя>, кроме отметки оси."""
    assert is_raster_field("z_dem")
    assert not is_raster_field("z_axis")
    assert alias_source("z_axis", True) == "Отметка оси, м"
    assert "{name}" in alias_source("z_dem", True)


def test_every_alias_has_an_english_pair():
    """Псевдоним без перевода показал бы русское слово в английском QGIS.

    Подписи вроде «X» и «fid» на обоих языках одинаковы, в словарь они
    не попадают вовсе, и требовать для них пару незачем.
    """
    cyr = re.compile("[А-Яа-яЁё]")
    missing = [s for s in all_alias_sources()
               if cyr.search(s) and s not in TRANSLATIONS]
    assert not missing, sorted(missing)


def test_split_gpkg_ref():
    """Разбор ссылки на слой: с именем слоя, без имени и мимо GeoPackage."""
    assert split_gpkg_ref("C:/d/a.gpkg|layername=routes") == ("C:/d/a.gpkg", "routes")
    assert split_gpkg_ref("C:/d/a.gpkg") == ("C:/d/a.gpkg", None)
    assert split_gpkg_ref("C:/d/A.GPKG|layername=x") == ("C:/d/A.GPKG", "x")
    assert split_gpkg_ref("memory:Пикеты") is None
    assert split_gpkg_ref("C:/d/a.shp") is None
    assert split_gpkg_ref("") is None
    assert split_gpkg_ref(None) is None


def test_dictionaries_do_not_overlap():
    """Одно имя не должно стоять в обоих словарях: правило выбора станет
    зависеть от порядка проверки, а это чинят потом полдня."""
    both = set(ALIASES) & set(PLAIN_ALIASES)
    assert not both, sorted(both)
