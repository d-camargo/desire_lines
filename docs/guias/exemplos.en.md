# Examples

The repository ships two ready-made datasets in `examples/`, one small and one
large, to walk through the four tabs end to end without having to assemble
your own data.

!!! note "The examples are not inside the plugin"
    `examples/` is marked `export-ignore` in `.gitattributes` — that is, it is
    **left out of the zip installed in QGIS** and only exists in the
    repository. Download the files through the links below (or clone the
    repo).

| Dataset | OD matrix (CSV) | Traffic zones (GPKG) | Zones | Matrix format |
|---|---|---|---|---|
| **MG micro-regions** | [`OD-MG_EXPORT.csv`](https://github.com/d-camargo/desire_lines/raw/main/examples/Microrregioes_MG/OD-MG_EXPORT.csv) | [`MICRO-MG.gpkg`](https://github.com/d-camargo/desire_lines/raw/main/examples/Microrregioes_MG/MICRO-MG.gpkg) | 66 | long (one row per pair) |
| **RMSP** | [`Tab24_OD2017.csv`](https://github.com/d-camargo/desire_lines/raw/main/examples/RMSP/Tab24_OD2017.csv) | [`zonas_2017_region_reproj_geometrias_corrigidas.gpkg`](https://github.com/d-camargo/desire_lines/raw/main/examples/RMSP/zonas_2017_region_reproj_geometrias_corrigidas.gpkg) | 517 | wide |

Start with the **MG** one: there are 66 zones, the matrix is already in long
format and everything runs in seconds. The **RMSP** one is the realistic case —
wide matrix, 517 zones and 267 thousand pairs after conversion.

## Example 1 — MG micro-regions

**General cargo** matrix between the 66 micro-regions of Minas Gerais, with
optimistic/medium/pessimistic scenarios for 2015, 2020, 2025, 2030 and 2035.

### Tab 1 — OD Matrix

1. *Read CSV* on `OD-MG_EXPORT.csv`, with the **format** checkbox
   **unchecked** — the file is already in long format, one row per pair
   (4,356 = 66 × 66). The file is in **windows-1252**, exactly the encoding
   the plugin assumes, so the accents in the names ("AIMORÉS") come out
   correctly.
2. *Read Vector* on `MICRO-MG.gpkg` (layer `traffic_zones`, 66 polygons,
   geographic **EPSG:4674 / SIRGAS 2000**).
3. Set the **Output GeoPackage** and click *Add Centroids to Traffic Zones*.

The columns of the matrix are:

| Column | Role |
|---|---|
| `Origem` | origin zone id (integer, 154 to 219) |
| `Origem_Descr` | name of the origin micro-region (descriptive only) |
| `Destino` / `Destino_Descr` | same, for the destination |
| `Carga_Geral_<year>_<scenario>` | 15 value columns — choose **one** as the value field (e.g. `Carga_Geral_2015_Medio`) |

The id field in the zones is **`Origem`** — same name and same numbering as the
origin column of the matrix, so it is the one that goes into the *Traffic ID*
combos.

### Tabs 2 and 3 — desire lines and AoN

Fill in the two layer combos with `matrix` and `centroids` and the fields as
follows:

| Combo | Value |
|---|---|
| *Origin* | `Origem` (from the matrix) |
| *Destination* | `Destino` |
| *Value* | `Carga_Geral_2015_Medio` (or another scenario) |
| *Traffic ID* | `Origem` (from the centroids) |

**What to expect:**

- **Desire lines:** **4,290 features** — the 4,356 pairs minus the 66
  intrazonal ones (`Origem = Destino`), which the plugin discards and which in
  this matrix are precisely the zero-value ones.
- **AoN (Delaunay):** the centroids are geographic and MG extends from UTM
  zone 22 to 24, so the plugin falls back to the **SIRGAS 2000 / Brazil Albers
  (EPSG:10857)** rule and says so in the final message. The `aon_flows` layer
  comes out in that CRS — not in the EPSG:4674 of the input.

### Tab 4 — highway assignment

This is the appropriate example for tab 4: **interurban** demand over a rural
network, which is the scope of the implemented HCM procedure. Use *Download via
GisBR* with **UF = `MG`** and *Clip to the centroid extent* checked (with the
[GisBR](https://github.com/d-camargo/gisbr) plugin installed), or point to
your own highway layer.

!!! warning "The unit of the cargo column is not veh/h"
    The `Carga_Geral_*` columns are **cargo**, not vehicles per hour — and HCM
    capacity is in **vehicles per hour per direction**. Assigning the raw
    column produces a v/c with no physical meaning. Convert first (cargo →
    equivalent vehicles → design hour) or read the result only as a **relative
    distribution** of flow over the network, not as v/c. See
    [Highway Assignment](alocacao-rodovias.md).

## Example 2 — RMSP (wide matrix)

Trip matrix between the 517 OD zones of the São Paulo Metropolitan Region
(2017 OD Survey), in **square table** format: the first column is called `OD`
and there is one column per destination zone, from `1` to `517`.

### Tab 1 — OD Matrix

1. *Read CSV* on `Tab24_OD2017.csv` with the **format** checkbox **checked** —
   this is the *wide* case. The plugin runs `pandas.melt` and writes a
   `matrix_long.csv` next to the original, with the columns **`Origem`**,
   **`Destino`** and **`Passageiros`** and **267,289 rows** (517 × 517).
   Without `pandas` in QGIS's Python the conversion does not happen — see
   [OD Matrix](matriz-od.md).
2. *Read Vector* on `zonas_2017_region_reproj_geometrias_corrigidas.gpkg`: 517
   polygons in **EPSG:31983 (SIRGAS 2000 / UTM 23S)**, already metric.

Zone fields: `NumeroZona`, `NomeZona`, `NumeroMuni`, `NomeMunici`,
`NumDistrit`, `NomeDistri`, `Area_ha_2` and **`IDTRAF`**. Use **`IDTRAF`** as
the *Traffic ID* — it is identical to `NumeroZona` in all 517 zones and matches
the 1–517 numbering of the matrix.

!!! danger "The dot in this CSV is a thousands separator"
    3,152 cells hold values such as `1.016`, `1.489`, `2.919` — always with
    three digits after the dot. These are **1,016 trips**, not 1.016. Read as
    a number, `1.016` becomes **1.016**, and precisely the largest flows of the
    matrix shrink to fewer than 3 trips. **Before importing**, remove those
    dots in the file (find-and-replace `.` with nothing, in a text editor). If
    the thickest desire lines on the map look like the wrong pairs, this is
    why.

### Tabs 2 and 3

| Combo | Value |
|---|---|
| *Origin* | `Origem` |
| *Destination* | `Destino` |
| *Value* | `Passageiros` |
| *Traffic ID* | `IDTRAF` |

**What to expect:**

- **Desire lines:** **266,772 features** — all pairs minus the 517 intrazonal
  ones. Most have a zero value: only **26,386** non-intrazonal pairs have
  trips. It is worth filtering the layer (`"Passageiros" > 0`, or a much
  higher threshold) before trying to read the map; the whole matrix drawn
  becomes a black block.
- **AoN (Delaunay):** the centroids are already in a metric CRS, so the plugin
  **uses EPSG:31983 as is** — no reprojection, unlike the MG example. There
  are 517 centroids, well above the minimum of 3.

### Tab 4 — why not with this dataset

The RMSP is an **urban area**, and the highway tab was built for
rural/interurban highways: urban crossing segments come out flagged with
`escopo='urbano'`, counted in the final message and **not** recomputed with an
urban procedure. In addition, the `Passageiros` column holds daily person
trips, not vehicles per hour. Use this dataset in tabs 1 to 3, and the MG one
in tab 4.

## If something does not add up

- No pair matched → *Origin*, *Destination* and *Traffic ID* are in different
  id schemes (`Origem` in MG, `IDTRAF` in the RMSP).
- Large flows showing up small in the RMSP → the thousands separator, above.
- More details in [Troubleshooting](../solucao-de-problemas.md),
  [Input formats](../referencia/formatos-de-entrada.md) and
  [Output fields](../referencia/campos-de-saida.md).
