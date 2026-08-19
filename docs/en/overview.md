# Overview (English)

**Desire Lines** is a QGIS plugin for **transport demand analysis from an
Origin/Destination (OD) matrix**. From the matrix and a traffic zone layer it builds
the zone centroids, the desire lines and the assigned demand — either on a synthetic
neighbourhood network or on the real highway network, with capacity computed by the
HCM 6th Edition procedure.

Everything runs inside a single four-tab dialog in QGIS, and each step writes a table
into the same output GeoPackage.

## The four tabs

1. **Origin/Destination Matrix** — imports the OD matrix (CSV) and the traffic zone
   layer, and generates the centroids.
2. **Desire Lines** — draws one straight line per OD pair between centroids, with
   width proportional to the flow.
3. **AoN (Delaunay)** — All-or-Nothing assignment over a synthetic Delaunay network
   built between the centroids (a topological neighbourhood abstraction, not a real
   road network).
4. **Highway Assignment** (*Alocação em rodovias*) — capacity by HCM 6th Edition
   (ch. 15 two-lane, ch. 12 multilane/freeway) and assignment on the real highway
   network (SNV), by AoN or by MSA/BPR equilibrium.

!!! warning "Requirements and scope of the Highway Assignment tab"
    This tab needs the [**GISBR**](https://github.com/d-camargo/gisbr) plugin
    (`plugin_dependencies=GisBR`), which is what downloads the official Brazilian
    highway network (SNV/DNIT, INDE). Without GISBR the first three tabs work
    normally; in this tab the download option is disabled, and you can still use it
    by pointing to a highway layer already loaded in the project.

    Its scope is **rural and interurban highways**. Urban crossings inside the
    network are flagged with `escopo = 'urbano'` and warned about — they are *not*
    recomputed with an urban procedure.

## Install in three steps

1. In QGIS, open *Plugins → Manage and install plugins* and go to
   **Install from ZIP**.
2. Select the downloaded `desire_lines-<version>.zip` and click *Install Plugin*;
   confirm the QGIS security warning with *Yes*.
3. Close the plugins window. The plugin shows up in the plugins toolbar and under
   the *Vector → &Desire Lines* menu.

Supported QGIS: 3.0 up to the 4.x series (Qt5 and Qt6 builds). GISBR itself requires
QGIS 3.16 or newer.

---

!!! note "Full documentation is in Portuguese"
    This page is the whole English documentation. The complete manual — guides for
    each tab, input formats, output fields, HCM parameters, method choice,
    troubleshooting and architecture — is written in Brazilian Portuguese: start at
    **[Início](../index.md)**.
