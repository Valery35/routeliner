# -*- coding: utf-8 -*-
# Routeliner - события на маршрутах и пикетаж (QGIS).
# © 2026 ООО «Информ++» (www.informpp.ru).
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Проверка готовности к выпуску. Перенесена из PlanetX (tools/preflight.py).

Смотрит на то, что обычно возвращает модератор каталога: заполненность
метаданных, лицензию, внешние зависимости, единый номер версии. Запуск
из корня репозитория:

    python tools/preflight.py          без сети
    python tools/preflight.py --net    ещё адреса и метки выпусков

Без сети проверяются и адреса metadata.txt: процент-кодировка (из-за неё
каталог не принял Routeliner 0.5.3), https, www у сайта Информ++, первая
запись поля changelog с номером версии. С --net адреса открываются, метки
выпусков берутся с GitHub, номер сверяется с ними - выданный номер закрыт.
Метки Routeliner пишутся без буквы v (AGENTS.md, раздел «Выпуск»), старая
метка v0.4.3 тоже учитывается.

Код возврата 1 означает ошибки. Замечания код возврата не меняют.
"""

import ast
import configparser
import importlib.util
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = "routeliner"
SKIP_DIRS = {"tests", "__pycache__"}

REQUIRED = ("name", "qgisMinimumVersion", "qgisMaximumVersion",
            "description", "version", "author", "email", "about",
            "repository", "tracker", "icon")

# Кроме стандартной библиотеки допустимы модули, которые есть в QGIS.
# osgeo - привязки GDAL, processing - модуль Processing из состава QGIS.
ALLOWED = {"qgis", "PyQt5", "PyQt6", "numpy", "osgeo", "processing"}

# Номер из трёх частей. Смотрим на соседние цифры и точки, а не на границу
# слова: «v0.5.4» и «routeliner-0.5.4.zip» находятся, 0.5.4.7 - не номер
# (шаблон PlanetX после нашей находки).
VERSION = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?!\.?\d)")
# Подвал README и руководства. Привязан к «Routeliner v», чтобы чужой номер
# в той же строке («Routeliner для RustGIS 0.1.1») не считался версией.
FOOTER = re.compile(r"\s*Routeliner v(\d+\.\d+\.\d+)(?!\.?\d)")
# Файлы, где номер версии модуля повторяется (AGENTS.md, «Проверка перед
# выпуском», пункт 3). Ищется номер в строке с именем модуля.
VERSION_FILES = ("README.md", "README.ru.md", "manual/manual.md",
                 "manual/manual_en.md")


def module_level_imports(path):
    """Имена всех модулей, которые файл импортирует, кроме запасного
    импорта в обработчике ImportError."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    fallback = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None \
                and ast.unparse(node.type) == "ImportError":
            for sub in ast.walk(node):
                fallback.add(id(sub))
    names = set()
    for node in ast.walk(tree):
        if id(node) in fallback:
            continue
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module \
                and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def plugin_files():
    for folder, dirs, files in os.walk(os.path.join(ROOT, PLUGIN)):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(folder, name)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def version_mentions():
    """Пары место и номер для упоминаний версии модуля в подвалах
    README и руководства и в первом разделе CHANGELOG.md."""
    found = []
    for name in VERSION_FILES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        for number, line in enumerate(read(path).split("\n"), 1):
            match = FOOTER.match(line)
            if match:
                found.append(("%s:%d" % (name, number), match.group(1)))
    changelog = os.path.join(ROOT, "CHANGELOG.md")
    if os.path.exists(changelog):
        for number, line in enumerate(read(changelog).split("\n"), 1):
            match = VERSION.search(line) if line.startswith("## ") else None
            if match:
                found.append(("CHANGELOG.md:%d" % number, match.group(1)))
                break
    return found


URL_FIELDS = ("homepage", "repository", "tracker")


def url_problems(general):
    """Адреса metadata.txt без сети. Каталог не принял Routeliner 0.5.3
    с адресом страницы в процент-кодировке (16 ноября 2026 года), адрес
    кириллицей он берёт. Сайт без www не открывается."""
    out = []
    for field in URL_FIELDS:
        url = general.get(field, "").strip()
        if not url:
            continue
        if re.search(r"%[0-9A-Fa-f]{2}", url):
            out.append("metadata.txt: %s в процент-кодировке, каталог её "
                       "не принимает - адрес пишется буквами" % field)
        if not url.startswith("https://"):
            out.append("metadata.txt: %s не https - %s" % (field, url))
        if re.match(r"https?://informpp\.ru", url):
            out.append("metadata.txt: %s без www, сайт так не открывается"
                       % field)
    return out


def url_answers(general):
    """Ответ сервера по адресам metadata.txt - только с ключом --net."""
    import urllib.error
    import urllib.parse
    import urllib.request
    out = []
    for field in URL_FIELDS:
        url = general.get(field, "").strip()
        if not url:
            continue
        parts = urllib.parse.urlsplit(url)
        wire = urllib.parse.urlunsplit(parts._replace(
            path=urllib.parse.quote(parts.path, safe="/")))
        request = urllib.request.Request(
            wire, headers={"User-Agent": "Routeliner release check"})
        try:
            with urllib.request.urlopen(request, timeout=20) as reply:
                status = reply.status
        except urllib.error.HTTPError as error:
            status = error.code
        except (urllib.error.URLError, OSError) as error:
            out.append("metadata.txt: %s не открылся - %s" % (field, error))
            continue
        if status >= 400:
            out.append("metadata.txt: %s ответил %d" % (field, status))
    return out


