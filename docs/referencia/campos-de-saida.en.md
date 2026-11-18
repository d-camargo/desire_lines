# Output fields

This page presents the complete technical specification of the attribute fields generated in each of the **Desire Lines** plugin's output vector layers.

---

## 1. Desire Lines Layer (Tab 2)

The **Desire Lines** layer is generated from a join (*JOIN*) between the OD matrix and the traffic zone centroids. Each feature represents a straight vector (line) connecting the origin zone centroid to the destination zone centroid for every OD pair with a flow greater than zero (self-pairs, where origin equals destination, are discarded).

* **Default layer / table name:** `Desire_Lines` (saved in the output GeoPackage or as an in-memory vector layer).
* **Geometry type:** Line (`LineString`).

| Field | Type | Unit | Description |
|---|---|---|---|
| `<campo_origem>` | Text or Integer | - | Identifier of the origin zone of the OD pair (inherited from the field selected in the matrix CSV). |
| `<campo_destino>` | Text or Integer | - | Identifier of the destination zone of the OD pair (inherited from the field selected in the matrix CSV). |
| `<campo_fluxo>` | Decimal (`Double`) | Demand (passengers, veh, etc.) | Demand/trip volume associated with the OD pair. |
| `geometry` | Line (`LineString`) | - | Geometry of the straight line connecting origin to destination. |

!!! note "Layer column names"
    The actual names of the `<campo_origem>`, `<campo_destino>` and `<campo_fluxo>` columns correspond to the names of the fields selected in the *comboboxes* of Tab 2 (e.g. `Origem`, `Destino`, `Passageiros`).

---

## 2. Synthetic AoN Delaunay Assignment Layer (Tab 3)

The **Synthetic AoN Assignment on a Delaunay network** layer contains the line segments resulting from the Delaunay triangulation between the centroids, accumulating the trip flow assigned along the shortest paths (Dijkstra) between all OD pairs.

* **Default layer name:** `aon_flows`
* **Geometry type:** Line (`LineString`)
* **Responsible module:** `aon.py` (`edge_flows_to_layer`)

| Field | Type | Unit | Description |
|---|---|---|---|
| `flow` | Decimal (`Double`) | Demand (veh/h or flow units) | Total traffic volume assigned to the Delaunay network segment. Equals the sum of the flows in both directions of the segment (`flow = flow_ab + flow_ba`). |
| `flow_ab` | Decimal (`Double`) | Demand | Volume assigned in the A -> B direction (from the first to the second vertex of the feature). Generated when the **Split by direction** option is enabled. |
| `flow_ba` | Decimal (`Double`) | Demand | Volume assigned in the B -> A direction (from the second to the first vertex of the feature). Generated when the **Split by direction** option is enabled. |

---

## 3. HCM Capacity Layer (Tab 4 — Pre-assignment)

Generated when you run the **Compute capacity** command on the plugin's fourth tab. It contains the processed and simplified road network with capacities computed according to the HCM 6th Edition procedures (Chapters 12 and 15), before any demand is assigned to it.

* **Default layer name:** `capacidade_hcm`
* **Geometry type:** Line (`LineString`)
* **Responsible module:** `traffic/outputs.py` (`flows_to_layer`)

It has exactly the same fields as described in the section below (Assignment on Real Highways), but with the following pre-assignment default values:

* `volume = 0.0`
* `vc = 0.0`
* `los = 'A'`
* `tempo_h = free-flow time (t0)`
* `atraso_h = 0.0`
* `metodo = 'capacidade'`

---

## 4. Assignment on Real Highways Layer (Tab 4 — AoN / MSA / FW)

Generated after running the assignment of the OD matrix demand onto the real highway network (SNV/DER) with the **Assign** command.

* **Default layer name:** `alocacao_aon` (for All-or-Nothing), `alocacao_msa` (for MSA equilibrium) or `alocacao_fw` (for Frank-Wolfe equilibrium).
* **Geometry type:** Line (`LineString`)
* **Responsible module:** `traffic/outputs.py` (`flows_to_layer`)

### Main Traffic and Performance Attributes

| Field | Type | Unit | Description |
|---|---|---|---|
| `arc_id` | Text (`String`) | - | Unique identifier of the directed arc in the graph (e.g. `('link101', 'fw')` or `('link101', 'bw')`). |
| `link_id` | Integer (`Integer64`) or Text (`String`) | - | Identifier of the original segment/link of the input road network (e.g. SNV/DER segment code). It is **Integer (`Integer64`)** when the source id is numeric (the default, the feature FID) and Text (`String`) when the *Link id field* has non-numeric values. |
| `sentido` | Text (`String`) | - | Travel direction of the arc: `fw` (*forward* — same as the geometry orientation) or `bw` (*backward* — opposite to the geometry). |
| `faixas` | Integer (`Int`) | lanes | Number of travel lanes available per direction on the segment. |
| `comp_m` | Decimal (`Double`) | m | Actual length of the road segment in metres. |
| `vel_livre` | Decimal (`Double`) | km/h | Free-flow speed (FFS) used in the calculation. |
| `capacidade` | Decimal (`Double`) | veh/h | Maximum theoretical per-direction capacity computed according to the HCM 6th Edition. |
| `volume` | Decimal (`Double`) | veh/h | Total traffic volume assigned to the arc after the assignment model is solved. |
| `vc` | Decimal (`Double`) | dimensionless | Volume/capacity ratio of the arc (`v/c = volume / capacidade`). |
| `los` | Text (`String`) | - | Operational Level of Service of the segment, from `A` to `F`, derived from the `v/c` indicator. |
| `tempo_h` | Decimal (`Double`) | h | Total travel time on the segment under the assigned flow, determined by the BPR performance function (`t = t0 * [1 + alfa * (v/c) ^ beta]`). |
| `atraso_h` | Decimal (`Double`) | h | Per-segment delay caused by congestion relative to free-flow time (`tempo_h - t0`). |
| `metodo` | Text (`String`) | - | Assignment algorithm used: `aon` (*All-or-Nothing*), `msa` (*Method of Successive Averages equilibrium*) or `fw` (*Frank-Wolfe equilibrium*). |
| `escopo` | Text (`String`) | - | Territorial scope classification: `rodoviario` (rural/intercity highway with HCM capacity) or `urbano` (urban crossing kept in the network without capacity recalculation). |

