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
Field names in the results are the same in both languages, so expressions,
styles and projects work in any locale. The attribute table and forms show
field aliases in the interface language, for example Measure, m instead of
rl_m.

# Menu, toolbar and log

The plugin adds the Plugins - Routeliner menu and the Routeliner toolbar. The
menu holds all tools under their numbers and the items Manual (PDF), Work log
and About. The toolbar has two buttons. The first opens the same list of tools,
the second opens the About window.

The About window shows the version and links to the site, the source code and
the bug tracker. Its buttons open the version history, the manual, the log and
the log folder. The bottom of the window shows the last lines of the log, so
an error can be read without looking for the file.

The work log is written to the file routeliner.log in the QGIS profile folder.
It receives the plugin load with the plugin and QGIS versions, every tool run
with its parameters and running time, the warnings of a tool and the
recalculation of live layers. A failure is written together with its call
stack. When the plugin loads, a file larger than 2 MB is renamed to
routeliner.log.old, and the log starts anew.

In case of an error it is enough to attach the log to a message on the bug
tracker. Log entries are written in Russian whatever the interface language.

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

**M values.** The fourth coordinate of a line vertex next to X, Y and Z. M
holds the chainage, odometer readings or a measure from another program. The
plugin reads the chainage from the M of a route and writes the chainage or the
measure into the M of a result. PostGIS, ArcGIS and the QGIS tools for M read
such layers.

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
on, the example runs through tools 1.02, 1.03, 2.01, 2.02, 4.01, 4.02, 5.01
and 5.02 at once, and the result of the comparison goes to the log.

Calibration is checked in a round trip. Tool 1.03 moves the ledger chainage
into the M of the routes. Then the same point events are placed by M without
the ledger and compared with the reference.

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

## 1.03 Calibrate routes

The tool assembles the routes and writes the chainage into the M of every
vertex. The result serves as a route with ready chainage for other programs and
for the plugin itself. The chainage source is chosen per route in this order:
control points, ledger, M of the routes themselves, length along the axis.

A control point carries a known station, for example a marker post on the line
or a survey point. The point is located on the nearest route within the search
radius, and its measure becomes a reference point. Between the points the
station runs linearly, and before the first and after the last point with a
scale of 1.

At a station equation the line gets two vertices at one point. The first
carries the station back, the second the station ahead.

| Parameter | Meaning |
|---|---|
| Control points with stations | Optional point layer |
| Control points: station field | Station in the selected notation |
| Control points: route ID field | Restricts locating to one route |
| Search radius for control points, m | 10 m by default |
| M values of the result | Chainage by default, or measure along the axis |

| Result field | Type | Content |
|---|---|---|
| route_id | text | Route ID |
| length | number | Length along the axis, m |
| st_from, st_to | number | Chainage of the start and the end, m |
| pk_from, pk_to | text | Stations of the start and the end in the selected notation |
| sections | integer | Number of chainage sections |
| equations | integer | Number of station equations |
| source | text | Chainage source: points, ledger, m or length |

## Common route and chainage parameters

These parameters belong to tools 1.02, 1.03, 2.01, 2.02, 3.01, 3.02, 4.01,
4.02 and 5.01.

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
| Chainage from the M values of the route geometry | The route chainage is taken from the M of its vertices |
| Metres per M unit | 1 by default, 1000 for M in kilometres |

A ledger row with an empty station ahead is a reference point, and a row with a
station ahead is an equation. The measure of an equation may be empty, in which
case the equation position is computed from the neighbouring reference points.
Before the first and after the last reference point the ledger is extended to
the route ends with a scale of 1.

Chainage from M goes to a route without ledger rows, because the ledger takes
precedence. A route without M keeps the chainage by length. Between vertices
the station runs linearly, and a vertex without M is skipped. Two vertices at
one point with different M are read as a station equation, including at the
joint of two features.

Tools 1.03, 2.01, 2.02 and 4.01 write M into the result geometry when the
parameter M values of the result asks for it. By default no M is written, and
the choices are the measure along the axis and the chainage, both in metres. At
an equation a section gets two vertices at one point, with the station back and
the station ahead.

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
| M values of the result | No M, measure along the axis or chainage |

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

## 5.01 Profile table

