# Purpose

Routeliner places table records on linear features when a record carries a
station or a distance from the start of the alignment instead of coordinates. A
linear feature is called a route, and in practice it is the centre line of a
road, a railway track, a pipeline, a power line or a mine working. A table
record is called an event: a point event is tied to one station, and a line
event, or section, lies between two stations.

The plugin follows the survey practice of the CIS countries, so a station is
read in five accepted notations. The ledger holds broken pickets and station
equations, and one route may have several chainage systems. Every record is
either placed on the map or sent to the error table with a code and an
explanation of the reason.

The tools sit in the Processing Toolbox in the Routeliner group and are
repeated in the Plugins - Routeliner menu. A tool has the same number in both
places and in this manual.

# Installation and requirements

The plugin is installed from the QGIS plugin repository or from a ZIP archive
through Plugins - Manage and Install Plugins - Install from ZIP. It requires
QGIS 3.40 or newer, QGIS 4 on Qt6 included. There are no external dependencies,
because the computation runs on the NumPy that ships with QGIS.

The interface language follows the language of QGIS: with a Russian locale the
labels and messages are Russian, and with any other locale they are English.

# Terms

**Measure.** The distance along the route axis from its start, in the units of
the route coordinate system. All computations of the plugin go through the
measure, and a station is converted to a measure and back.

**Picket and chainage.** A picket is a mark on the alignment every 100 m, and
chainage is a distance in metres written as a picket number and a plus. The
record ПК 15+35 means 1535 m of chainage, and the picket length is a tool
parameter with a default of 100 m.

**Ledger.** A table of reference points in which every station is matched to a
measure along the axis, and between neighbouring reference points the chainage
changes linearly with the measure. The difference between chainage and measure
on a section is called the misclosure, and it comes from the projection scale
and from survey errors.

**Station equation.** A point of the alignment where the chainage jumps from
the value "back" to the value "ahead". When the value ahead is larger, the
equation is a forward one, and some chainage values never occur on the
alignment. When the value ahead is smaller, the equation is a backward one, and
some values occur twice.

**Chainage section.** A stretch of the route between neighbouring reference
points or equations on which the chainage is monotonic. Sections are numbered
from zero, and the section number is needed when a station falls into a
backward equation and is ambiguous without it.

**Chainage system.** One set of ledger rows for a route. A route may have a
design, an as-built and a former system, which differ by the value of the
system field in the ledger. A route without ledger rows gets its chainage along
the axis length from the given start station.

**Offset.** The distance from the axis along the normal. A positive offset lies
to the left of the route direction by default, and a check box in the event
tools reverses the sign.

# Station notations

The notation is chosen in the Station notation parameter and applies to the
whole table. A number without a plus is not accepted in the picket-and-plus
mode, because 1535 can mean both a picket number and metres.

| Notation | Examples | Chainage, m |
|---|---|---|
| Picket and plus | ПК 15+35, 15+35,5, пк15+35.5, ПК -1+50, ПК 15 | 1535, 1535.5, 1535.5, -50, 1500 |
| Picket and plus, relative | +35 after ПК 15+10 | 1535 |
| Kilometre and metres | км 1+535, 1+535.2 | 1535, 1535.2 |
| Railway notation | км 12 ПК 3+45 | 11245 |
| Metres as a number | 1535, 1535,5, 1 535,5 | 1535, 1535.5, 1535.5 |
| Kilometres as a decimal | 1,535 | 1535 |

In the railway notation kilometres and pickets are numbered from one, with ten
pickets per kilometre. A plus larger than the picket length is accepted,
because that is how long pickets are written.

# Tools

## 1.01 Demo example

The tool creates a GeoPackage with a data set on which the whole plugin is
checked. Every record carries a reference answer computed analytically from the
formulas of a line and a circle, without the plugin. With the check switched
on, the example runs through tools 1.02, 2.01, 2.02, 4.01 and 4.02 at once, and
the result of the comparison goes to the log.

