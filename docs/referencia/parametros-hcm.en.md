# HCM Parameters and the Provenance Rule

This page presents the complete technical reference for all the operational and geometric parameters used in highway capacity calculation under the **HCM 6th Edition** (Highway Capacity Manual) and in the traffic assignment of the **Desire Lines** plugin.

---

## 1. Parameter Provenance Rule (Decision D7)

To ensure transparency and technical auditability in transport planning studies, the plugin strictly adopts **Rule D7 — "Nothing is assumed silently"**.

No capacity parameter is applied to a highway without its origin being explicitly declared. For each parameter `X` used, the output layer records a matching `src_X` field whose provenance value indicates one of four possible origins:

1. **`usuario`**: The value was entered or overridden manually by the user in the plugin interface (parameter fixed via *Fix* or entered in *Value where there is no data*).
2. **`oficial`**: The value was read directly from an attribute that exists in the highway layer (e.g. official SNV/DNIT or DER data obtained through GISBR, or a mapped layer field).
3. **`complementar`**: The value was obtained from a matching feature in a **complementary layer** spatially associated by proximity (Decisions D4 and D6).
4. **`padrao`**: The parameter was not in the layer's attribute table nor in the complementary layer and was not entered in the interface; the plugin applied the documented default value (road-class default or factory catalogue default).

### Resolution Hierarchy

The [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py) module resolves the value and provenance of each parameter for each road segment through the `resolve()` function, following this strict cascading order of precedence (Decisions D4 and D7):

```
[ Fixed Parameter (Fix) ]         ---> If fixed by user in UI          ---> value = UI,           src = 'usuario'
            | (if not fixed)
[ Field Mapped in UI ]            ---> If field selected for feature   ---> value = Field,        src = 'oficial'
            | (if absent/null)
[ Official Translation (D2) ]     ---> If recognized official attr     ---> value = Translated,   src = 'oficial'
            | (if absent/null)
[ Candidate Attribute ]           ---> If candidate field on feature   ---> value = Feature,      src = 'oficial'
            | (if absent/null)
[ Complementary Layer ]           ---> If feature within max_dist_m    ---> value = Complement,   src = 'complementar'
            | (if absent/null)
[ Value where no data ]           ---> If entered by user in UI        ---> value = UI,           src = 'usuario'
            | (if catalogue default)
[ Road-Class Default ]            ---> Multilane / 2-lane / unpaved    ---> value = Class,        src = 'padrao'
            | (if absent/null)
[ Catalogue Default ]             ---> Residual factory fallback       ---> value = Catalogue,    src = 'padrao'
```

---

## 2. Complete Table of Operational and HCM Parameters

The table below lists the 18 parameters managed by the plugin (defined in [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py)), with their units, types, default values and the official fields that are automatically searched for in the input layers.

