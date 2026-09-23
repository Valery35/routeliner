"""Сборка routeliner/translations.py: английские строки по началу русского ключа.
Запуск из корня репозитория: python tools/make_translations.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from i18n_keys import SKIP, SKIP_PREFIX, extract
keys = extract()
EN = {
# about / menu
"О модуле": "About",
"Руководство не найдено.": "The manual is not found.",
"События на маршрутах и пикетаж для QGIS": "Route events and chainage for QGIS",
"Руководство (PDF)": "Manual (PDF)",
# assembler
"длины в географической": "lengths in a geographic coordinate system are measured in degrees. Reproject the routes to a metric CRS",
"нет геометрии": "no geometry",
"маршрут распадается на": "the route falls apart into {n} pieces, the nearest gap {d:.3f} exceeds the tolerance {t:g}",
"в точке (": "{n} part ends meet at the point ({x:.2f}, {y:.2f})",
# chainage
"нужно не меньше двух реперов": "at least two ledger points are needed",
"ведомость пуста": "the ledger is empty",
"система «{name}»": "system «{name}»: {why}",
"ПК {st:.2f} вне пикетажа маршрута": "station {st:.2f} is outside the route chainage",
"не удалось разместить уравнения": "the station equations {eqs} could not be placed",
"мера {m:.3f} вне {a:.3f}": "measure {m:.3f} is outside {a:.3f}..{b:.3f}",
"ПК {st:.2f} встречается": "station {st:.2f} occurs {n} times (backward equation), specify the section",
"два репера с одной мерой": "two ledger points with the same measure m={m:.3f}",
"пикетаж не растёт": "chainage does not increase on the section m {a:.2f}..{b:.2f}, from {s0:.2f} to {s1:.2f}",
"нет участка {n}": "no section {n}",
"ПК {st:.2f} вне участка": "station {st:.2f} is outside section {n} ({a:.2f}..{b:.2f})",
"ПК {st:.2f} попал в прямую вставку": "station {st:.2f} falls into the forward equation gap {a:.2f}={b:.2f}",
"уравнение {b}={a} не помещается": "the equation {b}={a} does not fit between the ledger points m {m0:.2f} and {m1:.2f}",
"у репера ПК": "the ledger point at station {st:.2f} has no measure",
"репер ПК {st:.2f} (m={m:.2f})": "the ledger point at station {st:.2f} (m={m:.2f}) lies in the backward equation {b}={a}, and its side is unknown. Give the equation position as a measure",
# demo data
"Прямая с отметками": "Straight line with elevations",
"Кривая R=300": "Curve R=300",
"Части в произвольном порядке": "Parts in arbitrary order",
"С разрывом": "With a gap",
"начало": "start",
"репер, невязка -0.40": "ledger point, misclosure -0.40",
"обратная вставка 25 м": "backward equation 25 m",
"репер": "ledger point",
"прямая вставка 40 м": "forward equation 40 m",
"конец": "end",
"опорный для относительной записи": "reference for the relative record",
"относительная запись: тот же пикет": "relative record, the same picket",
"обратная вставка без участка": "backward equation without a section",
"попал в прямую вставку": "falls into the forward equation gap",
"за концом маршрута": "beyond the route end",
"испорченная запись": "damaged record",
"нет такого маршрута": "no such route",
"маршрут не собран: разрыв": "route not assembled, gap",
"простой участок": "plain section",
"записан против хода, меняется местами": "recorded against the route direction, swapped",
"через дугу, смещение 10 м влево": "across the arc, 10 m offset to the left",
"через обратную вставку": "across the backward equation",
"через обе вставки и изломы": "across both equations and the bends",
"нулевая длина": "zero length",
"в обратной вставке, указан участок": "in the backward equation, section given",
# events
"по длине": "by length",
"нет маршрута для привязки": "no route to locate on",
"маршрут «{rid}» не найден": "route «{rid}» is not found",
"пикет {pk} даёт меру": "station {pk} gives the measure {m:.2f} with the route length {L:.2f}",
"участок нулевой длины": "zero-length section",
"ближайший маршрут": "the nearest route «{rid}» is {d:.2f} m away, beyond the radius {r:g}",
# route
"маршрут нулевой длины": "zero-length route",
"мера {m:.3f} вне 0..": "measure {m:.3f} is outside 0..{L:.3f}",
"начало {a:.3f} не меньше конца": "the start {a:.3f} is not less than the end {b:.3f}",
# stations
"пустое значение": "empty value",
"число без «+»": "a number without «+» in the station-plus mode",
"не соответствует формату": "does not match the format {fmt}",
"«{s}»: километр с 1": "«{s}»: kilometre from 1, picket from 1 to 10",
"«{s}»: относительная запись": "«{s}»: relative record without a previous station",
# binder
"поставлено {a}, ошибок {b}": "placed {a}, errors {b}",
"нет слоя: {names}": "missing layer: {names}",
"{name}, ошибки": "{name}, errors",
"восстановлено динамических слоёв": "live layers restored: {n}",
"ошибка: {e}": "error: {e}",
"{name}: слой событий удалён": "{name}: the event layer was removed from the project, the binding is skipped",
"{name}: исходный слой удалён": "{name}: a source layer was removed, recalculation stopped",
"ведомость": "ledger",
# tools
"Демонстрационный пример": "Demo example",
"Проверка маршрутов": "Route check",
"Точечные события": "Point events",
"Участки (линейные события)": "Sections (line events)",
"Динамический слой точечных событий": "Live layer of point events",
"Динамический слой участков": "Live layer of sections",
"Пикетная разбивка": "Picket stakeout",
"Привязка точек к маршрутам": "Locate points on routes",
"Создаёт GeoPackage": (
    "Creates a GeoPackage with four routes: a straight line with elevations, a true arc of R=300 m, "
    "a polyline stored as parts in arbitrary order, and a route with a gap. It also holds an as-built "
    "ledger with broken pickets, a backward and a forward station equation, tables of point and line "
    "events, deliberately faulty records among them, and defect points. Every record carries a "
    "reference answer in the exp_* fields, computed analytically without the plugin.\n\n"
    "With the check switched on, the example runs through the plugin tools at once. The comparison "
    "with the reference goes to the log, and the results are added to the project."),
"Routeliner, пример": "Routeliner, example",
"Маршруты": "Routes",
"Дефекты": "Defects",
"Ведомость": "Ledger",
"Линейные события": "Line events",
"Собранные маршруты": "Assembled routes",
"Точечные события, результат": "Point events, result",
"Точечные события, ошибки": "Point events, errors",
"Участки, результат": "Sections, result",
"Дефекты, привязка": "Defects, located",
"Пикеты": "Pickets",
"да": "yes",
"нет": "no",
"Папка для примера": "Folder for the example",
"Количество случайных точечных событий": "Number of random point events",
"Зерно случайных чисел": "Random seed",
"Сразу прогнать через модуль": "Run through the plugin at once and compare with the reference",
"Проверка пройдена": "Check passed",
"Итог проверки": "Check summary",
"ПРОВЕРКА ПРОЙДЕНА": "CHECK PASSED",
"ПРОВЕРКА НЕ ПРОЙДЕНА": "CHECK FAILED",
"Не записан слой": "Layer {name} is not written: {err}",
"Пример записан": "Example written: {path}",
"Событий: точечных": "Events: point {a}, line {b}, defects {c}",
"Маршруты: не собран только R4": "Routes: only R4 not assembled - {v}",
"Точечные: совпало": "Point events: {a} of {n} match (largest deviation {w:.1f} mm), expected errors recognised {e} of {en}",
"Участки: совпало": "Sections: {a} of {n} match, zero-length error recognised: {v}",
"Дефекты: привязано верно": "Defects: {a} of {n} located correctly",
"Таблица ошибок повторяет": "The error table repeats the fields of the source record and adds rl_route (route), rl_error (reason code) and rl_message (explanation).",
"Параметры те же, что у инструмента": (
    "The parameters are those of tool {src}, but the result is not a one-off. The in-memory layer "
    "is recalculated by itself when the route geometry, the event table or the ledger changes, "
    "including unsaved edits and a CSV or Excel file changed on disk. An error table is created "
    "next to it.\n\n"
    "The binding is stored in the project and restored when the project opens. To stop the "
    "recalculation, remove the event layer from the project.\n\n"
    "The fields of the layer are those of the result of tool {src}."),
"Собирает каждый маршрут": (
    "Assembles every route from all features with the same ID. Multi-lines are split into parts, "
    "the parts are ordered by their joints rather than by storage order, and arcs are segmented. "
    "A route with a gap, a branch or in a geographic coordinate system goes to the error table.\n\n"
    "Result fields: route_id (route ID), length (length along the axis, m), parts (number of parts "
    "after assembly), gaps (number of gaps), gap_max (largest gap, m)."),
"Ставит на маршруты записи таблицы": (
    "Places table records on the routes by station in the chosen notation, with an offset from the "
    "axis. The station is converted to a measure through the route ledger, and without a ledger "
    "along the axis from the start station. The record «+35» takes the picket of the previous record "
    "of the same route.\n\n"
    "The fields of the source record are followed by rl_m (measure along the axis, m), rl_pk "
    "(station in the chosen notation), rl_x and rl_y (point coordinates in the route CRS), "
    "rl_azimuth (axis azimuth at the point, degrees clockwise from north)."),
"Вырезает участки маршрутов": (
    "Cuts route sections between the start and end stations, with a parallel offset. A section "
    "recorded against the route direction is turned over. A section across a route gap, when gaps "
    "are allowed, comes out as a multi-line.\n\n"
    "The fields of the source record are followed by rl_m_from and rl_m_to (start and end measures, "
    "m), rl_length (length along the axis, m), rl_pk_from and rl_pk_to (start and end stations), "
    "rl_swapped (1 when the start and the end were swapped)."),
"Ставит точки целых пикетов": (
    "Places points of whole pickets along every route, with a label and an azimuth for label "
    "rotation. With a ledger, broken pickets and station equations are taken into account. Pickets "
    "skipped by a forward equation are not placed, and pickets repeated by a backward equation are "
    "placed twice with different section numbers.\n\n"
    "Result fields: route_id (route ID), pk (station in the chosen notation), station (chainage, m), "
    "m (measure along the axis, m), section (chainage section number, from zero), azimuth (axis "
    "azimuth, degrees), km (1 for a picket that is a whole kilometre)."),
"Обратная задача": (
    "The inverse task. For every point the nearest route is found, and the measure, the station and "
    "the signed offset from the axis are computed on it. Points beyond the search radius go to the "
    "error table. When the points have a route ID field, they are located on that route only.\n\n"
    "The fields of the point are followed by rl_route (route ID), rl_m (measure along the axis, m), "
    "rl_pk (station in the chosen notation), rl_offset (offset, m, positive to the left of the route "
    "direction), rl_side (side relative to the route direction: left, right or axis)."),
"События": "Events",
"Таблица событий (слой, CSV, Excel)": "Event table (layer, CSV, Excel)",
"События: поле ID маршрута": "Events: route ID field",
"События: поле смещения от оси, м": "Events: offset from the axis field, m",
"Положительное смещение вправо по ходу": "Positive offset to the right of the route direction",
"События: поле номера участка": "Events: section number field (for backward equations)",
"События на маршрутах": "Events on routes",
"Имя слоя": "Layer name",
"Слой событий": "Event layer",
"Итог первого расчёта": "Result of the first calculation",
"Динамические слои работают только": "Live layers work only in the open QGIS project",
"Шаг разбивки, м": "Stakeout step, m",
"Точки": "Points",
"Точки: поле ID маршрута": "Points: route ID field (optional)",
"Радиус поиска, м": "Search radius, m (0 for no limit)",
"Точки с пикетами": "Points with stations",
"Итого: собрано": "Total: assembled {a}, errors {b}",
"События: поле пикета начала": "Events: start station field",
"События: поле пикета": "Events: station field",
"События: поле пикета конца": "Events: end station field",
"Итого: поставлено": "Total: placed {a} of {n}, errors {b}",
"Участки": "Sections",
"Динамический слой «{name}»": "Live layer «{name}»: {status}",
"Итого: пикетов": "Total: pickets {n}",
"Итого: привязано": "Total: located {a}, errors {b}",
"маршрут не собран: {msg}": "route not assembled: {msg}",
"Не найден слой для параметра": "No layer for the parameter «{p}»",
"Слой «{name}» должен быть в проекте": "Layer «{name}» must be in the project, otherwise there is nothing to watch",
"1. Подготовка": "1. Preparation",
"2. События по пикетам": "2. Events by station",
"3. Динамические слои": "3. Live layers",
"4. Пикетаж и привязка": "4. Chainage and locating",
"ПК и плюс": "Picket and plus (ПК 15+35, 15+35,5, ПК -1+50, +35)",
"километр и метры": "Kilometre and metres (км 1+535)",
"железнодорожная запись": "Railway notation (км 12 ПК 3+45)",
"метры числом": "Metres as a number (1535,5)",
"километры дробью": "Kilometres as a decimal (1,535)",
"Routeliner развивается": "Routeliner grows on tasks of real enterprises. If your production lacks a function, write to us",
"Допуск стыковки частей, м": "Part joint tolerance, m",
"Разрешить разрывы": "Allow gaps (a section across a gap comes out as a multi-line)",
"Длина по 3D": "3D length (with Z)",
"Обратное направление маршрутов": "Reverse route direction",
"Ведомость: поле ID маршрута": "Ledger: route ID field",
"Ведомость: поле пикета вперёд": "Ledger: station ahead field (equation)",
"Ведомость: поле пикета": "Ledger: station field",
"Ведомость: поле метража": "Ledger: distance field (measure along the axis)",
"Ведомость: поле системы пикетажа": "Ledger: chainage system field",
"Слой маршрутов (линии)": "Route layer (lines)",
"Поле ID маршрута": "Route ID field",
"Длина пикета, м": "Picket length, m",
"Пикет начала маршрута": "Route start station (without a ledger), m",
"Пикетажная ведомость": "Chainage ledger (optional)",
"Система пикетажа": "Chainage system (value of the system field)",
"Ошибки": "Errors",
"Не задан слой маршрутов": "The route layer is not set",
"Страница плагина": "Plugin page",
"Запись пикета": "Station notation",
"Маршрутов собрано": "Routes assembled {a}, not assembled {b}",
"Для ведомости нужны поля": "The ledger needs the route ID and station fields",
"Маршрут {rid}: {msg}": "Route {rid}: {msg}",
"Ведомость: систем пикетажа": "Ledger: chainage systems {a}, errors {b}",
"Разработано при поддержке": "Developed with the support of Inform++ LLC",
"Ведомость, маршрут {rid}": "Ledger, route {rid}: {msg}",
"Routeliner, события на маршрутах": "Routeliner, route events and chainage",
}
out = {}
missing = []
for k in keys:
    if k in SKIP or k.startswith(SKIP_PREFIX):
        continue
    if k in EN:
        out[k] = EN[k]; continue
    cands = [p for p in EN if k.startswith(p)]
    if not cands:
        missing.append(k); continue
    p = max(cands, key=len)
    out[k] = EN[p]
if missing:
    print("MISSING:", missing)
# проверка: плейсхолдеры совпадают
import string
fmt = string.Formatter()
for k, v in out.items():
    a = sorted(f for _, f, _, _ in fmt.parse(k) if f)
    b = sorted(f for _, f, _, _ in fmt.parse(v) if f)
    if a != b:
        print("PLACEHOLDERS", repr(k[:50]), a, b)
with open("routeliner/translations.py", "w", encoding="utf-8") as fh:
    fh.write('# -*- coding: utf-8 -*-\n"""Переводы RU -> EN. Ключ - русская строка ровно как в коде.\n\n'
             'Файл собран из исходников (tools/make_translations.py), проверка полноты\n'
             'в tests/core/test_i18n.py."""\n\nTRANSLATIONS = {\n')
    for k, v in out.items():
        fh.write(f"    {k!r}:\n        {v!r},\n")
    fh.write("}\n")
print(len(out), "entries")
