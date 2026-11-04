# Тексты объявлений Routeliner 0.5.2

Тексты для площадок из doc/PUBLISH.md. Каждый проверен measure.py в полосе letter, нарушений нет. После публикации ссылка на запись заносится в журнал doc/PUBLISH.md.

## GitHub, заметки к выпуску 0.5.2

- В окне «О модуле» есть ссылка «Поддержать разработку».
- Та же ссылка стоит внизу справки каждого инструмента и ведёт на профиль автора на GitHub, где описано, как поддержать работу.
- Страница модуля на GitHub открывается по-английски, русская версия доступна ссылкой.
- Версия 0.5.2 стоит в каталоге модулей QGIS.

- The About window has a Support development link.
- The same link sits at the bottom of every tool help.
- The plugin page on GitHub opens in English, and the Russian version is linked at the top of the page.
- Version 0.5.2 is in the QGIS plugin catalogue.

## ВК, vk.ru/qgismodules

```
Routeliner - модуль QGIS для событий на маршруте

Routeliner ставит на ось дороги, трубопровода, линии электропередачи или горной выработки записи, у которых вместо координат указан пикет. Модуль читает пять принятых в СНГ записей пикета и учитывает ведомость с рублеными пикетами, прямыми и обратными вставками.

Что модуль умеет:
- ставит точечные события и участки со смещением от оси
- ведёт динамические слои, которые пересчитываются после правки данных
- делает пикетную разбивку и находит пикет для любой точки
- строит продольный профиль с отметками рельефа, уклонами и развёрнутым планом
- читает и пишет пикетаж в M-значениях, так что слои понимают PostGIS и ArcGIS

Запись, которую поставить нельзя, уходит в таблицу ошибок с причиной. Демонстрационный пример с эталонными ответами проверяет модуль на вашем компьютере.

Модуль работает в QGIS 3.40 и QGIS 4, интерфейс и руководство написаны на русском и английском, а ставится он из каталога модулей QGIS по названию Routeliner. Модуль бесплатный, код открыт.

https://plugins.qgis.org/plugins/routeliner/
```

## Facebook

```
Выложили Routeliner, модуль QGIS для событий на маршруте.

Записи вдоль дорог, трубопроводов и линий электропередачи обычно несут пикет, а не координаты. Routeliner ставит такие записи на ось маршрута и учитывает ведомость с пикетажными уравнениями, как это принято в СНГ.

По маршруту строится продольный профиль с отметками рельефа и уклонами. Пикетаж можно взять из M-значений геометрии и записать в M результатов, а такие слои без пересчёта читают PostGIS, ArcGIS и инструменты QGIS для M.

Модуль бесплатный, ставится из каталога QGIS. Код открыт.

https://plugins.qgis.org/plugins/routeliner/
```

## OSGeo Discourse, раздел General

Заголовок и текст.

```
Routeliner: a QGIS plugin for route events with CIS chainage ledgers and station equations

Records along roads, pipelines and power lines often carry a station instead of coordinates. Routeliner places such records on the route axis. It reads five station notations used in the CIS and handles a ledger with broken pickets and forward and backward station equations.

The plugin places point events and sections with an offset. Live layers follow edits of the source data. It stakes out pickets and locates any point on a route. It also builds a longitudinal profile with raster levels, grades and a straightened plan for a print layout. Chainage can be read from route M values and written into the M of results. PostGIS and ArcGIS tools read such layers.

A record that cannot be placed goes to an error table with a reason code. A demo project with analytically computed answers checks the whole chain. A run of 3000 events gave a largest deviation of 2.2 mm.

Routeliner runs in QGIS 3.40 and QGIS 4, with the interface and the manual in English and Russian, under GPL 2 or later.

Plugin page: https://plugins.qgis.org/plugins/routeliner/
Source: https://github.com/Valery35/routeliner
```

## LinkedIn

```
Routeliner is a free QGIS plugin for linear referencing with real-world chainage.

Survey and maintenance records along roads, pipelines and power lines usually carry a station, not coordinates. Routeliner places them on the route axis. It handles a chainage ledger with station equations, as practised in the CIS.

The plugin builds a longitudinal profile with raster levels and grades. It also reads chainage from route M values and writes it into the M of results, so PostGIS and ArcGIS read the layers.

It runs in QGIS 3.40 and QGIS 4 and is open source under GPL 2 or later.

https://plugins.qgis.org/plugins/routeliner/

#QGIS #GIS #LinearReferencing #OpenSource #Pipelines #Roads
```

## Mastodon, en.osm.town

```
Routeliner is a free QGIS plugin that places route records by station instead of coordinates. It handles CIS chainage ledgers with station equations, builds longitudinal profiles and writes chainage into M values for PostGIS and ArcGIS.

https://plugins.qgis.org/plugins/routeliner/

#QGIS #GIS #OpenSource
```

## X, @Valery35

```
Routeliner, a free QGIS plugin: route events by station, chainage ledgers with station equations, longitudinal profiles and M values for PostGIS and ArcGIS. https://plugins.qgis.org/plugins/routeliner/ #QGIS #GIS
```

## Reddit r/QGIS

Заголовок.

```
Routeliner: a free QGIS plugin that places table records on routes by station, with CIS chainage ledgers and station equations
```

Текст.

```
Routeliner places records that carry a station instead of coordinates onto the axis of a road, a pipeline, a power line or a mine working.

It reads five station notations used in the CIS, such as PK 15+35, km 1+535 and the railway notation. It also handles a ledger with broken pickets, forward and backward station equations and several chainage systems on one route.

What it does:
- point events and sections by station, with an offset from the axis
- live layers that are recalculated after edits of routes, tables or the ledger
- picket stakeout and locating any point on a route
- a longitudinal profile with raster levels, grades and a straightened plan for a print layout
- chainage read from and written to M values, so PostGIS and ArcGIS read the layers

A record that cannot be placed goes to an error table with a reason code. A demo project with analytically computed reference answers checks the plugin on your own machine.

It runs in QGIS 3.40 and QGIS 4, with the interface and the manual in English and Russian. The plugin is free and open source under GPL 2 or later.

Plugin page: https://plugins.qgis.org/plugins/routeliner/
Source: https://github.com/Valery35/routeliner

Feedback on what your linear referencing work is missing is welcome.
```

## Reddit r/gis

Заголовок.

```
Linear referencing with real-world chainage: station equations, broken pickets and M values in a free QGIS plugin
```

Текст.

```
Survey records along roads, pipelines and power lines usually carry a station, not coordinates. In CIS practice the chainage also jumps at station equations. A ledger of reference points fixes the stations where measured length and nominal chainage disagree.

Routeliner is a QGIS plugin built around that ledger. It places point events and sections by station and finds the station and offset for any point. It also stakes out pickets and builds a longitudinal profile. In a backward equation the same station occurs twice, and the plugin resolves it by section number instead of guessing.

Chainage can come from a ledger, from control points with known stations or from route M values. Results can carry the chainage in M, with two vertices at each equation. PostGIS and ArcGIS read such layers.

A demo project with analytically computed answers runs the whole chain. In a run of 3000 events the largest deviation was 2.2 mm.

Plugin page: https://plugins.qgis.org/plugins/routeliner/
Source: https://github.com/Valery35/routeliner
```

## Telegram, @qgis_isolines

Черновик присылает бот PlanetX после публикации релиза 0.5.2 на GitHub.
