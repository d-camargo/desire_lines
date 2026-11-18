# OD Matrix

The **Origin/Destination Matrix** tab is the first of the plugin's four tabs.
It prepares the two inputs that every other tab uses: the OD matrix read as a
table and the centroids of the traffic zones, writing both to the same output
GeoPackage.

## Step by step

1. **Import the matrix.** Choose the CSV in the file selector (filter
    `CSV(*csv)`) and click *Read CSV*. Reading assumes **windows-1252**
    encoding and the **`;`** delimiter, with no geometry. The table enters the
    project as `matrix` and is written to the GeoPackage as the `output`
    table.

2. **Wide or long format.** Check *Travel Demand Matrix format* when the matrix
    is in **wide format** — an `OD` column plus one column per destination. The
    plugin converts it to **long format** with `pandas.melt` (`id_vars='OD'`),
    producing the columns `Origem`, `Destino` and `Passageiros`, writes a
    `matrix_long.csv` next to the original file and uses that file from then
    on. When unchecked, the matrix must already be in long format (one row per
    OD pair).

    !!! warning "Requires pandas"
        The wide→long conversion depends on `pandas` being available in
        QGIS's Python. Without it, the plugin shows an error message asking
        you to install the library and reload the plugin.

3. **Traffic zones.** The *Traffic zone (shp or gpkg format)* layer comes in
    through two equivalent paths:

    - import a SHP/GPKG in the selector and click *Read Vector* — the layer
      enters the project as `traffic_zones` and is automatically selected in
      the combo right below; or
    - in the combo "…or assign an existing traffic-zones layer from the
      project (leave empty to use the imported file above):", pick a polygon
      layer already open in the project — the combo only lists polygon layers
      and may be empty.

    If the combo is empty, the centroids button falls back to looking for a
    layer named `traffic_zones`.

4. **Output GeoPackage.** The file selector (filter `GeoPackage (*.gpkg)`)
    sets where everything is written; if the path does not end in `.gpkg`, the
    extension is appended. If left blank, the plugin uses an `output.gpkg` in
    the folder of the matrix CSV — or, failing that, in the folder of the
    vector file, and as a last resort in the user's home folder. It is worth
    filling this in explicitly so you know where the result ended up.

5. **Add Centroids to Traffic Zones.** Runs the `native:centroids` algorithm
    with `ALL_PARTS=True` (one centroid feature per part of a multipolygon) on
    the chosen zones layer, writes the `centroids` table to the GeoPackage and
    adds the layer to the project.

## What ends up in the GeoPackage

| Table | Contents |
|---|---|
| `output` | The OD matrix as a table, without geometry — one row per OD pair |
| `centroids` | Points, one per zone (or multipolygon part), inheriting the attributes of the zones layer |

The following tabs read exactly these two layers. For the expected format of
the matrix CSV and the zones layer, see [Input formats](../referencia/formatos-de-entrada.md).

## What the next tabs will ask of this matrix

The *Origin*, *Destination* and *Traffic ID* combos appear in the following
tabs (Desire Lines, AoN (Delaunay), Highway Assignment), not in this one — but
this is where you decide whether they will have anything to choose from:

- the matrix must have an origin column, a destination column and a
  value/flow column, one row per OD pair;
- *Origin* and *Destination* point to the identifier columns of the matrix;
- *Traffic ID* points to the field of the centroids layer that carries the
  same identifier;
- the value field — *Value to Desire Lines*, in the next tab — is the numeric
  flow column.

In the wide→long conversion the resulting columns are named `Origem`,
`Destino` and `Passageiros`.

!!! warning "The ids must use the same scheme"
    The matrix identifiers and the centroid id field must use the same
    coding scheme. When they do not, the assignment finds no pair at all and
    the plugin warns "No OD pairs matched the centroid ids" — see
    [Troubleshooting](../solucao-de-problemas.md).

**Next step:** [Desire lines](linhas-de-desejo.md).
