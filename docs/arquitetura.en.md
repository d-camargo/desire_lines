# Desire Lines Architecture

This document describes the internal structure of the **Desire Lines** plugin, the QGIS dependency boundary, how to run the test suite, the packaging process and the condensed record of the architecture decisions (**D1–D12**) of the highway assignment module.

---

## 1. Module Map

All of the plugin's source code lives inside the `desire_lines/` folder:

```text
desire_lines/
├── __init__.py                # QGIS plugin entry point (classFactory)
├── desirelines.py             # Main class: initGui(), run(), unload()
├── desirelines_dialog.py      # UI logic of the main dialog (tabs 1 to 3)
├── desirelines_dialog_base.ui # Qt Designer interface (layout of the dialog's 3 tabs)
├── traffic_panel.py           # UI logic of the dockable panel (Highway Assignment)
├── traffic_panel_base.ui      # Qt Designer interface (dockable panel layout)
├── ui_common.py               # Common UI mixin (PluginUiMixin) shared by dialog and panel
├── aon.py                     # AoN core on a synthetic Delaunay network (no GUI)
├── metadata.txt               # Official metadata read by QGIS and plugins.qgis.org
├── icon.png                   # Plugin icon in QGIS
├── i18n/                      # Translations (DesireLines_pt.qm)
└── traffic/                   # Traffic assignment subpackage on the real highway network
    ├── __init__.py
    ├── hcm.py                 # HCM capacity procedures (ch. 12 and 15)
    ├── graph.py               # Directed graph in pure Python (heapq + Dijkstra)
    ├── network.py             # Road network construction and centroid connectors
    ├── params.py              # HCM parameter handling and provenance (src_*)
    ├── assignment.py          # Assignment engines (AoN and MSA + BPR)
    ├── gisbr_bridge.py        # GISBR plugin integration and runtime check
    ├── malha_gisbr.py         # GISBR network download, clipping and geometric merge
    ├── merge.py               # Dangling end stitching, cleaning and schema unification (pure Python)
    └── outputs.py             # Output layers (capacidade_hcm/alocacao_*) and v/c styles
```

### Component Details

- **`desirelines.py`**: Manages the plugin lifecycle in the QGIS toolbar and menus. Instantiates the `DesireLinesDialog` dialog and controls the display of the `TrafficAssignmentPanel` dockable panel.
- **`desirelines_dialog.py`**: Orchestrates the graphical interface of the main dialog (OD Matrix, Desire Lines and AoN Delaunay tabs).
- **`traffic_panel.py`**: Orchestrates the interface of the *Highway Assignment* dockable panel (`TrafficAssignmentPanel`), connecting the panel controls to the calculation engines in `traffic/`.
- **`traffic_panel_base.ui`**: Qt Designer layout of the dockable panel (dock widget) with its two inner tabs: *Assignment* and *HCM Parameters*.
- **`ui_common.py`**: Provides the `PluginUiMixin` mixin class with shared interface helper methods (messages, progress bar and GeoPackage writing).
- **`aon.py`**: GUI-independent module for Tab 3 (AoN Delaunay).
- **`traffic/`**: Subpackage dedicated to HCM capacity calculation and real highway assignment (`traffic/` remains widget-free, decoupling the calculation engine from the UI).
- **`traffic/merge.py`**: Pure Python module for line cleaning (discarding planned segments and duplicates), ordered attribute schema unification and topological stitching of dangling ends (`costura_extremidades`).
- **`traffic/malha_gisbr.py`**: Orchestrates downloading via GISBR, metric CRS reprojection, territorial clipping, geometric overlap subtraction (`subtrai_sobreposicao`) and writing the unified network.

---

## 2. Boundary Between Pure Logic and PyQGIS

The plugin code is split into two categories according to its dependence on the QGIS API (`qgis.core` and `qgis.PyQt`):

### 2.1 Pure Python Modules (no QGIS dependency)
These modules import no QGIS component and can be run/tested in any Python 3 environment:

- **`traffic/hcm.py`**: Calculations of the HCM capacity equations (two-lane, multilane and freeway capacities).
- **`traffic/graph.py`**: Implementation of the custom directed graph using native Python structures (`heapq`, `dict`).
- **`traffic/network.py`**: Builder of the road graph and calculation of the connectors between centroids and network nodes.
- **`traffic/params.py`**: Parsing rules for HCM parameters and provenance assignment (`src_*`).
- **`traffic/assignment.py`**: AoN and MSA (Method of Successive Averages) traffic assignment algorithms.
- **`traffic/merge.py`**: Cleaning invalid geometries and planned segments, exact duplicate elimination, schema unification and topological stitching of dangling ends (node-to-node snapping and orthogonal projection T-splits).

### 2.2 Modules with a PyQGIS Dependency
These modules use QGIS classes (`QgsVectorLayer`, `QgsFeature`, `QgsGraphAnalyzer`, etc.) and require an initialised QGIS environment:

- **`aon.py`**: Uses native QGIS processing (`native:delaunaytriangulation`, `native:polygonstolines`, etc.) and `QgsGraphAnalyzer` for the synthetic network.
- **`traffic/outputs.py`**: Builds the output vector layers and applies the `vc`-graduated symbology.
- **`traffic/gisbr_bridge.py`**: Makes calls via `processing.run('gisbr:...')` or imports internal GISBR modules.
- **`traffic/malha_gisbr.py`**: Orchestrates calls to GISBR connectors, spatial indexing (`QgsSpatialIndex`), metric reprojection and overlap trimming with `QgsGeometry`.
- **`desirelines_dialog.py` / `traffic_panel.py` / `ui_common.py` / `desirelines.py`**: Interact directly with the Qt widgets and the user interface.

