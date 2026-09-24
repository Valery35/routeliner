# -*- coding: utf-8 -*-
"""Переводы RU -> EN. Ключ - русская строка ровно как в коде.

Файл собран из исходников (tools/make_translations.py), проверка полноты
в tests/core/test_i18n.py."""

TRANSLATIONS = {
    'О модуле':
        'About',
    'Руководство не найдено.':
        'The manual is not found.',
    'События на маршрутах и пикетаж для QGIS':
        'Route events and chainage for QGIS',
    'длины в географической системе координат считаются в градусах. Перепроецируйте маршруты в метрическую СК':
        'lengths in a geographic coordinate system are measured in degrees. Reproject the routes to a metric CRS',
    'нет геометрии':
        'no geometry',
    'маршрут распадается на {n} куска, ближайший разрыв {d:.3f} больше допуска {t:g}':
        'the route falls apart into {n} pieces, the nearest gap {d:.3f} exceeds the tolerance {t:g}',
    'в точке ({x:.2f}, {y:.2f}) сходятся {n} конца частей':
        '{n} part ends meet at the point ({x:.2f}, {y:.2f})',
    'нужно не меньше двух реперов':
        'at least two ledger points are needed',
    'ведомость пуста':
        'the ledger is empty',
    'система «{name}»: {why}':
        'system «{name}»: {why}',
    'не удалось разместить уравнения {eqs}':
        'the station equations {eqs} could not be placed',
    'мера {m:.3f} вне {a:.3f}..{b:.3f}':
        'measure {m:.3f} is outside {a:.3f}..{b:.3f}',
    'два репера с одной мерой m={m:.3f}':
        'two ledger points with the same measure m={m:.3f}',
    'пикетаж не растёт на участке m {a:.2f}..{b:.2f}, от {s0:.2f} до {s1:.2f}':
        'chainage does not increase on the section m {a:.2f}..{b:.2f}, from {s0:.2f} to {s1:.2f}',
    'нет участка {n}':
        'no section {n}',
    'уравнение {b}={a} не помещается между реперами m {m0:.2f} и {m1:.2f}':
        'the equation {b}={a} does not fit between the ledger points m {m0:.2f} and {m1:.2f}',
    'у репера ПК {st:.2f} не задана мера':
        'the ledger point at station {st:.2f} has no measure',
    'репер ПК {st:.2f} (m={m:.2f}) лежит в обратной вставке {b}={a}, и его сторона неизвестна. Задайте мерой положение уравнения':
        'the ledger point at station {st:.2f} (m={m:.2f}) lies in the backward equation {b}={a}, and its side is unknown. Give the equation position as a measure',
    'Прямая с отметками':
        'Straight line with elevations',
    'Кривая R=300':
        'Curve R=300',
    'Части в произвольном порядке':
        'Parts in arbitrary order',
    'С разрывом':
        'With a gap',
    'начало':
        'start',
    'репер, невязка -0.40':
        'ledger point, misclosure -0.40',
    'обратная вставка 25 м':
        'backward equation 25 m',
    'репер':
        'ledger point',
    'прямая вставка 40 м':
        'forward equation 40 m',
    'конец':
        'end',
    'опорный для относительной записи':
        'reference for the relative record',
    'относительная запись: тот же пикет':
        'relative record, the same picket',
    'обратная вставка без участка':
        'backward equation without a section',
    'попал в прямую вставку':
        'falls into the forward equation gap',
    'за концом маршрута':
        'beyond the route end',
    'испорченная запись':
        'damaged record',
    'нет такого маршрута':
        'no such route',
    'маршрут не собран: разрыв':
        'route not assembled, gap',
    'простой участок':
        'plain section',
    'записан против хода, меняется местами':
        'recorded against the route direction, swapped',
    'через дугу, смещение 10 м влево':
        'across the arc, 10 m offset to the left',
    'через обратную вставку':
        'across the backward equation',
    'через обе вставки и изломы':
        'across both equations and the bends',
    'нулевая длина':
        'zero length',
    'в обратной вставке, указан участок':
        'in the backward equation, section given',
    'по длине':
        'by length',
    'нет маршрута для привязки':
        'no route to locate on',
    'маршрут «{rid}» не найден':
        'route «{rid}» is not found',
    'пикет {pk} даёт меру {m:.2f} при длине маршрута {L:.2f}':
        'station {pk} gives the measure {m:.2f} with the route length {L:.2f}',
    'участок нулевой длины':
        'zero-length section',
    'ближайший маршрут «{rid}» в {d:.2f} м, дальше радиуса {r:g}':
        'the nearest route «{rid}» is {d:.2f} m away, beyond the radius {r:g}',
    'влево':
        'left',
    'вправо':
        'right',
    'Условный горизонт {z:.2f}':
        'Datum {z:.2f}',
    'М 1:{v:g} по вертикали':
        'Vertical scale 1:{v:g}',
    'М 1:{h:g} по горизонтали':
        'Horizontal scale 1:{h:g}',
    'ВУ{n} {a:.1f}° {side}':
        'PI{n} {a:.1f}° {side}',
    'маршрут нулевой длины':
        'zero-length route',
    'мера {m:.3f} вне 0..{L:.3f}':
        'measure {m:.3f} is outside 0..{L:.3f}',
    'начало {a:.3f} не меньше конца {b:.3f}':
        'the start {a:.3f} is not less than the end {b:.3f}',
    'пустое значение':
        'empty value',
    'число без «+» в режиме записи с плюсом':
        'a number without «+» in the station-plus mode',
    'не соответствует формату {fmt}':
        'does not match the format {fmt}',
    '«{s}»: километр с 1, пикет от 1 до 10':
        '«{s}»: kilometre from 1, picket from 1 to 10',
    '«{s}»: относительная запись без предыдущего пикета':
        '«{s}»: relative record without a previous station',
    'поставлено {a}, ошибок {b}':
        'placed {a}, errors {b}',
    'нет слоя: {names}':
        'missing layer: {names}',
    '{name}, ошибки':
        '{name}, errors',
    'восстановлено динамических слоёв: {n}':
        'live layers restored: {n}',
    'ошибка: {e}':
        'error: {e}',
    '{name}: слой событий удалён из проекта, привязка пропущена':
        '{name}: the event layer was removed from the project, the binding is skipped',
    '{name}: исходный слой удалён, пересчёт остановлен':
        '{name}: a source layer was removed, recalculation stopped',
    'ведомость':
        'ledger',
    'Демонстрационный пример':
        'Demo example',
    'Проверка маршрутов':
        'Route check',
    'Точечные события':
        'Point events',
    'Участки (линейные события)':
        'Sections (line events)',
    'Динамический слой точечных событий':
        'Live layer of point events',
    'Динамический слой участков':
        'Live layer of sections',
    'Пикетная разбивка':
        'Picket stakeout',
    'Привязка точек к маршрутам':
        'Locate points on routes',
    'Таблица профиля':
        'Profile table',
    'Чертёж профиля':
        'Profile drawing',
    'Руководство (PDF)':
        'Manual (PDF)',
    'Создаёт GeoPackage с четырьмя маршрутами: прямая с отметками, настоящая дуга R=300 м, ломаная из частей в произвольном порядке, маршрут с разрывом. В нём же исполнительная ведомость с рублеными пикетами, обратной и прямой вставками, таблицы точечных и линейных событий, в том числе заведомо ошибочных, и точки дефектов. У каждой записи есть эталонный ответ в полях exp_*, посчитанный аналитически, без участия модуля.\n\nС включённой проверкой пример сразу прогоняется через инструменты модуля. Итог сравнения с эталоном выводится в журнал, результаты добавляются в проект.':
        'Creates a GeoPackage with four routes: a straight line with elevations, a true arc of R=300 m, a polyline stored as parts in arbitrary order, and a route with a gap. It also holds an as-built ledger with broken pickets, a backward and a forward station equation, tables of point and line events, deliberately faulty records among them, and defect points. Every record carries a reference answer in the exp_* fields, computed analytically without the plugin.\n\nWith the check switched on, the example runs through the plugin tools at once. The comparison with the reference goes to the log, and the results are added to the project.',
    'Routeliner, пример':
        'Routeliner, example',
    'Маршруты':
        'Routes',
    'Дефекты':
        'Defects',
    'Ведомость':
        'Ledger',
    'Линейные события':
        'Line events',
    'Рельеф':
        'Terrain',
    'Собранные маршруты':
        'Assembled routes',
    'Точечные события, результат':
        'Point events, result',
    'Точечные события, ошибки':
        'Point events, errors',
    'Участки, результат':
        'Sections, result',
    'Дефекты, привязка':
        'Defects, located',
    'Пикеты':
        'Pickets',
    'Профиль, линии':
        'Profile, lines',
    'Профиль, подписи':
        'Profile, labels',
    'да':
        'yes',
    'нет':
        'no',
    'Папка для примера':
        'Folder for the example',
    'Количество случайных точечных событий':
        'Number of random point events',
    'Зерно случайных чисел':
        'Random seed',
    'Сразу прогнать через модуль и сравнить с эталоном':
        'Run through the plugin at once and compare with the reference',
    'Проверка пройдена':
        'Check passed',
    'Итог проверки':
        'Check summary',
    'ПРОВЕРКА ПРОЙДЕНА':
        'CHECK PASSED',
    'ПРОВЕРКА НЕ ПРОЙДЕНА':
        'CHECK FAILED',
    'Не записан слой {name}: {err}':
        'Layer {name} is not written: {err}',
    'Пример записан: {path}':
        'Example written: {path}',
    'Событий: точечных {a}, линейных {b}, дефектов {c}':
        'Events: point {a}, line {b}, defects {c}',
    'Маршруты: не собран только R4 - {v}':
        'Routes: only R4 not assembled - {v}',
    'Точечные: совпало {a} из {n} (наибольшее расхождение {w:.1f} мм), ожидаемых ошибок распознано {e} из {en}':
        'Point events: {a} of {n} match (largest deviation {w:.1f} mm), expected errors recognised {e} of {en}',
    'Участки: совпало {a} из {n}, ошибка нулевой длины распознана: {v}':
        'Sections: {a} of {n} match, zero-length error recognised: {v}',
    'Дефекты: привязано верно {a} из {n}':
        'Defects: {a} of {n} located correctly',
    'Профиль: отметки рельефа совпали {a} из {n} (наибольшее расхождение {w:.1f} мм), отметки оси R1 {b} из {m}, уравнений R3 {e} из 2, чертёж построен: {v}':
        'Profile: terrain levels match {a} of {n} (largest deviation {w:.1f} mm), R1 axis levels {b} of {m}, R3 equations {e} of 2, drawing built: {v}',
    'Собирает точки продольного профиля по каждому маршруту и снимает в них значения растров. Точки ставятся в начале и конце маршрута, на пикетажных уравнениях, на целых пикетах, на вершинах оси и с постоянным шагом. Точки из слоя событий (переходы, колодцы, скважины) ставятся по проекции на ось, если лежат в коридоре от оси.\n\nЗначения растров интерполируются билинейно по центрам ячеек. Растр может быть в любой системе координат, точки пересчитываются.\n\nПоля результата: route_id (ID маршрута), n (номер точки), kind (start, end, equation, event, picket, vertex, step), m (мера по оси, м), station (пикетаж, м), station_ahead (пикетаж вперёд, только у уравнения), pk (пикет в выбранной записи), section (номер участка пикетажа), x и y (координаты на оси), z_axis (отметка оси по Z маршрута, пусто, если у маршрута нет Z или все Z нулевые), turn (угол поворота трассы в вершине, градусы, плюс влево), label (подпись события) и по одному полю z_имя на каждый растр.':
        'Collects the points of a longitudinal profile along every route and samples raster values at them. Points are placed at the route start and end, at station equations, at whole pickets, at axis vertices and with a constant step. Points from the event layer (crossings, manholes, boreholes) are placed by projection onto the axis if they lie within the corridor from the axis.\n\nRaster values are interpolated bilinearly between cell centres. A raster may be in any coordinate system, the points are transformed.\n\nResult fields: route_id (route ID), n (point number), kind (start, end, equation, event, picket, vertex, step), m (measure along the axis, m), station (chainage, m), station_ahead (chainage ahead, equations only), pk (station in the chosen notation), section (chainage section number), x and y (coordinates on the axis), z_axis (axis elevation from the route Z, empty if the route has no Z or all Z are zero), turn (turn angle of the alignment at a vertex, degrees, positive to the left), label (event label) and one z_name field for each raster.',
    'Заголовок':
        'Title',
    'Тип':
        'Type',
    'Источник':
        'Source',
    'Знаков':
        'Decimals',
    'Высота, мм':
        'Height, mm',
    'Линия (1/0)':
        'Line (1/0)',
    'Строит чертёж продольного профиля одного маршрута по таблице 5.01: линии поверхностей над сеткой, сетку профиля со строками, шкалу отметок и развёрнутый план. Чертёж ставится в той же системе координат, что и таблица, в миллиметрах бумаги: одна единица карты равна миллиметру. В компоновке QGIS профиль печатается в натуральную величину при масштабе карты 1:1000.\n\nСтроки сетки задаются таблицей. Тип строки: value (число по выражению), text (подписи участков из поля слоя участков), grade (уклон и длина по выражению), distance (расстояния между точками), station (пикеты), plan (развёрнутый план). В выражениях можно писать поля таблицы профиля и подстановки {ground}, {design}, {pipe}, {d}, {base}, которые заменяются полями и числами из параметров. Строка, у которой нет данных, в сетку не выводится.\n\nПодписи точек прореживаются: если точки на бумаге ближе заданного промежутка, подпись остаётся у точки с большим приоритетом (начало и конец, уравнение, событие, пикет, вершина, шаг).\n\nПоля слоя линий: kind (вид линии), row (строка), color, width (толщина, мм). Поля слоя подписей: text, kind, rot (поворот, градусы), size (высота, мм), halign, valign.':
        'Builds the drawing of the longitudinal profile of one route from the 5.01 table: surface lines above the grid, the profile grid with its rows, the elevation scale and the straightened plan. The drawing is placed in the same coordinate system as the table, in paper millimetres, so one map unit equals one millimetre. In a QGIS print layout the profile prints at full size with the map scale 1:1000.\n\nThe grid rows are set by a table. Row type: value (number from an expression), text (section labels from a field of the section layer), grade (grade and length from an expression), distance (distances between points), station (pickets), plan (straightened plan). Expressions may use the fields of the profile table and the placeholders {ground}, {design}, {pipe}, {d}, {base}, which are replaced by fields and numbers from the parameters. A row without data is not put into the grid.\n\nPoint labels are thinned: if points are closer on paper than the given gap, the label stays at the point with the higher priority (start and end, equation, event, picket, vertex, step).\n\nFields of the line layer: kind (line kind), row (row), color, width (width, mm). Fields of the label layer: text, kind, rot (rotation, degrees), size (height, mm), halign, valign.',
    'только с поворотом или изломом уклона':
        'only with a turn or a grade break',
    'все вершины':
        'all vertices',
    'без вершин':
        'no vertices',
    'Отметка земли проектная, м':
        'Design ground level, m',
    'Отметка земли фактическая, м':
        'Existing ground level, m',
    'Отметка верха трубы, м':
        'Pipe top level, m',
    'Отметка дна траншеи, м':
        'Trench bottom level, m',
    'Расстояние земля - труба, м':
        'Ground to pipe, m',
    'Глубина траншеи, м':
        'Trench depth, m',
    'Обозначение трубы и тип изоляции':
        'Pipe type and coating',
    'Основание':
        'Bedding',
    'Уклон, ‰ / длина, м':
        'Grade, ‰ / length, m',
    'Расстояние, м':
        'Distance, m',
    'Пикет':
        'Station',
    'Развёрнутый план':
        'Straightened plan',
    'Поле отметки земли {ground}':
        'Ground level field {ground}',
    'Поле проектной отметки {design}':
        'Design level field {design}',
    'Поле отметки трубы или оси {pipe} (пусто - z_axis)':
        'Pipe or axis level field {pipe} (empty - z_axis)',
    'Участки: поле ID маршрута':
        'Sections: route ID field',
    'Участки: поле меры начала':
        'Sections: start measure field',
    'Участки: поле меры конца':
        'Sections: end measure field',
    'Маршруты через запятую (пусто - все)':
        'Routes separated by commas (empty - all)',
    'Растры (рельеф, проектная поверхность, пласт)':
        'Rasters (terrain, design surface, seam)',
    'Номер канала растров':
        'Raster band number',
    'Точки на целых пикетах через, м (0 - нет)':
        'Points at whole pickets every, m (0 - none)',
    'Точки с постоянным шагом, м (0 - нет)':
        'Points with a constant step, m (0 - none)',
    'Вершины оси':
        'Axis vertices',
    'События на профиль: точки (необязательно)':
        'Events for the profile: points (optional)',
    'События: поле подписи':
        'Events: label field',
    'События: коридор от оси, м':
        'Events: corridor from the axis, m',
    'Таблица профиля (результат 5.01)':
        'Profile table (result of 5.01)',
    'Маршрут (пусто - первый в таблице)':
        'Route (empty - the first in the table)',
    'Наружный диаметр трубы {d}, м':
        'Pipe outer diameter {d}, m',
    'Толщина основания {base}, м':
        'Bedding thickness {base}, m',
    'Строки сетки профиля':
        'Profile grid rows',
    'Участки для текстовых строк (необязательно)':
        'Sections for text rows (optional)',
    'Точки для развёрнутого плана (результат 4.02, необязательно)':
        'Points for the straightened plan (result of 4.02, optional)',
    'План: поле подписи':
        'Plan: label field',
    'Масштаб по горизонтали 1:':
        'Horizontal scale 1:',
    'Масштаб по вертикали 1:':
        'Vertical scale 1:',
    'Условный горизонт, м (пусто - автоматически)':
        'Datum, m (empty - automatic)',
    'Допуск выделения уклонов, м':
        'Grade detection tolerance, m',
    'Наименьший промежуток между подписями, мм':
        'Smallest gap between labels, mm',
    'Левый нижний угол профиля над сеткой (пусто - под маршрутом)':
        'Lower left corner of the profile above the grid (empty - below the routes)',
    'Не задана таблица профиля':
        'The profile table is not set',
    'В слое плана нужны поля rl_m и rl_offset (результат 4.02)':
        'The plan layer needs the fields rl_m and rl_offset (result of 4.02)',
    'Итого: точек профиля {n}, растров {r}':
        'Total: profile points {n}, rasters {r}',
    'Профиль маршрута «{rid}»: строк {r}, ширина {w:.0f} мм, условный горизонт {h:.2f}':
        'Profile of route «{rid}»: rows {r}, width {w:.0f} mm, datum {h:.2f}',
    'В таблице нет точек маршрута «{rid}»':
        'The table has no points of route «{rid}»',
    'В слое участков нет полей меры «{a}» и «{b}»':
        'The section layer has no measure fields «{a}» and «{b}»',
    'В таблице нет поля «{f}», нужна таблица инструмента 5.01':
        'The table has no field «{f}», the table of tool 5.01 is needed',
    'не задано: {names}':
        'not set: {names}',
    'Строка «{t}»: неизвестный тип «{k}»':
        'Row «{t}»: unknown type «{k}»',
    'Строка «{t}»: знаков и высота должны быть числами':
        'Row «{t}»: decimals and height must be numbers',
    'Строка «{t}» пропущена: {why}':
        'Row «{t}» skipped: {why}',
    'Строка «{t}» пропущена: нет участков с полем «{f}»':
        'Row «{t}» skipped: no sections with the field «{f}»',
    'Таблица ошибок повторяет поля исходной записи и добавляет rl_route (маршрут), rl_error (код причины) и rl_message (пояснение).':
        'The error table repeats the fields of the source record and adds rl_route (route), rl_error (reason code) and rl_message (explanation).',
    'Ставит на маршруты записи таблицы по пикету в выбранной записи, со смещением от оси. Пикет переводится в меру через ведомость маршрута, а без ведомости по длине оси от пикета начала. Запись «+35» берёт пикет предыдущей записи того же маршрута.\n\nК полям исходной записи добавляются rl_m (мера по оси, м), rl_pk (пикет в выбранной записи), rl_x и rl_y (координаты точки в СК маршрутов), rl_azimuth (азимут оси в точке, градусы от севера по часовой стрелке).':
        'Places table records on the routes by station in the chosen notation, with an offset from the axis. The station is converted to a measure through the route ledger, and without a ledger along the axis from the start station. The record «+35» takes the picket of the previous record of the same route.\n\nThe fields of the source record are followed by rl_m (measure along the axis, m), rl_pk (station in the chosen notation), rl_x and rl_y (point coordinates in the route CRS), rl_azimuth (axis azimuth at the point, degrees clockwise from north).',
    'Вырезает участки маршрутов между пикетами начала и конца, с параллельным смещением. Участок, записанный против хода маршрута, переворачивается. Участок через разрыв маршрута при разрешённых разрывах выдаётся мультилинией.\n\nК полям исходной записи добавляются rl_m_from и rl_m_to (меры начала и конца, м), rl_length (длина по оси, м), rl_pk_from и rl_pk_to (пикеты начала и конца), rl_swapped (1, если начало и конец поменяны местами).':
        'Cuts route sections between the start and end stations, with a parallel offset. A section recorded against the route direction is turned over. A section across a route gap, when gaps are allowed, comes out as a multi-line.\n\nThe fields of the source record are followed by rl_m_from and rl_m_to (start and end measures, m), rl_length (length along the axis, m), rl_pk_from and rl_pk_to (start and end stations), rl_swapped (1 when the start and the end were swapped).',
    'Параметры те же, что у инструмента {src}, а результат не разовый. Слой в памяти пересчитывается сам при правке геометрии маршрутов, таблицы событий или ведомости, в том числе при несохранённой правке и при изменении файла CSV или Excel на диске. Рядом создаётся таблица ошибок.\n\nПривязка хранится в проекте и восстанавливается при его открытии. Чтобы отключить пересчёт, удалите слой событий из проекта.\n\nПоля слоя совпадают с полями результата инструмента {src}.':
        'The parameters are those of tool {src}, but the result is not a one-off. The in-memory layer is recalculated by itself when the route geometry, the event table or the ledger changes, including unsaved edits and a CSV or Excel file changed on disk. An error table is created next to it.\n\nThe binding is stored in the project and restored when the project opens. To stop the recalculation, remove the event layer from the project.\n\nThe fields of the layer are those of the result of tool {src}.',
    'Собирает каждый маршрут из всех объектов с одним ID. Мультилинии раскладываются на части, части упорядочиваются по стыкам, а не по порядку хранения, дуги сегментируются. Маршрут с разрывом, развилкой или в географической системе координат попадает в таблицу ошибок.\n\nПоля результата: route_id (ID маршрута), length (длина по оси, м), parts (количество частей после сборки), gaps (количество разрывов), gap_max (наибольший разрыв, м).':
        'Assembles every route from all features with the same ID. Multi-lines are split into parts, the parts are ordered by their joints rather than by storage order, and arcs are segmented. A route with a gap, a branch or in a geographic coordinate system goes to the error table.\n\nResult fields: route_id (route ID), length (length along the axis, m), parts (number of parts after assembly), gaps (number of gaps), gap_max (largest gap, m).',
    'Ставит точки целых пикетов по каждому маршруту с подписью и азимутом для поворота подписи. При ведомости учитываются рубленые пикеты и пикетажные уравнения. В прямой вставке пропущенные пикеты не ставятся, в обратной повторяющиеся ставятся дважды с разными номерами участков.\n\nПоля результата: route_id (ID маршрута), pk (пикет в выбранной записи), station (пикетаж, м), m (мера по оси, м), section (номер участка пикетажа, с нуля), azimuth (азимут оси, градусы), km (1 для пикета, кратного километру).':
        'Places points of whole pickets along every route, with a label and an azimuth for label rotation. With a ledger, broken pickets and station equations are taken into account. Pickets skipped by a forward equation are not placed, and pickets repeated by a backward equation are placed twice with different section numbers.\n\nResult fields: route_id (route ID), pk (station in the chosen notation), station (chainage, m), m (measure along the axis, m), section (chainage section number, from zero), azimuth (axis azimuth, degrees), km (1 for a picket that is a whole kilometre).',
    'Обратная задача. Для каждой точки находится ближайший маршрут, и по нему считаются мера, пикет и смещение от оси со знаком. Точки дальше радиуса поиска уходят в таблицу ошибок. Если у точек есть поле ID маршрута, привязка идёт только к этому маршруту.\n\nК полям точки добавляются rl_route (ID маршрута), rl_m (мера по оси, м), rl_pk (пикет в выбранной записи), rl_offset (смещение, м, плюс влево по ходу), rl_side (сторона по ходу маршрута: left, right или axis).':
        'The inverse task. For every point the nearest route is found, and the measure, the station and the signed offset from the axis are computed on it. Points beyond the search radius go to the error table. When the points have a route ID field, they are located on that route only.\n\nThe fields of the point are followed by rl_route (route ID), rl_m (measure along the axis, m), rl_pk (station in the chosen notation), rl_offset (offset, m, positive to the left of the route direction), rl_side (side relative to the route direction: left, right or axis).',
    'События':
        'Events',
    'Таблица событий (слой, CSV, Excel)':
        'Event table (layer, CSV, Excel)',
    'События: поле ID маршрута':
        'Events: route ID field',
    'События: поле смещения от оси, м':
        'Events: offset from the axis field, m',
    'Положительное смещение вправо по ходу':
        'Positive offset to the right of the route direction',
    'События: поле номера участка (для обратных вставок)':
        'Events: section number field (for backward equations)',
    'События на маршрутах':
        'Events on routes',
    'Имя слоя':
        'Layer name',
    'Слой событий':
        'Event layer',
    'Итог первого расчёта':
        'Result of the first calculation',
    'Динамические слои работают только в открытом проекте QGIS':
        'Live layers work only in the open QGIS project',
    'Шаг разбивки, м':
        'Stakeout step, m',
    'Точки':
        'Points',
    'Точки: поле ID маршрута (необязательно)':
        'Points: route ID field (optional)',
    'Радиус поиска, м (0 без ограничения)':
        'Search radius, m (0 for no limit)',
    'Точки с пикетами':
        'Points with stations',
    'Итого: собрано {a}, ошибок {b}':
        'Total: assembled {a}, errors {b}',
    'События: поле пикета начала':
        'Events: start station field',
    'События: поле пикета':
        'Events: station field',
    'События: поле пикета конца':
        'Events: end station field',
    'Итого: поставлено {a} из {n}, ошибок {b}':
        'Total: placed {a} of {n}, errors {b}',
    'Участки':
        'Sections',
    'Динамический слой «{name}»: {status}':
        'Live layer «{name}»: {status}',
    'Итого: пикетов {n}':
        'Total: pickets {n}',
    'Итого: привязано {a}, ошибок {b}':
        'Total: located {a}, errors {b}',
    'маршрут не собран: {msg}':
        'route not assembled: {msg}',
    'Не найден слой для параметра «{p}»':
        'No layer for the parameter «{p}»',
    'Слой «{name}» должен быть в проекте, иначе нечего отслеживать':
        'Layer «{name}» must be in the project, otherwise there is nothing to watch',
    'Мера, м':
        'Measure, m',
    'Азимут, °':
        'Azimuth, °',
    'Мера начала, м':
        'Start measure, m',
    'Мера конца, м':
        'End measure, m',
    'Длина участка, м':
        'Section length, m',
    'Пикет начала':
        'Start station',
    'Пикет конца':
        'End station',
    'Начало и конец поменяны':
        'Start and end swapped',
    'Маршрут':
        'Route',
    'Смещение от оси, м':
        'Offset from the axis, m',
    'Сторона':
        'Side',
    'Код ошибки':
        'Error code',
    'Пояснение ошибки':
        'Error explanation',
    'Эталон, мера, м':
        'Reference, measure, m',
    'Эталон, X':
        'Reference, X',
    'Эталон, Y':
        'Reference, Y',
    'Эталон, код ошибки':
        'Reference, error code',
    'Эталон, мера начала, м':
        'Reference, start measure, m',
    'Эталон, мера конца, м':
        'Reference, end measure, m',
    'Эталон, маршрут':
        'Reference, route',
    'Эталон, пикетаж, м':
        'Reference, chainage, m',
    'Эталон, смещение, м':
        'Reference, offset, m',
    'ID маршрута':
        'Route ID',
    'Длина по оси, м':
        'Length along the axis, m',
    'Частей':
        'Parts',
    'Разрывов':
        'Gaps',
    'Наибольший разрыв, м':
        'Largest gap, m',
    'Пикетаж':
        'Chainage',
    'Участок пикетажа':
        'Chainage section',
    'Целый километр':
        'Whole kilometre',
    'Номер точки':
        'Point number',
    'Вид':
        'Kind',
    'Пикетаж вперёд':
        'Chainage ahead',
    'Отметка оси, м':
        'Axis level, m',
    'Угол поворота, °':
        'Turn angle, °',
    'Подпись':
        'Label',
    'Строка сетки':
        'Grid row',
    'Цвет':
        'Colour',
    'Толщина линии, мм':
        'Line width, mm',
    'Текст':
        'Text',
    'Поворот, °':
        'Rotation, °',
    'Высота текста, мм':
        'Text height, mm',
    'Выравнивание по горизонтали':
        'Horizontal alignment',
    'Выравнивание по вертикали':
        'Vertical alignment',
    'Название':
        'Name',
    'Система пикетажа':
        'Chainage system',
    'Примечание':
        'Note',
    'Номер события':
        'Event number',
    '1. Подготовка':
        '1. Preparation',
    '2. События по пикетам':
        '2. Events by station',
    '3. Динамические слои':
        '3. Live layers',
    '4. Пикетаж и привязка':
        '4. Chainage and locating',
    '5. Профили':
        '5. Profiles',
    'километр и метры (км 1+535)':
        'Kilometre and metres (км 1+535)',
    'железнодорожная запись (км 12 ПК 3+45)':
        'Railway notation (км 12 ПК 3+45)',
    'метры числом (1535,5)':
        'Metres as a number (1535,5)',
    'километры дробью (1,535)':
        'Kilometres as a decimal (1,535)',
    'Routeliner развивается на задачах реальных предприятий. Если вашему производству не хватает функции, напишите нам':
        'Routeliner grows on tasks of real enterprises. If your production lacks a function, write to us',
    'Допуск стыковки частей, м':
        'Part joint tolerance, m',
    'Разрешить разрывы (участок через разрыв выдаётся мультилинией)':
        'Allow gaps (a section across a gap comes out as a multi-line)',
    'Длина по 3D (с учётом Z)':
        '3D length (with Z)',
    'Обратное направление маршрутов':
        'Reverse route direction',
    'Ведомость: поле ID маршрута':
        'Ledger: route ID field',
    'Ведомость: поле пикета':
        'Ledger: station field',
    'Ведомость: поле метража (мера по оси)':
        'Ledger: distance field (measure along the axis)',
    'Ведомость: поле пикета вперёд (уравнение)':
        'Ledger: station ahead field (equation)',
    'Ведомость: поле системы пикетажа':
        'Ledger: chainage system field',
    'Слой маршрутов (линии)':
        'Route layer (lines)',
    'Поле ID маршрута':
        'Route ID field',
    'Длина пикета, м':
        'Picket length, m',
    'Пикет начала маршрута (без ведомости), м':
        'Route start station (without a ledger), m',
    'Пикетажная ведомость (необязательно)':
        'Chainage ledger (optional)',
    'Система пикетажа (значение поля системы)':
        'Chainage system (value of the system field)',
    'Ошибки':
        'Errors',
    'Не задан слой маршрутов':
        'The route layer is not set',
    'Страница плагина':
        'Plugin page',
    'Запись пикета':
        'Station notation',
    'Маршрутов собрано {a}, не собрано {b}':
        'Routes assembled {a}, not assembled {b}',
    'Для ведомости нужны поля ID маршрута и пикета':
        'The ledger needs the route ID and station fields',
    'Маршрут {rid}: {msg}':
        'Route {rid}: {msg}',
    'Ведомость: систем пикетажа {a}, ошибок {b}':
        'Ledger: chainage systems {a}, errors {b}',
    'Разработано при поддержке ООО «Информ++»':
        'Developed with the support of Inform++ LLC',
    'Ведомость, маршрут {rid}: {msg}':
        'Ledger, route {rid}: {msg}',
    'Растр {name}':
        'Raster {name}',
    'Routeliner, события на маршрутах и пикетаж':
        'Routeliner, route events and chainage',
}
