# Desire lines

The **Desire Lines** tab generates **one straight line per OD pair**,
connecting the centroid of the origin zone to the centroid of the destination
zone, with **thickness proportional to the flow value**. It is the most direct
visual reading of the matrix: where demand wants to go, without going through
any network.

!!! note "Before you start"
    This tab consumes the two layers produced in the previous tab — the matrix
    (`output` table) and the `centroids`. See [OD Matrix](matriz-od.md).

## Inputs

| Field | What to choose |
|---|---|
| *Matrix* | The OD matrix layer — the combo only lists layers **without geometry** |
| *Centroids* | The centroids layer — the combo only lists **point** layers |
| *Origin* | Origin zone id column in the matrix (**integer** field) |
| *Destination* | Destination zone id column in the matrix (**integer** field) |
| *Value to Desire Lines* | **Numeric** flow column (trips, passengers, tons…) — this is what becomes the thickness |
| *Traffic ID* | Field of the **centroids** layer with the same id used in Origin/Destination (**integer** field) |

The *Desire Lines* button is only enabled when both layers and all four fields
are filled in — if it stays grey, some combo is missing.

!!! warning "The ids must use the same scheme"
    *Origin*, *Destination* and *Traffic ID* are matched by equality. If the
    matrix numbers zones one way and the centroids another, the result comes
    out empty. See [Troubleshooting](../solucao-de-problemas.md).

## What the button produces

The plugin builds the lines through a spatial SQL query over the two layers:
for each row of the matrix, it looks up the centroid whose *Traffic ID* equals
the *Origin*, the centroid whose id equals the *Destination*, and draws the
segment between the two. Pairs where origin and destination are the same zone
(intrazonal trips) are **discarded** — there is no line from a zone to itself.

The result is written as the **`Desire_Lines`** table in the same output
GeoPackage defined in the matrix tab, added to the project and styled
automatically. The layer carries three attributes — the **origin**,
**destination** and **value** fields, with the names they have in the matrix —
plus the line geometry, in the CRS of the centroids.

## How to read the result

- **Each feature is an OD pair**, not a path: the line is the
  origin→destination vector, it ignores the road network and represents
  neither a route nor a distance travelled.
- The matrix is normally **asymmetric**: if it has A→B and B→A as separate
  rows, you get **two overlapping lines** with different values. To see total
  flow per pair, add the two directions in the matrix before generating.
- Where there are many zones, the map turns into a tangle. Filtering the
  layer by a minimum value (`"<value field>" > x`) or by an origin of
  interest is usually more informative than displaying the whole matrix.
- For an estimate of **network loading**, rather than demand per pair, go to
  [AoN (Delaunay)](aon-delaunay.md) or to
  [Highway Assignment](alocacao-rodovias.md).

## The applied style — and how to reinterpret it

The layer is created with a **graduated renderer by classes** on the value
field, varying the **line width** (thicker = larger flow):

- **5 classes**, **Natural Breaks (Jenks)** method — groups similar values
  and cuts at the natural gaps of the distribution, a good default for flow
  maps;
- width from **0.2 mm to 3.0 mm**, single semi-transparent blue colour.

This style is an editable starting point, not a constraint: open
*Layer Properties → Symbology* and change whatever you need — the number and
limits of the classes, the classification method (equal interval, quantiles,
standard deviation), the minimum and maximum widths, or the colour. A light
blue→dark blue ramp is already loaded on the layer, so switching the
**Method** from *Size* to *Color* grades by colour with no further setup.

!!! tip "Why classes, and not data-defined width"
    Earlier versions computed the width with a data-defined expression, which
    the symbology panel **would not let you edit** — the expression always
    overrode a value typed by hand. With the graduated renderer, everything
    that appears in the panel is editable.

**Next step:** [AoN (Delaunay)](aon-delaunay.md).
