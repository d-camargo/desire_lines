# Highway Assignment

The **Highway Assignment** panel loads the OD matrix onto the **actual road
network** (SNV/DER), computes the **capacity of each segment using the HCM 6th
edition procedure** and returns volume, volume/capacity ratio (`vc`) and level
of service per arc. It is the result that the synthetic network of the
[AoN (Delaunay)](aon-delaunay.md) tab cannot give — there is no capacity
there.

To open the panel, use the **single toolbar button with a menu arrow** (a click
opens the main dialog; the arrow opens the menu with *Desire Lines* and
*Highway Assignment*) or go to the menu **Vector ▸ Desire Lines ▸ Highway Assignment**.
The panel docks on the right side of the QGIS window and can stay open while
you navigate the map or edit layers.

Just above the tabs, the **Output GeoPackage** field defines the shared `.gpkg`
file where all generated layers are stored (by default `~/output.gpkg`).
Below it, the panel is divided into four operational tabs:
**Network**, **Capacity**, **Assignment**, and **Calibration**.

!!! danger "Scope: rural/interurban highways"
    Capacity comes from **HCM ch. 15** (two-lane highways) and **ch. 12**
    (multilane highways / freeways). Urban crossings within the network are
    **flagged** with `escopo='urbano'` and counted in the final message, but
    are **not** recomputed with an urban procedure — the HCM urban procedure
    (chs. 16-19) requires signal data that the official dataset does not
    provide. Read those arcs with caution.

## Network tab

The **Network** tab defines the working road network used for both capacity
computation and traffic assignment.

The *Network* group has two mutually exclusive options:

| Option | What to fill in | When to use |
|---|---|---|
| *Use an existing layer* | *Highway layer* and, optionally, *Link id field (optional)* | You already have the network loaded in the project (local file, your own clip) |
| *Download via GisBR (official SNV/DER network)* | *State (UF)* (**2-letter** code), *Download area*, if regional, *Region*, and the *Download network* button | You want the official network downloaded on the spot; the runs use the downloaded layer |

The *Link id field (optional)* is optional: it makes the `link_id` field of the
output point back to the identifier of your own dataset. Without it, the
plugin generates its own id.