| Identifier (`id`) | Label / Parameter | Unit | Type | Default value | Candidate fields in the layer (official source) | Description / Accepted values |
|---|---|---|---|---|---|---|
| `tipo_segmento` | Segment type | - | Text (`str`) | `'2_faixas'` | `tipo_pista`, `pista`, `tipo_seg`, `tp_pista`, `ds_pista`, `tipo_segmento` | Functional classification of the segment: `2_faixas` (two-lane highway - Ch. 15), `multipista` (multilane highway - Ch. 12) or `freeway` (controlled-access freeway - Ch. 12). |
| `lanes` | Number of lanes per direction | lanes | Integer (`int`) | `1` | `faixas`, `num_faixas`, `faixas_sentido`, `nr_faixas`, `n_faixas`, `lanes` | Number of travel lanes available in the direction of travel being analyzed. |
| `pavimentado` | Paved | - | Boolean (`bool`) | `True` | `pavimentado`, `superficie`, `tp_superficie`, `ds_superficie`, `st_pavimentado` | Pavement indicator. Defines the road class for default free-flow speed (60 km/h for unpaved vs. 80 km/h paved). The HCM procedure applies no direct capacity penalty. |
| `urbano` | Urban segment | - | Boolean (`bool`) | `False` | `urbano`, `trecho_urbano`, `travessia_urbana`, `tp_trecho`, `is_urbano` | Flags whether the segment is an urban crossing (`True`) or a rural/intercity highway (`False`). |
| `largura_faixa` | Lane width | m | Decimal (`float`) | `3.5` | `largura_faixa`, `larg_faixa`, `lane_width` | Average width of the travel lanes. DNIT standard: 3.50 m. |
| `largura_acostamento` | Shoulder width | m | Decimal (`float`) | `2.5` | `largura_acostamento`, `acostamento`, `shoulder_width` | Usable width of the lateral shoulder. DNIT standard: 2.50 m. |
| `terreno` | Terrain type | - | Text (`str`) | `'ondulado'` | `terreno`, `tp_terreno`, `ds_terreno`, `terrain` | Topography of the segment: `plano` (flat), `ondulado` (rolling) or `montanhoso` (mountainous). Affects the heavy-vehicle passenger-car equivalent (`E_T`). |
| `pct_veic_pesados` | Percentage of heavy vehicles | % | Decimal (`float`) | `20.0` | `pct_veic_pesados`, `pct_pesados`, `veic_pesados`, `pct_hv`, `heavy_vehicles` | Percentage of the traffic composition made up of trucks and buses relative to total volume. |
| `vel_livre` | Free-flow speed (FFS) | km/h | Decimal (`float`) | `80.0` | `vel_livre`, `ffs`, `v_livre`, `vl_maxima`, `speed_limit` | Mean speed observed under low traffic volume (*Free-Flow Speed*). |
| `phf` | Peak hour factor (PHF) | - | Decimal (`float`) | `0.92` | `phf`, `fator_pico`, `peak_hour_factor` | Ratio between the total peak-hour volume and the maximum flow rate in the 15-minute sub-interval (*Peak Hour Factor*). |
| `pct_no_passing` | No-passing zones | % | Decimal (`float`) | `50.0` | `pct_no_passing`, `ultrapassagem_proibida`, `pct_proib_ultrapassagem` | Percentage of the length of a two-lane segment with a continuous no-passing marking. |
| `access_density` | Access density | accesses/km | Decimal (`float`) | `10.0` | `access_density`, `densidade_acessos`, `n_acessos_km` | Number of intersections, commercial driveways and entrances per kilometre (used in the FFS calculation for multilane highways). |
| `directional_split` | Directional split | % | Decimal (`float`) | `50.0` | `directional_split`, `divisao_direcional`, `split_dir` | Share of flow in the peak direction (e.g. 50 for 50/50, 60 for 60/40). |
| `bpr_alpha` | BPR function alpha | - | Decimal (`float`) | `0.15` | `bpr_alpha`, `alpha_bpr` | The `alfa` coefficient of the travel-time equation `t = t0 * [1 + alfa * (v/c) ^ beta]`. Applied per arc when present. |
| `bpr_beta` | BPR function beta | - | Decimal (`float`) | `4.0` | `bpr_beta`, `beta_bpr` | The `beta` exponent of the BPR congestion equation. Applied per arc when present. |
| `capacidade` | Per-direction capacity (0 = HCM) | veh/h | Decimal (`float`) | `0.0` | `capacidade`, `capacity`, `cap`, `capacidade_vph` | Per-direction capacity supplied. The **sentinel 0.0** means automatic calculation by the HCM (Ch. 12 or 15). If `> 0`, it takes precedence over the HCM (keeping the `escopo`). |
| `tempo_livre` | Free-flow time (0 = length ÷ FFS) | min | Decimal (`float`) | `0.0` | `tempo_livre`, `free_flow_time`, `fft`, `t0` | Free-flow travel time on the arc. The **sentinel 0.0** means geometric calculation (`length ÷ vel_livre`). If `> 0`, it takes precedence over the calculation. |
| `mao_unica` | One-way (geometry direction) | - | Boolean (`bool`) | `False` | `mao_unica`, `oneway`, `one_way`, `sentido_unico` | If `True`, the segment generates only the arc in the digitizing direction of the geometry (`fw`), omitting the reverse arc (`bw`). If `False`, it operates as two-way, generating `fw` and `bw`. |

---

### 2.1 The `0.0` Sentinel and Supplied Parameters

