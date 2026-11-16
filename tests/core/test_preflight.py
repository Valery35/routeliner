"""Сторожа проверки перед выпуском tools/preflight.py, без сети.

Каталог модулей QGIS не принял Routeliner 0.5.3 - адрес страницы в
metadata.txt был в процент-кодировке. Выданный номер версии закрыт.
git здесь подменён. Сюда же влит прежний test_metadata.py.
"""
import configparser
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gittool  # noqa: E402
import preflight  # noqa: E402


# ------------------------------------------------------------ сам модуль
def test_metadata_reads_with_default_interpolation():
    """Каталог и QGIS читают metadata.txt ConfigParser с подстановками."""
    cp = configparser.ConfigParser()
    cp.read(os.path.join(ROOT, "routeliner", "metadata.txt"), encoding="utf-8")
    values = {k: cp.get("general", k) for k in cp.options("general")}
    assert values["homepage"].startswith("https://www.informpp.ru/")


def test_module_passes_offline_check():
    version, errors, _ = preflight.check(net=False)
    assert version and not errors, errors


def test_version_found_in_every_place():
    places = {p.split(":")[0] for p, _ in preflight.version_mentions()}
    assert places == {"README.md", "README.ru.md", "manual/manual.md",
                      "manual/manual_en.md", "CHANGELOG.md"}


# ------------------------------------------------------------ адреса
def test_percent_encoding_is_error():
    found = preflight.url_problems({
        "homepage": "https://www.informpp.ru/%D0%B3%D0%BB/qgis-routeliner"})
    assert any("процент" in f for f in found), found


def test_letters_without_www_and_http():
    assert preflight.url_problems({
        "homepage": "https://www.informpp.ru/главная-страница/qgis-routeliner",
        "tracker": "https://github.com/Valery35/routeliner/issues"}) == []
    found = preflight.url_problems({
        "homepage": "https://informpp.ru/routeliner",
        "repository": "http://github.com/Valery35/routeliner"})
    assert len(found) == 2, found


# ------------------------------------------------------------ метки
def run_with(tags, head, tag_at, version):
    answers = {"tag": "\n".join(tags), "rev-parse": head,
               "rev-list": tag_at, "fetch": ""}

    def fake(*args):
        return answers[args[0]]
    saved = gittool.git
    gittool.git = fake
    try:
        return [text for level, text in preflight.tag_problems(version)
                if level == "error"]
    finally:
        gittool.git = saved


def test_new_number_passes():
    assert run_with(["0.5.3", "0.5.4", "v0.4.3"], "a", "b", "0.5.5") == []


def test_released_number_on_other_commit():
    assert len(run_with(["0.5.4"], "a", "b", "0.5.4")) == 1


def test_released_number_with_v_tag():
    assert len(run_with(["v0.4.3"], "a", "b", "0.4.3")) == 1


def test_tagged_head_passes():
    assert run_with(["0.5.4"], "a", "a", "0.5.4") == []


def test_number_below_last_release():
    # номера сравниваются числами: 0.10.0 больше 0.9.0
    found = run_with(["0.9.0", "0.10.0"], "a", "b", "0.9.5")
    assert len(found) == 1 and "0.10.0" in found[0], found
