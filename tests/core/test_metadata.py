"""metadata.txt читается так же, как его читают каталог модулей и QGIS.

Каталог plugins.qgis.org и QGIS берут ConfigParser с подстановками по
умолчанию. Знак % в значении там ломает чтение - так 0.5.3 не прошла
в каталог из-за адреса домашней страницы в процент-кодировке.
"""
import configparser
import os

PATH = os.path.join(os.path.dirname(__file__), "..", "..", "routeliner", "metadata.txt")


def test_metadata_reads_with_default_interpolation():
    cp = configparser.ConfigParser()
    with open(PATH, encoding="utf-8") as f:
        cp.read_file(f)
    values = {k: cp.get("general", k) for k in cp.options("general")}
    for key in ("name", "version", "homepage", "tracker", "repository", "changelog"):
        assert values[key], key
    assert values["homepage"].startswith("https://www.informpp.ru/")