The `capacidade` and `tempo_livre` parameters use the value **`0.0` as an explicit sentinel** meaning "calculate automatically":

* **Why `0.0` and not `None`?** The plugin interface dynamically generates numeric controls (`QDoubleSpinBox`) from the `PARAMS` specifications. `None` cannot be represented directly in a Qt numeric *spinbox*, and an arbitrary positive default would override the entire network if the user did not supply a field.
* **Precedence when building the network**:
    * If `capacidade > 0.0`: the arc capacity receives exactly that value (with provenance `oficial` if it came from the layer, or `usuario` if it came from the UI), preserving the `escopo` classification (`rodoviario` or `urbano`). If `capacidade <= 0.0`, the analytical HCM 6th Edition procedure (`segment_capacity`) is triggered.
    * If `tempo_livre > 0.0`: the time `t0` receives the supplied value in minutes. If `tempo_livre <= 0.0`, it computes `t0 = (length_km / free_flow_speed_kmh) * 60.0`.
* **One-way (`mao_unica`)**:
    * When `mao_unica` resolves to `True` (recognizing textual or numeric values such as `True`, `1`, `'sim'`, `'yes'`, `'oneway'`), the road network builds **only the forward arc (`fw`)** and sets `arc_bw = None`. This ensures that already-oriented networks (such as Sioux Falls or directed municipal datasets) do not have their capacity artificially doubled by fictitious reverse arcs.

---

---

## 3. How Capacity is Estimated (Decision D9)

Capacity estimation for each road segment follows a structured three-tier process:
1. **What already exists in the official datasets** (basic geometry, cross-section type, pavement and identification);
2. **Complementary data** spatially associated (OSM networks, count stations, urban perimeters);
3. **Default values** by highway class and residual HCM catalogue fallbacks.

The resolution of the 18 operational and geometric parameters is handled by `params.resolve()`, which implements a **strict 8-step cascade** (Decision D4). The first step that yields a valid value wins; null, empty or non-coercible values cause resolution to fall through to the next step.

Resolution proceeds in **two passes**:
1. **First pass**: resolves `tipo_segmento` and `pavimentado`, which establish the road class for default speed and lane standards.
2. **Second pass**: resolves the remaining 16 operational parameters.

### The 8 Steps of the Resolution Cascade (Decision D4)

1. **Parameters fixed by the user (`overrides`)** &rarr; provenance **`usuario`**: Rows in the parameter table with the **Fix** checkbox ticked in the interface and no layer field mapped. Forces the specified value across the entire network, overriding official data.
2. **Field mapped in the layer (`field_map`)** &rarr; provenance **`oficial`**: Highway layer column explicitly selected in the *Layer field* combo.
3. **Automatic translation of feature attributes (`oficiais.traduz`)** &rarr; provenance **`oficial`**: Automatic detection of raw fields from official (DNIT, DER-SP) and collaborative (OSM) sources. Allows reading raw datasets or legacy GeoPackages without manual mapping.
4. **Candidate fields in the feature (`campos_candidatos`)** &rarr; provenance **`oficial`**: Automatic lookup by catalogue standard names (see Section 2). Because candidate lists include the parameter identifier itself, standardized networks downloaded via GisBR (Decision D3) are read directly at this step.
5. **Complementary layer by proximity (`complemento`)** &rarr; provenance **`complementar`**: Attributes of the nearest feature within the configured search radius (default 30 m), evaluated first through `oficiais.traduz()` and then through `campos_candidatos`.
6. **Value where there is no data (`defaults`)** &rarr; provenance **`usuario`**: Values entered into the *Value where there is no data* column in the interface without the *Fix* checkbox ticked, acting as fallback only where neither the road layer nor the complementary layer provided data.
7. **Road-class default (`PADRAO_POR_CLASSE`)** &rarr; provenance **`padrao`**: If `lanes` or `vel_livre` were not resolved in previous steps, standard values are assigned according to the class determined in the first pass:
    - **Multilane / freeway (`pista_dupla`)**: 2 lanes per direction, free-flow speed of 100 km/h;
    - **Two-lane paved (`pista_simples_pavimentada`)**: 1 lane per direction, free-flow speed of 80 km/h;
    - **Unpaved (`nao_pavimentada`)**: 1 lane per direction, free-flow speed of 60 km/h.