The tool collects the points of a longitudinal profile along every route and
samples raster values at them. Points are placed at the route start and end,
at station equations, at whole pickets, at axis vertices and with a constant
step. Points closer than 1 cm along the measure are merged into one.

A raster may be terrain, a design surface, the roof or floor of a seam, the
groundwater level or any other surface. The value is interpolated bilinearly
between cell centres, and the raster may be in any coordinate system.

Points from an event layer, such as crossings, manholes or boreholes, are put
on the profile by projection onto the axis. A point gets onto the profile only
when it lies closer to the axis than the corridor parameter allows.

| Parameter | Meaning |
|---|---|
| Routes separated by commas | Empty - all routes of the layer |
| Rasters | One or several rasters, one field for each |
| Raster band number | 1 by default |
| Points at whole pickets every, m | 100 m by default, 0 - no pickets |
| Points with a constant step, m | 0 by default - no step |
| Axis vertices | Only with a turn above 1° or a grade break above 1 ‰, all vertices or no vertices |
| Events for the profile | Optional point layer and label field |
| Events: corridor from the axis, m | 10 m by default |

The other parameters are those of the section Common route and chainage
parameters.

| Result field | Type | Content |
|---|---|---|
| route_id | text | Route ID |
| n | integer | Point number in the order of the measure |
| kind | text | Point kind, start, end, equation, event, picket, vertex or step |
| m | number | Measure along the axis, m |
| station | number | Chainage, m, chainage back for an equation |
| station_ahead | number | Chainage ahead, filled for an equation only |
| pk | text | Station in the chosen notation, both stations with an equals sign for an equation |
| section | integer | Chainage section number |
| x, y | number | Point coordinates on the axis |
| z_axis | number | Axis elevation from the route Z, empty without Z or with zero Z |
| turn | number | Turn angle of the alignment at a vertex, degrees, positive to the left |
| label | text | Event label |
| z_name | number | Raster value, the field name is built from the raster layer name |

## 5.02 Profile drawing

The tool builds the drawing of the longitudinal profile of one route from the
5.01 table. Surface lines and the elevation scale are drawn above the grid,
and the grid rows and the straightened plan go below them. The scale ticks
are at least 5 mm apart, and the labels at least 10 mm.

The drawing is placed in the same coordinate system as the table, in paper
millimetres. One map unit equals one millimetre, so in a QGIS print layout the
profile prints at full size with the map scale 1:1000. If the lower left
corner is not given, the drawing is placed below the routes with a margin of
100 units.

The grid is set by a table of rows, and by default it holds the Pipeline
template. Rows can be removed, added and reordered. A row without data is not
put into the grid, so the drawing has no empty rows.

| Row table column | Meaning |
|---|---|
| Title | Text in the title column on the left |
| Type | value, text, grade, distance, station or plan |
| Source | A QGIS expression for value and grade, a field of the section layer for text |
| Decimals | Number of decimals in the labels |
| Height, mm | Row height, 0 - the row only draws a line above the grid |
| Line (1/0) | 1 - the values of a value row are drawn as a line above the grid |

| Row type | What is drawn |
|---|---|
| value | A number at every point from an expression over the profile table fields |
| text | Section labels from a field of the section layer, with separators at the boundaries |
| grade | Grade in per mille and length of the sections of constant grade |
| distance | Distances along the measure between neighbouring labelled points |
| station | Point stations, an equation in two lines |
| plan | Straightened plan with the axis, turn angles and points with offsets |

Expressions may use the profile table fields and the placeholders {ground},
{design}, {pipe}, {d} and {base}. The first three are replaced by the fields
chosen in the parameters, and the last two by the pipe diameter and the
bedding thickness. If a placeholder is not set, the row is skipped with a log
message.

| Pipeline template row | Type | Source |
|---|---|---|
| Design ground level, m | value | {design} |
| Existing ground level, m | value | {ground} |
| Pipe top level, m | value | {pipe} |
| Trench bottom level, m | value | {pipe} - {d} - {base} |
| Ground to pipe, m | value | {ground} - {pipe} |
| Trench depth, m | value | {ground} - ({pipe} - {d} - {base}) |
| Pipe type and coating | text | field pipe of the section layer |
| Bedding | text | field base of the section layer |
| Grade, ‰ / length, m | grade | {pipe} |
| Distance, m | distance | |
| Station | station | |
| Straightened plan | plan | |