!!! warning "The download depends on the GisBR plugin"
    The download option is only enabled if the
    [GisBR](https://github.com/d-camargo/gisbr) plugin is installed — without
    it, the warning at the top of the panel is visible and the plugin switches
    back to *Use an existing layer* on its own. The rest of the panel **works
    normally** with your own layer; only the download is blocked.

The *Download area* combo defines the territorial coverage of the network to
be downloaded and clipped, with six options available:

1. **Centroid extent (+ radius)**: the study area is the rectangular envelope
   of the loaded centroids plus the radius configured in *Max connector (m)*.
   This is the default and recommended option, to focus the graph only on the
   surroundings of the demand.
2. **Whole state**: downloads the complete network of the state given in
   *State (UF)*.
3. **Metropolitan area**: clips the network to the extent of the selected
   Metropolitan Region.
4. **Micro-region**: clips the network to the extent of the selected
   geographic micro-region (IBGE).
5. **Meso-region**: clips the network to the extent of the selected geographic
   meso-region (IBGE).
6. **Health macro-region**: clips the network to the extent of the selected
   health macro-region.

The four regional options (*Metropolitan area*, *Micro-region*, *Meso-region*
and *Health macro-region*) require the *UF* (2 letters), which makes the
plugin dynamically load the regions available for that state, and the mandatory
choice of an item in the *Region* combo. Until a valid region is selected, the
download button remains disabled.

Downloading is triggered by the **Download network** button. When you enter the
*State (UF)*, the plugin populates the **Sources** list with all official road
databases available for that state in the GisBR catalogue — the DNIT federal
network (SNV) and registered state databases (DERs) —, all checked by default.
You can uncheck any source before starting the download. If downloading any
checked source fails (for instance, due to server unavailability), the process
**aborts immediately** with an error message naming the failed source, avoiding
incomplete network layers.

The download runs in the **background**: progress and cancellation are handled
by the **QGIS task manager** (bottom corner), and QGIS remains usable
throughout the process.

Regarding network clipping:

- In **Whole state** mode and regional extents (*Metropolitan area*,
  *Micro-region*, *Meso-region*, and *Health macro-region*), the network is
  clipped by the **official boundary** (IBGE, via GisBR), with a 500 m buffer
  at the border.
- In **Centroid extent (+ radius)** mode, clipping follows the bounding box of
  the centroids plus the maximum distance (*Max connector (m)*).

When more than one source is checked, the plugin performs a **geometric merge
with precedence**:

- **Precedence DNIT → state DERs**: the federal DNIT network is the primary
  reference and is included in full; subsequent state networks only contribute
  segments that do not duplicate roads already present.
- **Overlap handling**: state segments overlapping the reference network for
  **≥ 100 m within a 20 m tolerance buffer** are trimmed (subtracted). Short
  touches at junctions (< 100 m) are preserved to keep junction connectivity,
  and residual slivers shorter than 50 m are discarded. Planned segments from
  any source are filtered out beforehand.
- **Topological stitching (30 m)**: dangling ends within **30 m** of another
  road are snapped to the closest node (node-to-node) or orthogonally projected,
  splitting the intersected link at a T-junction. Grade-separated crossings
  (such as overpasses and underpasses) without nearby dangling ends are **not**
  connected, preserving the absence of real turning movements.

Each feature in the resulting network receives the traceability attributes
**`fonte`** (source identifier, e.g. `dnit_snv` or `der_mg_rodovias`) and
**`ajuste`** (empty for untouched segments, `'aparada'` for trimmed overlaps,
`'costurada'` for stitched ends, or `'aparada+costurada'`). The remaining source
fields are unified. The final network is saved in the output GeoPackage as the
**`malha_gisbr_<uf>`** layer (for example, `malha_gisbr_mg`), loaded directly into
the QGIS project and automatically selected in *Use an existing layer*, ready
for capacity calculation and assignment. The final message in the message bar
separates segments **removed as duplicates**, **trimmed**, and **stitched**
(with a per-source report in the Message Log).

When the *Use an existing layer* option is used, the study area is also
clipped to the extent of the centroids (with a connector buffer), limiting the
size of the network and speeding up graph construction. If the clip fails, the
plugin shows a warning and proceeds with the full network.

!!! note "Automatic reprojection to a metric CRS"
    Layers in a geographic CRS (degrees) — whether from the GisBR download or
    an existing layer — are reprojected automatically to a metric CRS (the
    region's UTM, or SIRGAS 2000 / Brazil Albers if the area covers more than
    one zone). The output layer comes out in that CRS, and the warning
    *Highway network reprojected…* appears in the message bar.

## Capacity tab

The **Capacity** tab gathers the operational and geometric settings for the
HCM capacity computation and network parameters.

The *HCM parameters (default, or override globally / by field)* group presents the parameter table for the 18 operational parameters of the system (segment type, lanes, terrain, % heavy vehicles, FFS, PHF, lane and shoulder width, no-passing zones, access density, directional split, BPR alpha and beta, given capacity, free-flow time, and one-way).

Each row in the table provides four columns:

| Column | Description |
|---|---|
| **Parameter** | Name of the operational or geometric HCM parameter. |
| **Value where there is no data** | Value used when neither the road feature nor the complementary layer provide data (step 6 of the cascade). If modified by the user from catalogue defaults, it is recorded with **`usuario`** provenance. |
| **Fix** | Checkbox (`QCheckBox`) that, when ticked (with no layer field mapped), forces the entered value across the entire road network (step 1 of the cascade). This value takes precedence over layer attributes and complementary layers, recorded with **`usuario`** provenance. |
| **Layer field** | Combobox allowing you to map any column from the road layer directly to the parameter (step 2 of the cascade). Values successfully read receive **`oficial`** provenance. |

When you use the *Download via GisBR (official SNV/DER network)* option on the Network tab, the downloaded network (`malha_gisbr_<uf>`) already arrives standardized with the 21-column schema in technical HCM vocabulary (Decisions D2 and D3). As a result, the plugin automatically recognizes and reads official attributes directly from the layer without requiring any manual field mapping.

### Complementary data (optional) group

Located directly below the parameter table, the **Complementary data (optional)** group allows enriching the road network with data from secondary sources (Decisions D4 and D6):

* **Complementary layer**: Combobox accepting any additional vector layer loaded in the QGIS project (lines such as OSM centerlines or `osm_links_rm<id>`, points such as count stations with heavy vehicle %, or polygons such as IBGE urbanized areas). Leave empty if you only want to work with data from the road network.
* **Max. distance**: Search radius in metres (default **30 m**). The plugin evaluates the geometric midpoint of each road link and finds the nearest complementary feature within the configured distance (measured in the metric CRS of the network).

Attributes from the matched feature undergo automatic translation (`oficiais.traduz`) and candidate lookup, and the inherited parameters receive **`complementar`** provenance (step 5 of the resolution cascade).

### Special network parameters and the `0` sentinel

Three parameters make it possible to directly incorporate known attributes of
already calibrated networks (such as municipal networks or benchmarks like
Sioux Falls):

* **Capacity per direction (0 = HCM)** (`capacidade`): Capacity per direction in veh/h. The **`0`** sentinel means automatic computation by the HCM 6th edition procedure (Ch. 15 two-lane highway or Ch. 12 multilane/freeway). Any value **`> 0`** overrides the HCM capacity.
* **Free-flow time (0 = length ÷ FFS)** (`tempo_livre`): Free-flow time in minutes. The **`0`** sentinel computes the time from the geometric length and the free-flow speed (`comprimento ÷ vel_livre`). Any value **`> 0`** overrides the computed time.
* **One-way (direction of the geometry)** (`mao_unica`): Boolean. If true (`True`, `1`, `'sim'`, `'yes'`), generates only the arc in the direction of the geometry (`fw`), omitting the reverse (`bw`). If false (`False`), generates both directed arcs (`fw` and `bw`).

### Precedence and Resolution Cascade (Decisions D4 and D7)

Parameter resolution occurs in two passes through a strict 8-step cascade implemented in `params.resolve()`. The first step that supplies a valid value wins:

| Precedence | Source | Recorded as |
|---|---|---|
| 1st | Parameter fixed in the UI by ticking **Fix** (without a layer field mapped) | `usuario` |
| 2nd | Column of the road layer selected in the **Layer field** column | `oficial` |
| 3rd | Automatic translation of attributes from recognized official sources (`oficiais.traduz`) | `oficial` |
| 4th | Standard candidate column names present on the feature (including the standardized network schema) | `oficial` |
| 5th | Nearest feature from the **Complementary layer** within the configured maximum distance | `complementar` |
| 6th | Value entered in the **Value where there is no data** column | `usuario` |
| 7th | Default by road class (`PADRAO_POR_CLASSE`: multilane, two-lane paved, or unpaved) | `padrao` |
| 8th | Residual factory default from the plugin's catalogue (`PARAMS`) | `padrao` |

!!! note "Provenance goes to the output layer"
    Each arc carries a `src_<parameter>` field with `oficial`, `complementar`, `usuario` or
    `padrao`, and the final message summarises how many (arc, parameter) pairs
    came from each source. It is what separates "capacity computed with the
    dataset's data" from "capacity computed with the factory default" — see
    [HCM parameters](../referencia/parametros-hcm.md).

### Compute capacity button

The **Compute capacity** button, located at the bottom of the tab, runs **only**
the HCM procedure: it builds the arcs from the highway network, resolves the operational
parameters, and writes the **`capacidade_hcm`** layer (with `volume = 0`) to the shared
output GeoPackage. It serves to check capacity and provenance **before** spending time
on the assignment — needing neither an OD matrix nor centroids, only the network.
Arcs whose resulting capacity comes out **zero or invalid** are dropped.

## Assignment tab

The **Assignment** tab configures the demand and runs the traffic assignment onto the highway network.

The *Assignment* group asks for the matrix and the centroids:

| Field | What to choose |
|---|---|
| *OD matrix* | Matrix layer — the combo lists layers **without geometry** |
| *Origin* / *Destination* | Zone id columns in the matrix |
| *Demand (veh/h)* | Numeric demand column — the unit matters here: HCM capacity is in **vehicles per hour per direction** |
| *Centroids* | Centroids layer |
| *Traffic id* | Field of the centroids with the same id used in Origin/Destination |
| *Max connector (m)* | Maximum accepted distance between a centroid and the road network (`max_dist_m`, default 5000 m) |

Each centroid is linked to the network by a two-way **connector** (connectors
tie the centroid to the network for the computation but **do not appear** in
the output layer), with high capacity and negligible cost — it exists only to
inject demand into the network and does not represent any road. The anchor is
the nearest point **on the link** (the link is split there). A centroid whose
distance to the network exceeds *Max connector (m)* is left **out** of the
assignment, and the plugin tells you how many.

### Method: AoN, MSA Equilibrium or Frank-Wolfe Equilibrium

The *Method* field defines the loading algorithm:

| Method | How it loads | When to use |
|---|---|---|
| *All-or-Nothing (no capacity restraint)* | A single pass along the shortest path at **free-flow** time; all the flow of the pair takes that path | Overload diagnosis: where demand exceeds capacity if nobody diverts |
| *Equilibrium MSA + BPR* | Iterative: the time of each arc grows with its loading (**BPR** function, `t = t0 · (1 + α·(v/c)^β)`) and demand is redistributed by the **method of successive averages** (fixed step $1/k$) | Equilibrium estimate for teaching purposes or comparison with classical methods |
| *Equilibrium Frank-Wolfe + BPR* | Iterative with optimal step: at each iteration it evaluates the Beckmann function and computes the optimal step size $\lambda$ by **bisection line search** | **Recommended default**: Wardrop user equilibrium with fast convergence to tight gaps |

*Iterations* (default **100**, configurable up to 5000) and *Gap tolerance*
(default **0.001**) apply to the equilibrium methods (**Frank-Wolfe** and
**MSA**) — with All-or-Nothing selected, both fields are disabled. The
algorithm stops when the gap reaches the configured tolerance or when the
number of iterations is exhausted; the final message in the message bar
reports the gap reached and the number of iterations run.

The method selected by default is **Equilibrium Frank-Wolfe + BPR**, because
its convergence is substantially faster than that of MSA, reaching higher
precision in fewer iterations.

!!! warning "Under AoN, vc > 1 is not equilibrium — it is overload"
    In AoN capacity **never** feeds back into the cost, so nothing prevents an
    arc from receiving more trips than it can handle. The gap comes out as
    "n/a" on purpose. A `vc` above 1 there says *"demand exceeds capacity on
    this segment"*, not *"this is the equilibrium loading"*.

### Assign button

The **Assign** button, located at the bottom of the tab, runs the full process of
graph construction, centroid connection, OD matrix reading, and traffic assignment.
The result is written to the shared output GeoPackage as **`alocacao_fw`**,
**`alocacao_msa`**, or **`alocacao_aon`** (depending on the chosen method).

Upon successful completion, the plugin automatically populates and selects the
newly published layer in the *Assignment layer* field of the **Calibration tab**.

## Calibration tab

The **Calibration** tab compares model assignment flows against observed field
traffic counts (such as PNCT/DNIT monitoring stations), computing the **GEH** statistic
and evaluating macro-simulation fit against normative criteria.

### Calibration inputs

The *Calibration with traffic counts (GEH)* group provides the following settings:

| Field | What to fill in | Description |
|---|---|---|
| *Assignment layer* | Assignment line layer | Layer containing `link_id` and `volume` attributes. Automatically set to the layer generated upon clicking *Assign*. |
| *Count posts* | Point layer | Layer containing the spatial locations of traffic count posts. |
| *Count field* | Numeric field | Attribute column with observed traffic volume (e.g. AADT). |
| *Post id field (optional)* | Identifier field (optional) | Human-readable post identifier. If left empty, the feature `FID` is used. |
| *Max. snapping distance* | Distance in metres (default **200 m**) | Search radius for matching each post to the nearest assigned highway link. |
| *Model → count factor* | Numeric factor (default **1.0000**) | Scaling multiplier applied to assigned volume to match temporal and conceptual units. |

### Spatial post-to-link snapping

To evaluate post counts against assigned flows, the algorithm performs spatial snapping:

1. **Nearest link and both-direction sum**: The assignment layer contains one feature per directed arc (`fw` and `bw`), and segments divided to anchor centroids share the same `link_id`. Since highway traffic counts (such as PNCT AADT) are bidirectional, the plugin finds the nearest link to the post and **sums the volume of all features with the same `link_id` whose distance to the post is within 1 metre of the minimum distance**. This captures both travel directions (`fw` + `bw`) of the same physical segment (and naturally handles one-way roads as a single arc).
2. **Posts without a matching link (`sem_link`)**: If the distance to the nearest highway link exceeds the configured *Max. snapping distance* (default 200 m), the post is considered isolated. It is written to the output layer with `faixa = 'sem_link'` and null (`NULL`) GEH, and is **excluded** from the total count ($n$) evaluated in the DNIT criterion and %RMSE.
3. **Invalid count records**: Records with null, non-numeric, negative, or empty geometry values are excluded from the calculation and reported in the log.

### Model → count factor (Units)

Following the plugin rule that **nothing is assumed silently**, the user must explicitly provide the scaling factor between the matrix unit and the count unit:

* HCM capacity and the assignment matrix are typically expressed in **peak-hour vehicles** (veh/h).
* Highway counts (such as PNCT data series) are commonly published as **Annual Average Daily Traffic (AADT)**.
* If the peak hour represents a fraction $K = 0.10$ of daily traffic ($AADT \approx \text{Peak} / K$), the **Model → count factor** should be set to **$10.0$** ($1 / K$).
* The evaluated modeled volume is computed as $M = \text{assigned volume} \times \text{factor}$. The applied factor is recorded in the `fator` attribute of every output feature.

### Calibrate button and interpreting results

The **Calibrate** button at the bottom of the tab executes spatial snapping and GEH calculation, writing the **`calibracao_geh`** point layer to the shared output GeoPackage. The layer is loaded into QGIS and automatically styled with categorized symbols by GEH band:

* **Band A** ($GEH < 5$): green (`#2ca02c`) — excellent calibration;
* **Band B** ($5 \le GEH < 10$): yellow (`#ffff33`) — acceptable fit;
* **Band C** ($10 \le GEH < 12$): orange (`#ff7f00`) — moderate divergence;
* **Band D** ($GEH \ge 12$): red (`#d7191c`) — substantial divergence;
* **Without link** (`sem_link`): grey (`#808080`) — posts located beyond the maximum snapping distance.

Upon completion, the QGIS message bar displays the executive summary:
> `Calibration: N posts (k without a link within X m) — A p% · A+B q% · %RMSE r — DNIT criterion (≥60% A, ≥95% A+B): met (or not met) (factor f)`

The notification is shown in green (*success*) when the official DNIT criterion is met, and in yellow (*warning*) otherwise. In addition, the QGIS **Message Log** (*Desire Lines* tab) lists the 10 posts with the highest GEH values (post, count, modeled, GEH), highlighting priority locations for matrix or network refinements.

## The result

All layers are saved in the file configured in **Output GeoPackage**:
the assignment layers **`alocacao_fw`**, **`alocacao_msa`**, or **`alocacao_aon`**, the preliminary **`capacidade_hcm`** layer (generated via the *Compute capacity* button), and the **`calibracao_geh`** point layer (generated via the *Calibrate* button).

The arc layers are styled by **`vc`** in fixed classes from A to F (green up to
0.35; thick purple above 1.00). Main assignment fields:

| Field | Meaning |
|---|---|
| `arc_id` / `link_id` / `sentido` | Identification of the directed arc and of the source link (`fw`/`bw`) |
| `tipo` | Arc classification: `link` (original, intact) or `link_dividido` (split to anchor a centroid) |
| `faixas`, `comp_m`, `vel_livre` | Lanes per direction, length in metres, free-flow speed |
| `capacidade` | Capacity per direction in veh/h (HCM or given) |
| `volume` | Volume assigned to the arc |
| `vc` | `volume / capacidade` |
| `los` | **Approximate** level of service, derived from `vc` (the official HCM LOS uses density/average travel speed) |
| `tempo_h`, `atraso_h` | Travel time on the arc and delay over free flow |
| `metodo`, `escopo` | Method used (`fw`/`msa`/`aon`/`capacidade`) and `rodoviario` or `urbano` |
| `src_*` | Provenance of each parameter (including `src_capacidade`, `src_tempo_livre`, `src_mao_unica`): `oficial`, `complementar`, `usuario` or `padrao` |

The success message at the end of assignment summarizes pairs assigned,
number of arcs, provenance, count of urban arcs, gap, matrix rows with
unknown ids, and **unreachable** pairs (disconnected network) — see
[Output fields](../referencia/campos-de-saida.md) and
[Troubleshooting](../solucao-de-problemas.md).

!!! warning "The ids must use the same scheme"
    If *Origin*, *Destination* and *Traffic id* do not use the same coding, no
    pair matches and the assignment aborts with a warning. Same trap as in the
    [OD Matrix](matriz-od.md).

**Next step:** [Examples](exemplos.md).