8. **Factory catalogue default (`PARAMS`)** &rarr; provenance **`padrao`**: Residual default value defined in each parameter's catalogue specification in the plugin.

### Translation Rules for Official Sources and OSM (Decision D2a)

The `traffic/oficiais.py` module translates attributes from official and collaborative sources into HCM parameters, ignoring case and normalizing accents and whitespace:

| Source field | Recognized values | Resulting HCM parameters |
|---|---|---|
| `TipoPista` (DER-SP), `Superficie_Federal` (SNV/DNIT) | `DUP` | `tipo_segmento = 'pista_dupla'`, `pavimentado = True` |
| idem | `PAV`, `EOD` | `tipo_segmento = '2_faixas'`, `pavimentado = True` |
| idem | `IMP`, `EOP`, `LEN` | `tipo_segmento = '2_faixas'`, `pavimentado = False` |
| `PerimetroU` (DER-SP) | Starts with `S` (`Sim`, `S`) | `urbano = True` |
| idem | Starts with `N` (`Não`, `Nã`, `N`) | `urbano = False` |
| `lanes` + `oneway` (OSM) | If `oneway` in {`yes`, `true`, `1`} | `lanes = int(lanes)` |
| idem | If `oneway` in {`no`, `false`, `0`} or absent | `lanes = max(1, int(lanes) // 2)` |
| `oneway` (OSM) | `yes`, `true`, `1` &rarr; `mao_unica = True`; `no`, `false`, `0` &rarr; `False` | `mao_unica = True` or `False` (`-1` does not translate) |
| `maxspeed` (OSM) | Numeric value in km/h | If speed limit &ge; 80 km/h: `vel_livre = limit + 8`<br>If speed limit < 80 km/h: `vel_livre = limit + 11` (HCM 6th ed. ch. 12: FFS = limit + 5 mph or + 7 mph below 50 mph) |

!!! note "GisBR estimated speeds are excluded from automatic rules"
    The `velocidade_kmh` attribute produced by GisBR during OSM extraction is **not** translated automatically. When an OSM road lacks `maxspeed`, GisBR estimates speed based on highway classification. Flagging this as `complementar` would violate the principle that *nothing is assumed silently*; users wishing to apply it can map the field explicitly.

### What Official Sources (DNIT and DER-SP) Provide and What is Missing

When downloading the official São Paulo state network via GisBR (merging federal DNIT/SNV and state DER-SP networks), official datasets directly provide only basic geometry and minimal operational attributes:

| HCM Parameter | DNIT (SNV) | DER-SP | Technical note |
|---|:---:|:---:|---|
| `tipo_segmento` | :white_check_mark: (`Superficie_Federal`) | :white_check_mark: (`TipoPista`) | Maps `DUP` to multilane and `PAV`/`IMP` to 2-lane. |
| `pavimentado` | :white_check_mark: (`Superficie_Federal`) | :white_check_mark: (`TipoPista`) | Identifies paved or unpaved surface. |
| `urbano` | :x: | :white_check_mark: (`PerimetroU`) | DNIT has no urban perimeter attribute; DER-SP provides `Sim`/`Nã`. |
| `lanes` | :x: | :x: | Neither official source provides exact lane counts. |
| `vel_livre` | :x: | :x: | Neither source provides posted or free-flow speeds. |
| `pct_veic_pesados` | :x: | :x: | Vehicle classification is not included per segment. |
| `terreno` | :x: | :x: | Terrain type (flat, rolling, mountainous) is absent. |
| `largura_faixa` | :x: | :x: | Absent; uses design standard default (3.5 m). |
| `largura_acostamento` | :x: | :x: | Absent; uses design standard default (2.5 m). |
| `access_density` | :x: | :x: | Not surveyed in official road inventories. |
| `pct_no_passing` | :x: | :x: | Not surveyed in official road inventories. |
| `phf` | :x: | :x: | Absent; uses planning default (0.92). |
| `directional_split` | :x: | :x: | Absent; adopts balanced 50/50 split. |
| `mao_unica` | :x: | :x: | Inferred from geometry/dual carriageway or complementary OSM layer. |