---

## 3. How to Run the Test Suite

The repository's test suite lives in `test/` and is run via `pytest`.

### Recommended Execution

From the repository root, run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest test -q
```

### Why is the `QT_QPA_PLATFORM=offscreen` variable mandatory?

Tests that import QGIS or PyQt components need to initialise a `QApplication` instance (defined in `test/utilities.py:get_qgis_app()`). In environments without an active X/Wayland server (such as CI environments, VPS servers or SSH terminals):

- Without `QT_QPA_PLATFORM=offscreen`, Qt tries to open a graphical display, fails and immediately terminates the Python process with a **core dump** / **segmentation fault**.
- With `QT_QPA_PLATFORM=offscreen`, Qt's in-memory rendering plugin is enabled, allowing the suite to run completely without a graphical interface.

> **Note**: The `make test` command runs only a quick Python syntax check (`ast.parse`) and does not replace the full `pytest` suite.

---

## 4. Packaging and Deploy

Packaging the plugin for publication is automated by `qgis-plugin-ci`.

### Build Flow

1. **Configuration**: Defined in the `.qgis-plugin-ci` file at the project root:
   ```yaml
   plugin_path: desire_lines
   github_organization_slug: d-camargo
   project_slug: desire_lines
   ```
2. **ZIP generation**:
   ```bash
   make package
   ```
   This command runs `qgis-plugin-ci package $(VERSION) --disable-submodule-update` and saves the resulting artifact in the `dist/desire_lines-<version>.zip` folder.
3. **Export filters**: The `.gitattributes` file uses the `export-ignore` directive to ensure development files (`docs/`, `test/`, `examples/`, `Makefile`, etc.) are left out of the production package.
4. **Package name**: The root directory inside the published ZIP file **must be named `desire_lines`**, exactly matching the id registered on `plugins.qgis.org`.

---

## 5. Condensed Record of Architecture Decisions (D1–D12)

The following architecture decisions guided the development of the highway traffic assignment module (`desire_lines/traffic/`):

- **D1 — HCM-CALC is a reference, not a dependency**: HCM-CALC is a Windows application with no declared free licence; the HCM algorithms were reimplemented in pure Python and the HCM-CALC examples are used only as a reference in the unit tests. The `traffic/` subpackage remains widget-free.
- **D2 — Highway HCM scope restricted to SNV/DER**: Covers two-lane segments (HCM ch. 15) and divided/multilane/freeway segments (ch. 12); excludes signalised intersections and urban crossings because that data is absent from the official highway database.
- **D3 — LOS by `v/c` bands (declared approximation)**: The Level of Service (LOS A to F) is determined by bands of the volume/capacity (`v/c`) ratio for quick bottleneck diagnosis, since the national database does not provide the exact HCM density.
- **D4 — Custom Python graph (`heapq`), not `QgsGraph`**: `QgsGraph` creates edges per geometric segment with no link to the feature's links, which would make it impossible to recompute the link cost at every MSA iteration; the custom Python graph solves this and supports networks of up to ~50,000 links.
- **D5 — Directed links (one per direction)**: Each highway segment is represented by two independent directed links (A→B and B→A, with reversed geometries), allowing directional flows, capacities and costs.
- **D6 — GISBR as an optional dependency with runtime check**: The dependency was removed from the metadata because QGIS compares the exact name (`GisBR` in the repository × `GISBR` in the installed metadata) and kept asking for the installation. GISBR is optional: the plugin checks at runtime (`gisbr_bridge.is_available()`) and does not ask to install it when it already exists. Without GISBR, a window appears when the plugin loads suggesting the installation, with a button for the Plugin Manager and a "Don't show again" option (the warning in the assignment tab remains and softly disables the network download if GISBR is not installed).
- **D7 — HCM parameters with provenance and documented defaults**: Applies the hierarchy (official field → documented default → user override) and records the origin of each parameter in the `src_*` fields for full auditability.
- **D8 — Code in an isolated `traffic/` subpackage**: Assignment and capacity calculation logic concentrated in `desire_lines/traffic/` with no dependency on GUI widgets (`traffic/` remains widget-free), easing testing and maintenance.
- **D9 — Separate action buttons (Compute capacity vs. Assign)**: Lets the HCM operational capacity be computed and inspected in the attribute table before running the assignment algorithms.
- **D10 — AoN exposed as a first-class method**: The All-or-Nothing (AoN) method is exposed to the user as a first-class option for preliminary analyses on large networks, besides being the base step of each MSA iteration.
- **D11 — Flagged urban crossings (`escopo='urbano'`)**: Urban segments in the highway network are not removed, but receive the highway capacity as a declared approximation and are marked `escopo='urbano'` for an alert in the log and on the map.
- **D12 — Geometric merge with precedence and topological stitching (D3/D4)**: Merging the federal network (DNIT/SNV) and state databases (DER) follows federal precedence, trimming overlapping state segments (intersection ≥ 100 m within a 20 m buffer) and stitching dangling ends to existing nodes or splitting links at T-junctions within 30 m, without connecting grade-separated crossings (overpasses). Features receive traceability attributes (`fonte` and `ajuste`).
