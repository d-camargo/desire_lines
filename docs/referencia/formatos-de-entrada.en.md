# Input formats

This page describes the requirements, specifications and conventions for all input data accepted by the **Desire Lines** plugin.

---

## 1. Origin/Destination Matrix (CSV)

The OD matrix is the CSV file containing trip volumes or flows between pairs of zones.

### Long Format

This is the **default format** expected by the plugin's calculation and assignment steps. Each row of the table represents a single Origin-Destination pair.

| Origem | Destino | Passageiros |
|---|---|---|
| 101 | 102 | 450.5 |
| 101 | 103 | 120.0 |
| 102 | 101 | 380.0 |
| 102 | 103 | 95.0 |

* **Origem (Origin):** Numeric or alphanumeric identifier of the origin zone.
* **Destino (Destination):** Numeric or alphanumeric identifier of the destination zone.
* **Value / Flow:** Demand volume (passengers, vehicles, tonnes, etc.), given as a numeric value (integer or decimal).

!!! note "Column names"
    The column names in the CSV file can be arbitrary, since they are selected through the *comboboxes* in the plugin's tabs. If the matrix goes through automatic conversion from the wide format, the plugin uses `Origem`, `Destino` and `Passageiros` as the default names.

---

### Wide Format

The wide (matrix) format is a table structure with one origin column and one column for each destination zone.

| OD | 101 | 102 | 103 |
|---|---|---|---|
| **101** | 0 | 450.5 | 120.0 |
| **102** | 380.0 | 0 | 95.0 |
| **103** | 110.0 | 85.0 | 0 |

To use a matrix in wide format:

1. In the **Origin/Destination Matrix** tab, check the **Travel Demand Matrix format** option.
2. The first column of the CSV must be named exactly **`OD`**.
3. The remaining columns represent the destination identifiers.
4. When you click **Read CSV**, the plugin automatically converts the matrix to long format using `pandas.melt`, saves the `matrix_long.csv` file in the same directory as the original CSV, and loads the latter into the output GeoPackage.

!!! warning "Dependency on the pandas library"
    Converting from wide to long format depends on the `pandas` library being installed in the QGIS Python environment. If the library is missing, an error message is shown asking you to install it.

---

### Technical Reading Properties

When importing the matrix CSV file, the plugin uses QGIS's native delimited-text driver with the following fixed settings:

* **Encoding:** `windows-1252` (the default CSV export encoding on Brazilian Windows systems).
* **Field delimiter:** Semicolon (`;`).
* **Geometry type:** None (`geomType=none`).

---

### Handling Matrix Inconsistencies

| Scenario / Inconsistency | Plugin behavior |
|---|---|
| **Origin = Destination pairs (self-pairs)** | Automatically discarded (`WHERE origin != dest` in the SQL queries, and ignored in the assignment algorithms). |
| **Duplicate pairs in the matrix** | Assigned cumulatively (flows from repeated rows for the same OD pair are summed during assignment). |
| **Origin/destination zone missing from the centroids** | The OD pair finds no geographic match, is recorded as not found (`skipped` / `missing`) and is counted in the warning bar at the end of the assignment. |
| **Null or invalid flow values** | Rows with a null or non-numeric flow value are ignored during the calculation. |

---

## 2. Traffic Zones and Centroids

### Traffic Zone Layer (Polygon Vector)

The traffic zone layer represents the territorial division of the study area into polygons.

* **Geometry type:** Polygon (`Polygon`) or MultiPolygon (`MultiPolygon`).
* **Supported formats:** GeoPackage (`.gpkg`), ESRI Shapefile (`.shp`) or any polygon layer supported by QGIS.
* **Required attribute:** At least one column containing the unique zone identifier (*Traffic ID*).
* **Coordinate Reference System (CRS):** Any valid CRS (geographic or projected).

---

### Centroid Layer (Point Vector)

Centroids are the point representation of each traffic zone and serve as origin and destination nodes in the desire line and network assignment calculations.

* **Geometry type:** Point (`Point`) or MultiPoint (`MultiPoint`).
* **Automatic generation:** When you click **Add Centroids to Traffic Zones** on the first tab, the plugin runs the native `native:centroids` algorithm with `ALL_PARTS=True` (generating one centroid for each part of a multipolygon and inheriting the attribute table of the zone layer).
* **Required attribute:** Must have the *Traffic ID* field, with values matching the IDs present in the OD matrix.

---

## 3. Road Network (Tab 4 — Highway Assignment)

For traffic assignment on real networks (the **Highway assignment** tab), the road layer has specific geometry and attribute requirements.

* **Geometry type:** Line (`LineString`) or MultiLineString (`MultiLineString`).
* **Data source:** A highway vector layer loaded in QGIS (e.g. SNV/DER) or downloaded directly through the integration with the **GISBR** plugin.
* **Input attributes (Rule D7 — Provenance):**
    * The network attributes (number of lanes, road type, free-flow speed, etc.) can be mapped from existing columns in the layer.
    * If the layer does not have these fields, the plugin automatically applies default parameters aligned with DNIT and HCM standards, recording the data provenance in the `src_*` fields of the resulting layer.
* **Scope classification:** The procedure computes highway capacity for rural/intercity segments. Segments located in urban crossings are kept in the network but flagged with `escopo = 'urbano'`.

For more details on the provenance of the road network parameters, see the [HCM Parameters](parametros-hcm.md) page.

---

## 4. Zone ID Normalization (`_zone_key`)

A common cause of failure when joining data tables is a mismatch in attribute types (e.g. the matrix has the ID as the integer `101` while the centroid layer holds the ID as the text `"101"` or as the float `"101.0"`).

To guarantee full compatibility without requiring any prior manual conversion by the user, the plugin internally applies the normalization function **`_zone_key`**:

```python
@staticmethod
def _zone_key(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return str(value).strip()
```

### `_zone_key` Conversion Rules:

1. **Null values (`None`):** Returns `None`.
2. **Integer or integer numeric string:** Tries to convert directly to `int` (e.g. `101` or `"101"` becomes `101`).
3. **Float or string with a decimal point:** If the simple conversion fails, it tries to convert to `float` and then to `int` (e.g. `101.0` or `"101.0"` becomes `101`).
4. **Alphanumeric codes:** If the value cannot be converted to a number, it is converted to a `string` and leading/trailing whitespace is removed (e.g. `" ZONA_A "` becomes `"ZONA_A"`).

This way, the comparison between the matrix key and the centroid key always works, regardless of how the QGIS data provider or the CSV file interpreted the data type.