As shown by the table, official sources alone leave major gaps in essential parameters such as lane counts, free-flow speed, and traffic composition.

### Enrichment Recipe for São Paulo (Stage 2 — Complementary Layer)

To achieve high-fidelity capacity estimates in São Paulo state, we recommend augmenting the official network with complementary layers (selected in the Capacity tab under *Complementary data*):

1. **Lanes and speeds via OpenStreetMap (QuickOSM)**:
   - Download highway centerlines with `highway` matching `motorway`, `trunk`, or `primary` containing `lanes`, `oneway`, and `maxspeed` tags via the QuickOSM plugin.
   - Spatially snapped to official road links within 30 m, attributes for `lanes`, `vel_livre`, and `mao_unica` are absorbed with `complementar` provenance.
2. **Pre-processed OSM network from GisBR Base (`osm_links_rm<id>`)**:
   - In Metropolitan Areas covered by the [`gisbr_base`](https://github.com/d-camargo/gisbr_base) repository, the road link layer provides clean geometry with `maxspeed` and `oneway`, completing speed and directionality.
3. **Heavy vehicle percentage from count stations**:
   - A point layer of count monitoring stations (DER-SP or DNIT) containing `pct_veic_pesados` or `pct_pesados` transfers field-measured vehicle mix onto adjacent highway segments.
4. **Urban crossings for SNV via IBGE polygons**:
   - Because DNIT lacks urban boundary flags, linking **IBGE Urbanized Areas** polygons with an `urbano = 1` field flags federal highway crossings inside cities as urban (`escopo = 'urbano'`).

---

## 4. Override and Mapping Procedure

### 4.1 Direct Field Mapping in the Interface (Decision D7)

In the **Highway assignment** panel, on the **Capacity** tab, the parameter table provides a *Layer field* combobox allowing you to select any column from the road layer.

* **Mapping precedence (D4/D7)**: When the user selects a column in a parameter's combo, that field name is passed in the dictionary `field_map = {param_id: field_name}` to `params.resolve()`.
* **Official identification**: Any value successfully read from the mapped column is recorded with provenance **`oficial`**, even if the field name differs from standard candidate names (e.g. `cap_veic_hora` or `t_zero`).
* **Graceful fallback**: If the mapped field holds a null, empty, or invalid value on a given feature, the cascade falls through to subsequent steps (official translation, candidates, complementary data, and defaults).

### 4.2 Automatic Reading by Candidates (`oficial`)

If no field is selected in the interface's combo, the plugin automatically inspects the layer schema for the names listed in `campos_candidatos` (Section 2 table). The search is case-insensitive (`CAPACITY`, `Capacity`, and `capacity` are treated identically). The first candidate with valid data sets the parameter as `oficial`.

### 4.3 Fixing and Global Values in the Interface (`usuario`)

The parameter table offers two distinct modes of user intervention:

* **Fix (*Fix*) column**: Ticking a parameter's checkbox (without a layer field mapped) marks the value as an *override* (cascade step 1). It takes precedence over layer attributes and complementary layers, applying the value across all segments with **`usuario`** provenance.
* **Value where there is no data (*Value where there is no data*) column**: Without the *Fix* checkbox ticked, the entered value serves only as a residual fallback (cascade step 6) when neither the highway layer nor complementary layers provide data. If modified from factory defaults, it is recorded as **`usuario`**.

For sentinel parameters (`capacidade` and `tempo_livre`), the value `0.0` signals that analytical HCM calculation or geometric estimation should be preserved.

### 4.4 Assumed Default Values (`padrao`)

If a parameter has no fixed override, is found neither through field mapping, attribute translation, candidates, nor complementary layers, and was not modified in the interface, the plugin adopts the road-class default or residual factory value from the `PARAMS` catalogue.

* The corresponding provenance will be marked as **`padrao`**.
* When **Compute capacity** or **Assign** finishes, the message bar shows a summary of how many (arc, parameter) pairs came from each source (`oficial`, `complementar`, `usuario`, `padrao`), ensuring full traceability (Rule D7).
