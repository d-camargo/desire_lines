# Desire Lines

**Desire Lines** is a QGIS plugin for **transport demand analysis from an
Origin/Destination (OD) matrix**. From the matrix and a traffic zone layer, it builds
the centroids, the desire lines and the assigned demand — either on a synthetic
neighbourhood network or on the real highway network, with capacity computed by the
HCM 6th Edition procedure.

It is made for people who plan transport, not for people who program: everything
happens inside QGIS, in a three-tab dialog and a dockable panel, and each step
writes a table to the same output GeoPackage.

## The tools

- **OD Matrix** ("Origin/Destination Matrix") — imports the OD matrix from CSV and
  the traffic zone layer, and generates the centroids.
- **Desire Lines** — draws one straight line per OD pair between centroids, with
  width proportional to the flow.
- **AoN (Delaunay)** — assigns demand by All-or-Nothing on a synthetic Delaunay
  network between the centroids.
- **Highway Assignment** (dockable panel) — computes capacity by the HCM 6th
  Edition and assigns demand on the real highway network (SNV), by AoN, by
  MSA/BPR equilibrium or by Frank-Wolfe equilibrium (default).

!!! warning "Scope of Highway Assignment"
    This tool was developed for **rural and interurban highways**: urban
    crossings inside the network are flagged with `escopo = 'urbano'` and
    warned about, not recomputed with an urban procedure. The GISBR plugin is
    **optional**: it is only needed to download the official network (SNV/INDE).
    Without it, the panel keeps working with a network layer already loaded in
    the project; only the download is disabled.

## Where to start

<div class="grid cards" markdown>

-   **[Installation](instalacao.md)**

    Supported QGIS versions, installation from the official QGIS repository and
    the optional GISBR for downloading the highway network.

-   **[Guides](guias/matriz-od.md)**

    One guide per tab, from the OD matrix CSV to highway assignment, plus an
    end-to-end tutorial with the example data.

-   **[Reference](referencia/formatos-de-entrada.md)**

    Input formats, fields of each output layer, HCM parameters with provenance
    and the criteria for choosing between methods.

-   **[Troubleshooting](solucao-de-problemas.md)**

    What to do when the matrix will not read, GISBR does not show up or the
    assignment comes out empty.

</div>
