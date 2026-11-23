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
you navigate the map or edit layers. It is divided into two inner tabs:
**Assignment** and **HCM parameters**.

!!! danger "Scope: rural/interurban highways"
    Capacity comes from **HCM ch. 15** (two-lane highways) and **ch. 12**
    (multilane highways / freeways). Urban crossings within the network are
    **flagged** with `escopo='urbano'` and counted in the final message, but
    are **not** recomputed with an urban procedure — the HCM urban procedure
    (chs. 16-19) requires signal data that the official dataset does not
    provide. Read those arcs with caution.

## Assignment tab

The **Assignment** tab gathers the network, matrix and assignment settings, as
well as the selection of the output file.

### The network: existing layer or download via GisBR

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
for capacity calculation and assignment.

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

### The assignment

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

#### Method: AoN, MSA Equilibrium or Frank-Wolfe Equilibrium

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

### Output GeoPackage and action buttons

Below the assignment group, the *Output GeoPackage* field defines the `.gpkg`
file where the generated layers will be written. If left blank, the plugin
uses the default path `~/output.gpkg`.

At the end of the *Assignment* tab, two buttons trigger the processing:

* **Compute capacity**: runs **only** the HCM part: builds the arcs from the
  network, resolves the parameters and publishes the **`capacidade_hcm`**
  layer, with `volume = 0`. It serves to check capacity and provenance
  **before** spending time on the assignment — and it needs neither a matrix
  nor centroids, only the network. Arcs whose capacity comes out **zero or
  invalid** are dropped.
* **Assign**: runs the full process of graph construction, OD matrix reading
  and traffic assignment, publishing the **`alocacao_fw`**, **`alocacao_msa`**
  or **`alocacao_aon`** layer (depending on the chosen method).

## HCM parameters tab

The **HCM parameters** tab contains the *HCM parameters (default, or override
globally / by field)* group, which gathers the operational and geometric
settings for the HCM capacity computation and network parameters.

Nothing is assumed silently: the tab has one row per parameter for the 18
parameters of the system (segment type, lanes, terrain, % heavy vehicles, FFS,
PHF, lane and shoulder width, no-passing zones, access density, directional
split, BPR alpha and beta, given capacity, free-flow time and one-way).

Each row offers **two inputs**: a global value typed into the control and a
*field:* combobox to map any column of the highway layer.

### Special network parameters and the `0` sentinel

Three parameters make it possible to directly incorporate known attributes of
already calibrated networks (such as municipal networks or benchmarks like
Sioux Falls):

* **Capacity per direction (0 = HCM)** (`capacidade`): Capacity per direction in veh/h. The **`0`** sentinel means automatic computation by the HCM 6th edition procedure (Ch. 15 two-lane highway or Ch. 12 multilane/freeway). Any value **`> 0`** overrides the HCM capacity.
* **Free-flow time (0 = length ÷ FFS)** (`tempo_livre`): Free-flow time in minutes. The **`0`** sentinel computes the time from the geometric length and the free-flow speed (`comprimento ÷ vel_livre`). Any value **`> 0`** overrides the computed time.
* **One-way (direction of the geometry)** (`mao_unica`): Boolean. If true (`True`, `1`, `'sim'`, `'yes'`), generates only the arc in the direction of the geometry (`fw`), omitting the reverse (`bw`). If false (`False`), generates both directed arcs (`fw` and `bw`).

### Precedence and field mapping (Decision D2)

When you select a column in the *field:* combo of any parameter, that mapping
is passed straight to the resolution (`field_map`). The value found in the
mapped column is adopted with **`oficial`** provenance.

The strict order of precedence per feature and per parameter is:

| Precedence | Source | Recorded as |
|---|---|---|
| 1st | Global value typed in the tab (if different from the 0 sentinel for capacity/free-flow time) | `usuario` |
| 2nd | Column of the selected layer in that row's *field:* combo | `oficial` |
| 3rd | Columns with standard candidate names present in the feature | `oficial` |
| 4th | Default from the plugin's factory catalogue | `padrao` |

!!! note "Provenance goes to the output layer"
    Each arc carries a `src_<parameter>` field with `oficial`, `usuario` or
    `padrao`, and the final message summarises how many (arc, parameter) pairs
    came from each source. It is what separates "capacity computed with the
    dataset's data" from "capacity computed with the factory default" — see
    [HCM parameters](../referencia/parametros-hcm.md).

## The result

The layer is written to the output GeoPackage set in the *Output GeoPackage*
field, named according to the method —
**`alocacao_fw`**, **`alocacao_msa`** or **`alocacao_aon`** (and `capacidade_hcm` via the **Compute capacity** button) — and is styled by **`vc`** in fixed classes from A to F (green up to
0.35; thick purple above 1.00). Main fields:

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
| `src_*` | Provenance of each parameter (including `src_capacidade`, `src_tempo_livre`, `src_mao_unica`): `oficial`, `usuario` or `padrao` |

The success message at the end is where the losses appear: pairs assigned,
number of arcs, provenance summary, count of urban arcs, gap, matrix rows with
unknown ids and **unreachable** pairs (disconnected network). It is worth
reading — see [Output fields](../referencia/campos-de-saida.md) and
[Troubleshooting](../solucao-de-problemas.md).

!!! warning "The ids must use the same scheme"
    If *Origin*, *Destination* and *Traffic id* do not use the same coding, no
    pair matches and the assignment aborts with a warning. Same trap as in the
    [OD Matrix](matriz-od.md).

**Next step:** [Examples](exemplos.md).
