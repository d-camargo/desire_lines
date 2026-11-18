# Troubleshooting

One item per symptom. Each gives the **message** as it appears in the QGIS
message bar (in Portuguese, when the PT-BR translation is active), the
**cause** and **what to do**. If you got here with a message on screen, search
for it on this page (`Ctrl+F`).

---

## The option to download the network via GISBR is disabled

!!! warning "Message"
    "O plugin GisBR (https://github.com/d-camargo/gisbr) é necessário para
    obter a malha rodoviária oficial." (i.e. "The GisBR plugin is required to
    obtain the official highway network.") — shown as a fixed warning at the
    top of the *Highway Assignment* tab.

**Cause.** The [GISBR](https://github.com/d-camargo/gisbr) plugin is optional
and is either not installed or was not detected. The check is done at runtime
(`gisbr_bridge.is_available()`): it tries to import
`gisbr.core.sources`/`gisbr.core.connectors.wfs` and, if that fails, looks for
the `gisbr` processing provider registered in QGIS. Desire Lines does not ask
you to install it when it already exists. Without GISBR installed, **one**
window appears when the plugin loads, suggesting the installation, with a
button for the Plugin Manager and a "Don't show again" option (the warning in
the assignment tab remains).

**What to do.**

* The **tab is not disabled as a whole** — only the radio button
  *Download via GisBR (official SNV/DER network)* is turned off. If you already
  have a highway network layer in the project, choose *use existing layer* and
  the tab works normally.
* To get the download back, install GISBR (QGIS 3.16+) and reopen the dialog —
  see [Installation](instalacao.md).

---

## Failure downloading the network from GISBR

!!! warning "Message"
    "Falha ao obter a malha rodoviária do GisBR: …" (i.e. "Failed to obtain the
    highway network from GisBR: …"; the end varies with the error returned by
    GISBR).

**Cause.** GISBR is installed, but the request did not return a layer: network
unavailable, the SNV/INDE WFS service down or slow, a proxy/firewall blocking
it, or a state (UF)/extent that produced no features at all.

**What to do.**

1. Test GISBR on its own (download the network through it) — if it fails
   there, the problem is not in Desire Lines.
2. Check the connection and the QGIS proxy settings
   (*Settings → Options → Network*).
3. Check the state abbreviation (UF): the button only enables with **exactly 2
   letters**.
4. If the service is unstable, download the network once, save it to a
   GeoPackage and switch to *existing layer* mode — this avoids depending on
   the network on every run.

---

## The network was empty after clipping

!!! warning "Message"
    "A malha rodoviária ficou vazia após o recorte." (i.e. "The highway network
    was empty after clipping.")

**Cause.** Clipping by the study area (the envelope of the centroids plus the
connector margin) did not intersect any feature of the network. Almost always
it is a **CRS or region mismatch**: centroids in one place, network in another.

**What to do.**

* Check that centroids and network are in the same region of the map — load
  both layers and look.
* Confirm the declared CRS of each layer (a wrong CRS shifts everything).
* Increase *Max connector (m)*: it also increases the clipping margin.
* If you are downloading via GISBR, check that the UF is the one of the study
  area.

!!! note "Similar warning, but not fatal"
    "Não foi possível recortar a malha pela área de estudo (…); usando a malha
    completa." (i.e. "Could not clip the network to the study area (…); using
    the full network.") — here the clipping failed and the plugin **carried
    on** with the whole network. It does not invalidate the result; it only
    makes the run slower.

---

## No centroid (or only a few) connected to the network

!!! warning "Messages"
    "Nenhum centróide pôde ser conectado à malha rodoviária (nó mais próximo
    além de … m)." (no centroid could be connected to the highway network;
    nearest node beyond … m — critical, stops the run) or "{n} centróide(s)
    não conectados à malha rodoviária." ({n} centroid(s) not connected to the
    highway network — warning, continues with the rest).

**Cause.** The centroid connector links each centroid to the nearest node of
the network, but only up to the configured maximum distance. Large zones, zones
with no highway nearby or a sparse network leave the centroid out of reach.

**What to do.**

* **Increase *Max connector (m)*** in the *Highway Assignment* tab (default
  5000 m). This is the adjustment that solves most cases.
* If only a few zones are left out, check whether they are peripheral zones or
  islands — it may be more correct to exclude them from the analysis than to
  stretch the connector to the point of inventing an access that does not
  exist.
