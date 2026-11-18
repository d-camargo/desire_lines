# AoN (Delaunay)

The **AoN (Delaunay)** tab performs an **All-or-Nothing** assignment of the OD
matrix over a **synthetic network** built from the zone centroids themselves.
It is the intermediate step between the per-pair reading
([Desire lines](linhas-de-desejo.md)) and the loading of the actual road
network ([Highway Assignment](alocacao-rodovias.md)).

!!! danger "The Delaunay network is **not** the real road network"
    The network is the **Delaunay triangulation** of the centroids: each zone
    is linked to its geographic neighbours by straight segments. This is a
    **topological abstraction of neighbourhood**, not a representation of
    highways — there are no roads, directions, capacity or speed in it. The
    volumes per edge tell *where demand crosses the territory*, not how many
    vehicles use a highway. For highway volumes, use the
    [Highway Assignment](alocacao-rodovias.md) tab.

## What "All-or-Nothing" means here

For each OD pair, **all** of the flow follows the **single least-cost path**
between origin and destination, and is added to each edge of that path. The
cost is the segment **length** — there is no time, speed or congestion. Since
there is no capacity feedback into the cost, there are also no alternative
routes and no equilibrium: a heavily loaded edge does not push trips onto
another path. The network is **bidirectional** — both A→B and B→A exist.

## Inputs

| Field | What to choose |
|---|---|
| *Matrix* | The OD matrix layer — the combo only lists layers **without geometry** |
| *Centroids* | The centroids layer — the combo only lists **point** layers |
| *Origin* | Origin zone id column in the matrix (**integer** field) |
| *Destination* | Destination zone id column in the matrix (**integer** field) |
| *Value (flow)* | **Numeric** flow column to be assigned |
| *Traffic ID* | Field of the **centroids** with the same id used in Origin/Destination (**integer** field) |

The *Allocate (AoN)* button is only enabled with both layers and all four
fields filled in. **At least 3 valid centroids** are required — with fewer
there is no triangle to triangulate, and the plugin warns and aborts.

!!! warning "The ids must use the same scheme"
    Matrix rows whose origin or destination id does not exist among the
    centroids are discarded and counted in the final message. If no pair
    matches, the assignment does not even run — see
    [Troubleshooting](../solucao-de-problemas.md).

## Split by direction (flow_ab / flow_ba)

The *Split by direction (flow_ab / flow_ba)* checkbox controls the fields of
the output layer:

| Field | When it appears | Meaning |
|---|---|---|
| `flow` | always | Total on the segment = `flow_ab + flow_ba`. This is the field used by the style. |
| `flow_ab` | only with the box checked | Volume in the **drawn** direction of the segment, from the first to the last vertex |
| `flow_ba` | only with the box checked | Volume in the opposite direction |

!!! note "AB/BA are the directions of the segment, not origin/destination"
    `ab`/`ba` refer to the **orientation of the drawn geometry**, anchored on
    the vertices of the line — not to the origin and destination of the
    matrix. The AB/BA convention is the one used for link direction in
    transport software (TransCAD, Cube, Emme) precisely so that it is not read
    as O/D. Leave the box unchecked when you only care about the total loading
    of the segment.

## Automatic choice of a metric CRS

Shortest path by length requires **metric** units: distances measured in
degrees distort the result, because a degree of longitude is not worth the
same as a degree of latitude. The plugin handles this on its own, reprojecting
the centroids before triangulating:

| State of the centroids | CRS used in the assignment |
|---|---|
| CRS is already **projected/metric** | used **as is** |
| **Geographic** and the area fits in a **single UTM zone** (same hemisphere) | the zone's **UTM WGS84**, chosen automatically |
| **Geographic** and the area spans **more than one UTM zone** or crosses the equator | **SIRGAS 2000 / Brazil Albers (EPSG:10857)** — an equivalent projection, in metres, IBGE standard |
| None applicable | the plugin **aborts** and asks you to reproject the centroids to a metric system |

The success message at the end reports which CRS was chosen, how many pairs
were assigned, over how many edges, and the losses: **unreachable** pairs
(disconnected graph), matrix rows with unknown ids, and **skipped** pairs
(origin equal to destination, or origin absent from the network). It is worth
reading this message — it is the only place where the losses appear.

## The result

The layer is written as the **`aon_flows`** table in the same output
GeoPackage as the matrix tab, added to the project and styled by `flow` (the
same graduated-by-width renderer as the desire lines, and equally editable in
*Layer Properties → Symbology*). The geometry is in the chosen metric CRS,
which may differ from that of the input layers.

## When this result is useful

It works well for:

- seeing **where demand crosses the territory** and which links between
  neighbouring zones concentrate flow, when no road network is available;
- comparing matrix scenarios (before/after) over a fixed network that is cheap
  to build;
- a quick consistency check of the matrix and centroids before the heavier
  work of the highway tab.

It is not suitable for:

- estimating **highway volume**, v/c, level of service or anything that
  depends on capacity — the network is synthetic and has no capacity;
- studying routes or detours: there are no alternative paths in
  All-or-Nothing, and the edges are not roads.

**Next step:** [Highway Assignment](alocacao-rodovias.md).
