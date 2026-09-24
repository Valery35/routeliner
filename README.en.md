[Русский](README.md) | **English**

# Routeliner

Routeliner is a QGIS plugin that places table records on the axes of roads,
tracks, pipelines and power lines when a record carries a station instead of
coordinates. The plugin reads the five station notations
accepted in the CIS countries and takes into account a ledger with broken
pickets and station equations.

Every record is either placed on the map or sent to the error table with a
reason code. A longitudinal profile with raster levels, grades and ledger
stations is built along a route.

The route chainage can be taken from the M values of its geometry and written
into the M of the results. PostGIS, ArcGIS and the QGIS tools for M read such
layers.

## Tools

The tools sit in the Processing Toolbox in the Routeliner group and are
repeated in the Plugins - Routeliner menu under the same numbers.

| Number | Tool | Result |
|---|---|---|
| 1.01 | Demo example | GeoPackage with reference answers and a self-check of the plugin |
| 1.02 | Route check | Assembled routes, gaps and branches |
| 1.03 | Calibrate routes | Routes with chainage in the M values of their vertices |
| 2.01 | Point events | Points by station with an offset from the axis |
| 2.02 | Sections (line events) | Route pieces between two stations |
| 3.01 | Live layer of point events | A layer recalculated after edits of the source data |
| 3.02 | Live layer of sections | The same for sections |
| 4.01 | Picket stakeout | Points of whole pickets with station equations taken into account |
| 4.02 | Locate points on routes | Measure, station and offset for every point |
| 5.01 | Profile table | Profile points with stations and raster levels |
| 5.02 | Profile drawing | Longitudinal profile with a grid and a straightened plan for a print layout |

## Installation

The plugin is installed from the QGIS plugin repository or from a ZIP archive
through Plugins - Manage and Install Plugins - Install from ZIP. It requires
QGIS 3.40 or newer, QGIS 4 on Qt6 included, and there are no external
dependencies, because the computation runs on the NumPy that ships with QGIS.

The interface language follows the language of QGIS, so with a Russian locale
the interface is Russian, and with any other locale it is English.

## Documentation

The PDF manual opens from Plugins - Routeliner - Manual (PDF) and describes
the tool parameters and the fields of every layer the plugin creates. The
source text is in [manual/manual_en.md](manual/manual_en.md), and the Russian version is in
[manual/manual.md](manual/manual.md).

## Development

The computation core in routeliner/core does not depend on QGIS and is
checked by tests without QGIS.

```
python -m pytest
```

The interface translation dictionary is built from the Russian strings of the
code, and it has to be rebuilt after these strings change.

```
python tools/make_translations.py
```

The rules for work on the repository are in [AGENTS.md](AGENTS.md), and the
version history is in [CHANGELOG.md](CHANGELOG.md).

## License

GNU GPL version 2 or later, see [LICENSE](LICENSE).

- - -

Developed with the support of Inform++ LLC ([www.informpp.ru](https://www.informpp.ru)).

Plugin page: [github.com/Valery35/routeliner](https://github.com/Valery35/routeliner)

Routeliner v0.5.0

Routeliner grows on tasks of real enterprises. If your production lacks a
function, write to us:
[www.informpp.ru/главная-страница/предприятиям](https://www.informpp.ru/главная-страница/предприятиям)
