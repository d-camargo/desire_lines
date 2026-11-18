# HCM Parameters and the Provenance Rule

This page presents the complete technical reference for all the operational and geometric parameters used in highway capacity calculation under the **HCM 6th Edition** (Highway Capacity Manual) and in the traffic assignment of the **Desire Lines** plugin.

---

## 1. Parameter Provenance Rule (Decision D7)

To ensure transparency and technical auditability in transport planning studies, the plugin strictly adopts **Rule D7 — "Nothing is assumed silently"**.

No capacity parameter is applied to a highway without its origin being explicitly declared. For each parameter `X` used, the output layer records a matching `src_X` field whose provenance value indicates one of three possible origins:

1. **`usuario`**: The value was entered or overridden manually by the user in the plugin interface.
2. **`oficial`**: The value was read directly from an attribute that exists in the highway layer (e.g. official SNV/DNIT or DER data obtained through GISBR).
3. **`padrao`**: The parameter was not in the layer's attribute table and was not overridden in the interface; the plugin applied the documented default value.

### Resolution Hierarchy

The [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py) module resolves the value and provenance of each parameter for each road segment through the `resolve()` function, following this strict order of precedence (Decision D7):

```
[ User Override ]             ---> If a global value is set in the UI  ---> value = UI,            src = 'usuario'
            | (if absent)
[ Field Mapped in the UI ]    ---> If a field is selected for the feature ---> value = Mapped Field, src = 'oficial'
            | (if absent/null)
[ Candidate Attribute ]       ---> If a candidate field exists          ---> value = Feature,       src = 'oficial'
            | (if absent/null)
[ Default Value ]             ---> Catalogue fallback                   ---> value = Default,       src = 'padrao'
```

---

## 2. Complete Table of Operational and HCM Parameters

The table below lists the 18 parameters managed by the plugin (defined in [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py)), with their units, types, default values and the official fields that are automatically searched for in the input layers.

| Identifier (`id`) | Label / Parameter | Unit | Type | Default value | Candidate fields in the layer (official source) | Description / Accepted values |
|---|---|---|---|---|---|---|
| `tipo_segmento` | Segment type | - | Text (`str`) | `'2_faixas'` | `tipo_pista`, `pista`, `tipo_seg`, `tp_pista`, `ds_pista`, `tipo_segmento` | Functional classification of the segment: `2_faixas` (two-lane highway - Ch. 15), `multipista` (multilane highway - Ch. 12) or `freeway` (controlled-access freeway - Ch. 12). |
| `lanes` | Number of lanes per direction | lanes | Integer (`int`) | `1` | `faixas`, `num_faixas`, `faixas_sentido`, `nr_faixas`, `n_faixas`, `lanes` | Number of travel lanes available in the direction of travel being analyzed. |
| `pavimentado` | Paved | - | Boolean (`bool`) | `True` | `pavimentado`, `superficie`, `tp_superficie`, `ds_superficie`, `st_pavimentado` | Pavement indicator. Unpaved segments (`False`) receive a capacity penalty. |
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

## 3. Override and Mapping Procedure

### 3.1 Direct Field Mapping in the Interface (Decision D7)

In the **Highway assignment** panel, on the **HCM Parameters** tab, each parameter has a *combobox* (*field:*) that lets you select any column of the road layer directly.

* **Mapping precedence (D7)**: When the user selects a column in a parameter's *combobox*, that field name is sent in the dictionary `field_map = {param_id: field_name}` to the `params.resolve()` method.
* **Official identification**: Any value successfully read from the mapped column is recorded with provenance **`oficial`**, even if the field name in your dataset is completely different from the pre-registered candidates (for example, a column named `cap_veic_hora` or `t_zero`).
* **Graceful fallback**: If the mapped field holds a null, empty or invalid value on a given feature, the resolver searches the default candidate list and, if nothing is found, applies the factory value (`padrao`).

### 3.2 Automatic Reading by Candidates (`oficial`)

If no field is selected in the interface's *field:* combo, the plugin automatically inspects the layer schema for the names listed in `campos_candidatos` (table above). The search is case-insensitive (`CAPACITY`, `Capacity` and `capacity` are treated identically). The first candidate with valid data sets the parameter as `oficial`.

### 3.3 Global Override in the Interface (`usuario`)

The user can type or adjust a global value in the edit control of any parameter in the interface.

* Global values typed in the interface have the highest priority: they prevail over mapped fields and over candidates that exist on the feature.
* The provenance written to the `src_*` field of the resulting layer will be marked as **`usuario`**.
* For the parameters with a sentinel (`capacidade` and `tempo_livre`), the default value `0.0` signals that no global override is active, allowing the value to be read from the layer or calculated automatically.

### 3.4 Assumed Default Values (`padrao`)

If a parameter has no user override and is found neither through field mapping nor through the candidate names, the plugin adopts the factory value from the `PARAMS` catalogue.

* The corresponding provenance will be marked as **`padrao`**.
* When **Compute capacity** or **Assign** finishes, the message bar shows a summary of how many (arc, parameter) pairs came from each source (`oficial`, `usuario`, `padrao`), ensuring full traceability (Rule D7).