| Parameter | Meaning |
|---|---|
| Folder for the example | Folder for routeliner_demo.gpkg and events_points.csv |
| Number of random point events | 60 by default, and half as many defects are created, at least 30 |
| Random seed | The same seed gives the same example |
| Run through the plugin at once | Switches on the check against the reference |

The content of the example is described in the section Demo example layers.

## 1.02 Route check

The tool assembles every route from all features of the layer with the same
ID. It is the tool to start with on new data, because it shows the routes that
the other tools will not be able to place events on.

Multi-lines are split into parts, and the parts are ordered by matching ends
rather than by storage order. Ends closer than the joint tolerance are merged
into one node.

The route direction is the one in which the larger share of the part length is
digitised, and the reverse check box turns it round. Arcs (CircularString,
CompoundCurve) are cut into chords with an angle of no more than 0.02°.

A gap larger than the tolerance and a branch of three or more ends at one
point count as errors. A geographic coordinate system counts as an error too,
because lengths in it come out in degrees. When gaps are allowed, the measure
continues across a gap without counting its length.

| Result field | Type | Content |
|---|---|---|
| route_id | text | Route ID |
| length | number | Length along the axis, m |
| parts | integer | Number of parts after assembly |
| gaps | integer | Number of gaps |
| gap_max | number | Largest gap, m |

## Common route and chainage parameters

These parameters belong to tools 1.02, 2.01, 2.02, 3.01, 3.02, 4.01 and 4.02.

| Parameter | Meaning |
|---|---|
| Route layer (lines) | Line layer with the route axes |
| Route ID field | Field by which features are assembled into a route |
| Part joint tolerance, m | 0.01 m by default |
| Allow gaps | A route with a gap does not go to the errors |
| 3D length | The measure takes Z into account |
| Reverse route direction | The route start moves to the other end |
| Station notation | One of the notations of the section Station notations |
| Picket length, m | 100 m by default |
| Route start station, m | Start chainage for routes without a ledger |
| Chainage ledger | Optional table of reference points and equations |
| Ledger: route ID field | Route ID in the ledger |
| Ledger: station field | Station of a reference point or station "back" of an equation |
| Ledger: distance field | Measure along the axis for a reference point |
| Ledger: station ahead field | Filled in the equation rows only |
| Ledger: chainage system field | Field with the system name |
| Chainage system | Value of the system field, rows of other systems are not read |

A ledger row with an empty station ahead is a reference point, and a row with a
station ahead is an equation. The measure of an equation may be empty, in which
case the equation position is computed from the neighbouring reference points.
Before the first and after the last reference point the ledger is extended to
the route ends with a scale of 1.

## 2.01 Point events

The tool places table records on the routes by station, with an offset from
the axis. Any QGIS layer serves as the table, CSV, Excel, DBF and a table
without geometry included. The record «+35» takes the picket number from the
previous record of the same route.

| Parameter | Meaning |
|---|---|
| Event table | Layer or table with the records |
| Events: route ID field | Route ID of the record |
| Events: station field | Station in the chosen notation |
| Events: offset from the axis field, m | Optional offset |
| Positive offset to the right of the route direction | Reverses the offset sign |
| Events: section number field | Section number for a station in a backward equation |

The result repeats all fields of the source record and adds the fields of the
plugin.

| Result field | Type | Content |
|---|---|---|
| rl_m | number | Measure along the axis, m |
| rl_pk | text | Station in the chosen notation, two decimals |
| rl_x, rl_y | number | Point coordinates in the route coordinate system |
| rl_azimuth | number | Axis azimuth at the point, degrees clockwise from north |

## 2.02 Sections (line events)

The tool cuts route sections between the start and end stations with a
parallel offset. A section recorded against the route direction is turned
over, and a section across a route gap comes out as a multi-line when gaps are
allowed. The parameters are those of tool 2.01, with two stations instead of
one.

| Result field | Type | Content |
|---|---|---|
| rl_m_from, rl_m_to | number | Start and end measures, m |
| rl_length | number | Section length along the axis, m |
| rl_pk_from, rl_pk_to | text | Start and end stations in the chosen notation |
| rl_swapped | integer | 1 when the start and the end were swapped |