Grade sections are found by vertical simplification of the line, and the
simplification tolerance is a parameter with a default of 0.02 m. A short
section is crossed by a diagonal from corner to corner. On a section longer
than four row heights such a diagonal almost merges with the row border, so a
grade sign four row heights wide is drawn at the section centre. Sections for
text rows come from the result of 2.02 or from any table with start and end
measure fields.

Point labels are thinned when the points are closer on paper than the given
gap, 3 mm by default. The label stays at the point with the higher priority.
The priority falls from the route start and end to an equation, an event, a
picket, a vertex and a step point.

The straightened plan is built from points with the fields rl_m and rl_offset,
that is from the result of 4.02. The plan is schematic, so offsets are
compressed until the farthest point fits into the row.

| Parameter | Meaning |
|---|---|
| Profile table | Result of 5.01 |
| Route | Empty - the first route of the table |
| Ground level field {ground} | Usually the field of the terrain raster |
| Design level field {design} | Optional field |
| Pipe or axis level field {pipe} | Empty - z_axis |
| Pipe outer diameter {d}, m | 0.16 m by default |
| Bedding thickness {base}, m | 0.3 m by default |
| Horizontal and vertical scale | 1:500 and 1:100 by default |
| Datum, m | Empty - 1 m below the lowest level rounded down to a metre |
| Smallest gap between labels, mm | 3 mm by default |

The result consists of two layers. The line layer holds the fields kind (line
kind), row (row), color (colour) and width (width, mm). The label layer holds
the fields text, kind, rot (rotation, degrees), size (height, mm), halign and
valign. The style of both layers is set on loading and takes colour, width,
rotation and alignment from these fields.

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

The terrain raster routeliner_demo_dem.tif with a 5 m cell is written next to
it. The terrain is an inclined plane z = 151.5 + 0.01 (x - 455000) + 0.02 (y -
6428000), and bilinear interpolation on a plane is exact. Along R1 the ground
lies 1.5 m above the axis, so on the profile the R1 axis looks like a pipe. That is why profile
levels are checked against the formula and not against the raster itself.

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

Measures, lengths, offsets, coordinates and levels in the result fields are
rounded to 0.001 m, and angles to 0.01°. This rounding is finer than the
computation error described below.

Accuracy is checked on the demo example. A run with seed 42 and 3000 random
events in QGIS 4.0.3 matched all 3002 point events with the reference, with a
largest deviation of 2.2 mm. All 1500 defects of the same run were located on
their own route with a deviation of the measure and the offset below 1 cm.

In the same run the profile table along routes R1-R3 gave 573 points. The
terrain levels at all points matched the plane formula with a deviation of at
most 0.5 mm, which comes from rounding the values to a millimetre. The axis levels of R1 matched at all 194 points, and both
equations of R3 got into the table.

Calibration in the same run wrote both ledger equations into the M of route
R3. All 2976 point events without a section number, placed by M without the
ledger, matched the reference within 1 cm.

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
| Set M value | One M value for all vertices | Chainage in M from a ledger or control points, with equations |
| Linear Referencing symbol layer (since 3.40) | Distance labels along a line at rendering | Pickets as layer features with fields |
| Elevation profile (since 3.26) | Profile of surfaces along a line in a separate panel | Profile grid with ledger stations, grades and a straightened plan as layers for a print layout |
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

Chainage sections from M are numbered by breaks of scale and by equations, not
by the ledger reference points. A section number from an events table set by
the ledger can therefore shift after calibration. The number for chainage from
M is best taken from the picket stakeout 4.01 of the same route.

The profile drawing is built for one route per run and with one datum. That is
why the profile of a long alignment with a large height difference comes out
tall.

Unlike the live layers 3.01 and 3.02, the profile drawing is not recalculated
by itself after data edits. After an edit tools 5.01 and 5.02 have to be run
again.

- - -

Developed with the support of Inform++ LLC ([www.informpp.ru](https://www.informpp.ru)).

Plugin page: [github.com/Valery35/routeliner](https://github.com/Valery35/routeliner)

Routeliner v0.5.1

Routeliner grows on tasks of real enterprises. If your production lacks a
function, write to us:
[www.informpp.ru/главная-страница/предприятиям](https://www.informpp.ru/главная-страница/предприятиям)