def number(text):
    return tuple(int(part) for part in text.split("."))


TAG = re.compile(r"v?(\d+\.\d+\.\d+)")


def tag_problems(version):
    """Номер версии против меток выпусков - только с ключом --net, метки
    сначала берутся с GitHub. Выданный номер закрыт: метка этого номера
    на другом коммите значит, что номер не подняли. Метки Routeliner без
    буквы v, метка с v того же номера тоже считается."""
    import gittool
    out = []
    try:
        try:
            gittool.git("fetch", "--tags", "--quiet", "origin")
        except gittool.GitError as error:
            out.append(("warn", "метки с GitHub не получены - %s"
                        % str(error).splitlines()[-1]))
        tags = [t.strip() for t in gittool.git("tag", "-l").splitlines()]
        valid = {t: TAG.fullmatch(t).group(1) for t in tags if TAG.fullmatch(t)}
        head = gittool.git("rev-parse", "HEAD").strip()
        for tag, num in sorted(valid.items()):
            if num != version:
                continue
            at = gittool.git("rev-list", "-n", "1", tag).strip()
            if at != head:
                out.append(("error", "номер %s уже выпущен меткой %s на "
                            "другом коммите - номер не поднят"
                            % (version, tag)))
        if valid:
            last = max(valid, key=lambda t: number(valid[t]))
            if number(version) < number(valid[last]):
                out.append(("error", "номер %s меньше последнего выпуска %s"
                            % (version, last)))
    except gittool.GitError as error:
        out.append(("error", "метки выпусков не прочитаны - %s" % error))
    return out


def check(net=False):
    """Списки ошибок и замечаний."""
    errors, warnings = [], []
    meta_path = os.path.join(ROOT, PLUGIN, "metadata.txt")
    cp = configparser.ConfigParser()
    cp.read(meta_path, encoding="utf-8")
    general = cp["general"]
    # Каталог и QGIS читают каждое поле с подстановкой, одиночный «%»
    # срывает загрузку в каталог.
    for field in general:
        try:
            general.get(field)
        except configparser.InterpolationError as error:
            errors.append("metadata.txt: поле %s - %s" % (field, error))

    raw = configparser.ConfigParser(interpolation=None)
    raw.read(meta_path, encoding="utf-8")
    plain = raw["general"]
    for field in REQUIRED:
        if not plain.get(field, "").strip():
            errors.append("metadata.txt: не заполнено поле %s" % field)
    if re.search(r"[А-Яа-яЁё]", plain.get("description", "")):
        warnings.append("description на русском, каталог международный")
    if plain.get("experimental", "").lower() not in ("false", ""):
        warnings.append("модуль помечен как experimental")

    maximum = plain.get("qgisMaximumVersion", "").strip()
    if maximum and int(maximum.split(".")[0]) < 4:
        errors.append("qgisMaximumVersion=%s не покрывает QGIS 4" % maximum)

    icon = plain.get("icon", "").strip()
    if icon and not os.path.exists(os.path.join(ROOT, PLUGIN, icon)):
        errors.append("нет файла значка %s/%s" % (PLUGIN, icon))

    for name in ("__init__.py", "metadata.txt", "LICENSE"):
        if not os.path.exists(os.path.join(ROOT, PLUGIN, name)):
            errors.append("нет файла %s/%s" % (PLUGIN, name))
    license_path = os.path.join(ROOT, "LICENSE")
    if not os.path.exists(license_path):
        errors.append("нет файла LICENSE")
    elif "GNU GENERAL PUBLIC LICENSE" not in read(license_path):
        errors.append("LICENSE не является текстом GPL")

    version = plain.get("version", "").strip()
    for place, mention in version_mentions():
        if mention != version:
            errors.append("%s: версия %s, в metadata.txt %s"
                          % (place, mention, version))
    log = plain.get("changelog", "").strip()
    if log and not log.startswith(version + " "):
        errors.append("metadata.txt: changelog начинается не с %s" % version)

    errors += url_problems(plain)
    if net:
        errors += url_answers(plain)
        for level, text in tag_problems(version):
            (errors if level == "error" else warnings).append(text)

    allowed = ALLOWED | set(sys.stdlib_module_names)
    for path in plugin_files():
        for module in sorted(module_level_imports(path) - allowed):
            errors.append("%s: внешний импорт %s"
                          % (os.path.relpath(path, ROOT), module))
    return version, errors, warnings


def main(argv=()):
    net = "--net" in argv
    version, errors, warnings = check(net)
    if importlib.util.find_spec("pyflakes") is None:
        warnings.append("pyflakes не установлен, анализ кода пропущен")
    else:
        out = subprocess.run(
            [sys.executable, "-m", "pyflakes", os.path.join(ROOT, PLUGIN)],
            capture_output=True, text=True, timeout=120)
        for line in out.stdout.splitlines():
            if line.strip():
                warnings.append("pyflakes: " + line.strip())

    print("Проверка готовности Routeliner %s" % (version or "?"))
    if errors:
        print("\nОшибки:")
        for line in errors:
            print("  " + line)
    if warnings:
        print("\nЗамечания:")
        for line in warnings:
            print("  " + line)
    if not errors and not warnings:
        print("\nВсё в порядке.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