## 3.01 Live layer of point events

The tool takes the parameters of tool 2.01 and creates two in-memory layers in
the Routeliner group, an event layer and an error layer. These layers are
recalculated by themselves 0.4 s after the last edit of the route layer, the
event table or the ledger. Recalculation also follows unsaved edits and a CSV
or Excel file changed on disk.

The binding of the layers is written to the project, and when the project
opens the in-memory layers are filled again, because QGIS saves them empty.
Removing the event layer from the project stops the recalculation, and the
fields of the layer are those of the result of tool 2.01.

## 3.02 Live layer of sections

The tool does for sections what tool 3.01 does for point events. Its
parameters and fields are those of tool 2.02.

## 4.01 Picket stakeout

The tool places points of whole pickets along every route with the stakeout
step. With a ledger, broken pickets and equations are taken into account, so
pickets skipped by a forward equation are not placed, and pickets repeated by
a backward equation are placed twice with different section numbers.

| Result field | Type | Content |
|---|---|---|
| route_id | text | Route ID |
| pk | text | Station in the chosen notation |
| station | number | Chainage, m |
| m | number | Measure along the axis, m |
| section | integer | Chainage section number, from zero |
| azimuth | number | Axis azimuth, degrees, for label rotation |
| km | integer | 1 for a picket that is a whole kilometre |

## 4.02 Locate points on routes

The tool solves the inverse task: for every point it finds the nearest route
and computes the measure, the station and the offset from the axis on it. A
point beyond the search radius goes to the error table. When the points have a
route ID field, a point is located on the given route only. Points in another
coordinate system are transformed to the route coordinate system.

| Result field | Type | Content |
|---|---|---|
| rl_route | text | Route ID |
| rl_m | number | Measure along the axis, m |
| rl_pk | text | Station in the chosen notation |
| rl_offset | number | Offset from the axis, m, positive to the left of the route direction |
| rl_side | text | Side relative to the route direction: left, right or axis |

The values of rl_side are written as codes, so that they do not depend on the
interface language.

# Error table

Tools 1.02, 2.01, 2.02, 3.01, 3.02 and 4.02 produce an error table without
geometry. It repeats the fields of the source record and adds three fields.

| Field | Content |
|---|---|
| rl_route | Route ID of the record |
| rl_error | Reason code, the same in both languages |
| rl_message | Explanation in the interface language |

| rl_error code | Reason |
|---|---|
| route_not_found | No route with this ID, or the route is not assembled |
| route_gap | The route falls apart with a gap larger than the tolerance |
| route_branching | Three or more part ends meet at one point |
| geographic_crs | The routes are in a geographic coordinate system |
| station_parse_failed | The station record does not match the chosen notation |
| station_out_of_range | The station is outside the route chainage |
| station_in_gap | The station falls into a forward equation |
| station_ambiguous | The station occurs twice in a backward equation, no section number given |
| measure_out_of_range | The measure is outside the route, or the point is beyond the search radius |
| ledger_invalid | The ledger is inconsistent, for example the chainage does not grow on a section |
| from_ge_to | Zero-length section |

# Demo example layers

Tool 1.01 writes five layers in the EPSG:32640 coordinate system to the file
routeliner_demo.gpkg. The fields with the exp_ prefix hold the reference answer
and are needed for the check only.

**routes.** Four routes. R1 is a 2000 m straight line with Z values from 150
to 170 m. R2 is a 500 m straight line, an arc of 300 m radius turning 90° to
the left and another 500 m straight line, with the arc stored as a
CompoundCurve. R3 is a polyline of four 400 m legs stored as three features
with parts in arbitrary order and one part reversed. R4 consists of two parts
with a 15 m gap and has to end up in the errors.

| Field | Content |
|---|---|
| route_id | Route ID, R1-R4 |
| name | Route description |

