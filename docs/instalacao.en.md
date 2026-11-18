# Installation

## Supported QGIS versions

`desire_lines/metadata.txt` declares support from QGIS 3.0 up to the 4.x series
(`qgisMaximumVersion=4.99`) and declares `supportsQt6=True`: the plugin runs on
both Qt5 and Qt6 builds of QGIS (the code uses qualified enums and
`QMetaType.Type.<X>`).

| Item | Value |
|---|---|
| Minimum QGIS version | 3.0 |
| Maximum QGIS version | 4.99 |
| Qt | Qt5 and Qt6 |
| Current plugin version | 0.7.4 |

## Install from the official QGIS repository

Desire Lines is published in the [official QGIS plugin
repository](https://plugins.qgis.org/plugins/desire_lines/). In QGIS, open
*Plugins → Manage and Install Plugins*, search for **Desire Lines** in the *All*
tab and click *Install Plugin*. QGIS notifies you when a new version is
released.

## Where the plugin shows up after installation

Desire Lines shows up in two places: in the plugins toolbar as a **single button
with a drop-down arrow** (clicking the icon opens the main *Desire Lines*
dialog; the arrow opens the drop-down menu with the *Desire Lines* and *Highway
Assignment* options), and in the *Vector* → *&Desire Lines* menu (with the same
options).

![Desire Lines icon in the toolbar and entry in the Vector menu](https://github.com/user-attachments/assets/69aaddac-a9c1-4cee-a3cb-c3fb0cbf7148)

## GISBR requirement (Highway Assignment tab)

!!! warning "GISBR is optional (only needed to download the official network)"
    [GISBR](https://github.com/d-camargo/gisbr) is optional: it is what fetches
    the official highway network (SNV/DNIT, INDE) and requires QGIS 3.16 or
    newer. Desire Lines checks at runtime whether GISBR is installed and does
    not ask you to install it when it already exists.

    **Without GISBR installed**, **one** window appears when the plugin loads,
    suggesting the installation, with a button for the Plugin Manager and a
    "Don't show again" option.

    Even without GISBR, the first three tabs (*OD Matrix*, *Desire Lines*,
    *AoN (Delaunay)*) work normally. In the *Highway Assignment* tab, the
    visible warning is still shown and the option to download the network via
    GISBR is disabled — but the tab remains usable if you already have a
    highway network layer loaded in the project and point to it. In other
    words, what you lose without GISBR is the download of the official network,
    not the whole tab.

    The message shown is: "O plugin GisBR
    (https://github.com/d-camargo/gisbr) é necessário para obter a malha
    rodoviária oficial." (in English: "The GisBR plugin
    (https://github.com/d-camargo/gisbr) is required to obtain the official
    highway network.")

## Installation by symlink (development)

If you work on the code, there is no need to build a zip after every change.
From the repository root:

```bash
make deploy            # symlinks desire_lines/ into the default QGIS profile
make deploy-flatpak    # same symlink, in the QGIS Flatpak profile
make undeploy          # removes the symlink from the default profile
make undeploy-flatpak  # removes the symlink from the Flatpak profile
```

`make deploy` creates the symlink at
`~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/desire_lines`.
After changing code, reload with Plugin Reloader or restart QGIS.

To understand how the code is organised, see [Architecture](arquitetura.md).