* An excessively long connector distorts the shortest path: prefer the smallest
  value that connects all the zones of interest.

---

## Matrix zone with no matching centroid

!!! warning "Messages"
    "Nenhum par OD correspondeu aos ids dos centroides. Verifique se Origem,
    Destino e ID de Tráfego usam o mesmo esquema de id." (*AoN (Delaunay)* tab;
    no OD pair matched the centroid ids — check that Origin, Destination and
    Traffic ID use the same id scheme) · "Nenhum par OD corresponde aos
    centróides conectados. Verifique se Origem, Destino e Id de tráfego usam o
    mesmo esquema de identificação." (*Highway Assignment* tab) · "{n} linha(s)
    da matriz com ids desconhecidos" ({n} matrix row(s) with unknown ids —
    warning in the summary, when only part did not match).

**Cause.** The origin/destination ids in the matrix do not match the id field
chosen in the centroid layer. Typical causes: different fields selected in the
combos, a numeric id on one side and text on the other, blank spaces, leading
zeros, or zones that exist in the matrix but not in the layer.

**What to do.**

1. Check the three combos (*Origin*, *Destination*, *Traffic ID*) — the layer
   id must use the same scheme as the matrix ids.
2. The plugin normalises ids before comparing (`_zone_key`): `10.0` and `10`
   match, and spaces at the ends are ignored. What does **not** match is
   `"010"` with `10`, nor ids from different schemes — see
   [Input formats](referencia/formatos-de-entrada.md).
3. If the message is the "{n} matrix row(s) with unknown ids" warning, the run
   finished: those rows were **discarded**, and the result covers only the
   rest. It is worth checking whether the discard is acceptable.

---

## Null or invalid capacity

!!! warning "Messages"
    "{n} de {N} arcos descartados por capacidade nula ou inválida." ({n} of {N}
    links discarded for null or invalid capacity — warning) · "Nenhum arco tem
    capacidade válida; revise os parâmetros HCM." (no link has valid capacity;
    review the HCM parameters — critical, stops the run).

**Cause.** Capacity comes out of the HCM procedure; a non-positive value means
the inputs for that link are unusable (zero lanes, missing facility type, width
or factor out of range). Keeping those links would cause a division by zero in
v/c and report LOS F where the problem is missing data — so they are
**removed**.

**What to do.**

* Check the network fields mapped to the HCM parameters and the global override
  values — see [HCM parameters](referencia/parametros-hcm.md).
* Use the provenance field (`src_*`) of the output layer to see which
  parameters came as `oficial`, `padrao` or `usuario`: mass discarding usually
  means an expected field does not exist in the network.
* If the discard is small and localised, inspect those links in the attribute
  table before accepting the result.

---

## Geographic CRS in a metric analysis

!!! warning "Message"
    "não foi possível determinar um SRC métrico automaticamente; reprojete os
    centroides para um sistema métrico (UTM) e tente novamente." (i.e. "could
    not determine a metric CRS automatically; reproject the centroids to a
    metric system (UTM) and try again.")

**Cause.** Distances, lengths and connectors are computed in metres. The plugin
picks a metric CRS on its own (automatic UTM zone if the area fits in one zone;
otherwise SIRGAS 2000 / Brazil Albers, EPSG:10857). The message appears when
even that automatic choice was not possible — usually because the source CRS of
the centroids is missing or inconsistent with the coordinates.

**What to do.**

* Reproject the centroids to a metric CRS (UTM of the region, or EPSG:10857)
  and run again.
* Confirm that the layer's **declared** CRS is the real CRS of the data — a
  layer in degrees marked as metric (or the opposite) is the most common cause.
* For the automatic selection rule, see
  [AoN (Delaunay)](guias/aon-delaunay.md).

---

## Very slow run on a large network

**Cause.** The graph engine is pure Python (it exists by decision D4 — the
native QGIS engine does not allow updating link cost between iterations). The
comfortable envelope is around **50,000 directed links**; MSA runs one Dijkstra
per origin **on every iteration**, so the cost grows with
`iterations × origins`.

**What to do.**

* **Use AoN** for diagnosis and for iterating quickly: it is a single pass,
  roughly 10× faster than MSA with 10 iterations.
* Reduce MSA *Max iterations*, or loosen the gap tolerance.
* Clip the network to the study area (leave clipping on) and reduce the number
  of zones/unique origins — that is what weighs the most.
* Details in [Methods](referencia/metodos.md).