**ledger.** The as-built ledger of route R3. The misclosure over the first 400
m is 0.40 m, a backward equation of 25 m stands at the measure of 700 m, and a
forward equation of 40 m at the measure of 1300 m.

| Field | Content |
|---|---|
| route_id | Route ID |
| system | Name of the chainage system, «исполнительная» (as-built) |
| station | Station of a reference point or station "back" of an equation |
| measure | Measure along the axis, m |
| station_ahead | Station "ahead", filled for an equation only |
| note | Row explanation |

**events_points.** Point events, random and predefined. The same set is
written next to the GeoPackage to the file events_points.csv with a semicolon
as the separator.

| Field | Content |
|---|---|
| eid | Event number |
| route_id | Route ID |
| pk | Station in the picket-and-plus notation |
| offset | Offset from the axis, m |
| section | Section number for a station in a backward equation |
| exp_m | Reference measure, m |
| exp_x, exp_y | Reference coordinates |
| exp_error | Expected error code, empty for a valid record |
| note | Record explanation |

**events_lines.** Six sections, among them a section across the arc with a 10
m offset, a section across both equations of route R3 and a zero-length
section.

| Field | Content |
|---|---|
| eid | Section number |
| route_id | Route ID |
| pk_from, pk_to | Start and end stations |
| offset | Offset from the axis, m |
| exp_m_from, exp_m_to | Reference start and end measures, m |
| exp_error | Expected error code |
| note | Record explanation |

**defects.** Points near routes R1-R3 with offsets from 1 to 15 m to both
sides.

| Field | Content |
|---|---|
| did | Point number |
| exp_route | Reference route ID |
| exp_m | Reference measure, m |
| exp_station | Reference chainage, m |
| exp_offset | Reference offset, m, positive to the left |

# Accuracy

Accuracy is checked on the demo example. A run with seed 42 and 3000 random
events in QGIS 4.0.3 matched all 3002 point events with the reference, with a
largest deviation of 2.4 mm. All 1500 defects of the same run were located on
their own route with a deviation of the measure and the offset below 1 cm.

The deviation appears on arcs with an offset, because an arc is cut into
chords, and the normal to a chord differs from the normal to the arc by no
more than 0.01°. Chainage from a ledger does not depend on the cutting,
because it is computed through the measure.

# Relation to the standard QGIS tools

QGIS has tools that work with one line and one distance. Routeliner uses the
same geometry and adds the event table, the chainage and the ledger to it.

| QGIS tool | What it does | What Routeliner adds |
|---|---|---|
| Interpolate point on line | A point at a given distance from the start of one line | Station instead of distance, a table of records, offset, ledger |
| Line substring | Part of one line between two distances | Sections from a table, offset, route assembly from parts |
| Points along geometry | Points with a constant step | Picket stakeout with equations |
| Linear Referencing symbol layer (since 3.40) | Distance labels along a line at rendering | Pickets as layer features with fields |
| Network analysis, shortest path | A path over a road graph between points | Builds no networks, a path from network analysis can serve as a route |

Network analysis and Routeliner solve different tasks, because network analysis
searches for a path over a road graph, and Routeliner places data on an axis
that already exists. The result of the Shortest path tool fits as a route layer
once it has an ID field.

# Limitations

A live layer is recalculated as a whole and in the main QGIS thread, so on
tables of hundreds of thousands of records the interface stops for the time of
the computation.

The parallel offset of a section is built with sharp corners cut, so loops are
possible when the offset exceeds the radius of a curve on the section.

When gaps are allowed, the order of the route parts is set from the first part
in storage order to the nearest end. For parts lying far from each other, the
order is worth checking with tool 1.02.

- - -

Developed with the support of Inform++ LLC ([www.informpp.ru](https://www.informpp.ru)).

Plugin page: [github.com/Valery35/routeliner](https://github.com/Valery35/routeliner)

Routeliner v0.3.0

Routeliner grows on tasks of real enterprises. If your production lacks a
function, write to us:
[www.informpp.ru/главная-страница/предприятиям](https://www.informpp.ru/главная-страница/предприятиям)