---

### HCM Parameter Provenance Fields (`src_*`)

To meet the principle of full data transparency (**Rule D7 — "Nothing is assumed silently"**), the output layer includes 18 additional fields indicating the exact provenance of each operational and capacity parameter used in the calculation.

The `src_*` fields can take one of three possible values:

* **`oficial`**: The parameter was read directly from an attribute that exists in the input highway layer (through field mapping in the UI or a candidate-name lookup).
* **`usuario`**: The parameter was entered or overridden manually by the user in the plugin interface.
* **`padrao`**: The parameter was not in the input layer and the plugin applied the default value aligned with DNIT/HCM guidelines.

| Provenance field | Associated parameter | Description |
|---|---|---|
| `src_tipo_segmento` | `tipo_segmento` | Provenance of the segment type (`2_faixas`, `multipista`, `freeway`). |
| `src_lanes` | `lanes` | Provenance of the number of lanes per direction. |
| `src_pavimentado` | `pavimentado` | Provenance of the paved-surface indicator. |
| `src_urbano` | `urbano` | Provenance of the urban-crossing flag. |
| `src_largura_faixa` | `largura_faixa` | Provenance of the lane width (m). |
| `src_largura_acostamento` | `largura_acostamento` | Provenance of the shoulder width (m). |
| `src_terreno` | `terreno` | Provenance of the terrain type (flat, rolling, mountainous). |
| `src_pct_veic_pesados` | `pct_veic_pesados` | Provenance of the percentage of heavy vehicles (trucks and buses). |
| `src_vel_livre` | `vel_livre` | Provenance of the free-flow speed (km/h). |
| `src_phf` | `phf` | Provenance of the Peak Hour Factor. |
| `src_pct_no_passing` | `pct_no_passing` | Provenance of the percentage of the segment with a passing prohibition. |
| `src_access_density` | `access_density` | Provenance of the access density per kilometre (accesses/km). |
| `src_directional_split` | `directional_split` | Provenance of the directional distribution of traffic (e.g. 50/50, 60/40). |
| `src_bpr_alpha` | `bpr_alpha` | Provenance of the `alfa` parameter of the BPR impedance equation. |
| `src_bpr_beta` | `bpr_beta` | Provenance of the `beta` parameter of the BPR impedance equation. |
| `src_capacidade` | `capacidade` | Provenance of the per-direction capacity supplied (`oficial`, `usuario` or `padrao`). |
| `src_tempo_livre` | `tempo_livre` | Provenance of the free-flow time supplied (`oficial`, `usuario` or `padrao`). |
| `src_mao_unica` | `mao_unica` | Provenance of the one-way flag (`oficial`, `usuario` or `padrao`). |

---

## 5. v/c Graduated Symbology and Style

The highway assignment output layers (`alocacao_aon`, `alocacao_msa` and `alocacao_fw`) are automatically configured with a native QGIS graduated symbology renderer (`QgsGraduatedSymbolRenderer`) applied to the **`vc`** field.

The style uses an intuitive 6-class colour scale (from dark green to purple) accompanied by increasing line width:

| Level of Service | `v/c` range | Hex colour | Width (mm) | Operating condition |
|:---:|:---:|:---:|:---:|---|
| **LOS A** | `v/c <= 0.35` | `#1a9641` | 0.6 mm | **Free flow:** Excellent condition, no restriction on manoeuvring. |
| **LOS B** | `0.35 < v/c <= 0.55` | `#a6d96a` | 0.8 mm | **Stable flow:** Slight increase in density, speeds maintained. |
| **LOS C** | `0.55 < v/c <= 0.75` | `#ffffbf` | 1.0 mm | **Restricted flow:** Reduced freedom to manoeuvre, speed influenced by traffic. |
| **LOS D** | `0.75 < v/c <= 0.90` | `#fdae61` | 1.2 mm | **Approaching unstable flow:** High density, small disturbances cause delays. |
| **LOS E** | `0.90 < v/c <= 1.00` | `#d7191c` | 1.5 mm | **Capacity:** Operation at the operational limit, highly unstable flow. |
| **LOS F** | `v/c > 1.00` | `#7b3294` | 2.0 mm | **Oversaturation:** Demand exceeds theoretical capacity; queues and congestion form. |

!!! warning "LOS as an operational approximation"
    The Level of Service assigned in the `los` field and in the automatic symbology is an **approximation derived from the `v/c` indicator**. The official HCM 6th Edition procedure defines LOS through specific performance measures: *Percent Time-Spent-Following (PTSF)* and *Average Travel Speed (ATS)* for two-lane highways (Chapter 15), or vehicle density per kilometre per lane for multilane highways and freeways (Chapter 12).
