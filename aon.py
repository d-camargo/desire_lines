# -*- coding: utf-8 -*-
"""
All-or-Nothing (AoN) allocation over a Delaunay network.

This module is intentionally free of GUI code so it can be unit-tested from
the QGIS Python Console (see test/). It uses only ``qgis.analysis`` and
``qgis.core`` plus native Processing algorithms — no external dependencies
(no NetworkX). See AoN_delaunay_desire_lines.md for the rationale.

Pipeline (per AoN_delaunay_desire_lines.md, Section 4):
  A. Centroids + OD demand come from the caller (the dialog reads them).
  B. ``build_delaunay_edges`` builds the simplified network (Delaunay edges).
  C. ``allocate_aon`` builds the graph and runs Dijkstra-based AoN.

The math (Section 2): for every OD pair the *entire* flow follows the single
least-cost path; ``x_a += f_od`` for each edge ``a`` on that path.
"""
from qgis import processing
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
)
from qgis.analysis import (
    QgsGraphBuilder,
    QgsGraphAnalyzer,
    QgsVectorLayerDirector,
    QgsNetworkDistanceStrategy,
)


# --- CRS selection ----------------------------------------------------------

# IBGE-standard equal-area projection for Brazil ("SIRGAS 2000 / Brazil
# Albers"), used when the OD area spans more than one UTM zone (a single UTM
# zone would distort the far edges). The proj4 string is a fallback for PROJ
# databases too old to know EPSG:10857.
BRAZIL_ALBERS_EPSG = 10857
BRAZIL_ALBERS_PROJ4 = (
    '+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 '
    '+x_0=5000000 +y_0=10000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 '
    '+units=m +no_defs'
)


def _brazil_albers():
    """Brazil Albers CRS, by EPSG id with a proj4 fallback for old PROJ."""
    crs = QgsCoordinateReferenceSystem.fromEpsgId(BRAZIL_ALBERS_EPSG)
    if crs.isValid():
        return crs
    # Build from the proj4 string. fromProj()/createFromProj() exist only from
    # QGIS 3.10; createFromProj4() covers 3.0+ (the plugin's minimum).
    crs = QgsCoordinateReferenceSystem()
    if hasattr(crs, 'createFromProj'):
        crs.createFromProj(BRAZIL_ALBERS_PROJ4)
    else:
        crs.createFromProj4(BRAZIL_ALBERS_PROJ4)
    return crs


def _utm_zone(lon):
    """UTM zone number (1..60) for a longitude in degrees."""
    zone = int((lon + 180.0) / 6.0) + 1
    return max(1, min(60, zone))


def pick_metric_crs(src_crs, extent):
    """Choose a metric CRS for the graph.

    :param src_crs: source CRS of the centroids (``QgsCoordinateReferenceSystem``).
    :param extent: (min_lon, min_lat, max_lon, max_lat) of the centroids,
        expressed in ``src_crs`` units.
    :returns: (target_crs, reason). ``target_crs`` is ``None`` (with an
        explanatory ``reason`` dict) when no valid metric CRS could be determined
        and the caller should ask the user for a metric (UTM) layer.

    Rules (decided with the user):
      * src already projected/metric  -> use as-is.
      * geographic, fits one UTM zone -> assign that UTM zone automatically.
      * geographic, spans >1 zone or  -> Brazil Albers (EPSG:10857).
        crosses the equator
    """
    if not src_crs.isGeographic():
        return src_crs, {'code': 'already_metric'}

    min_lon, min_lat, max_lon, max_lat = extent
    zone_min = _utm_zone(min_lon)
    zone_max = _utm_zone(max_lon)
    same_hemisphere = (min_lat >= 0) == (max_lat >= 0)

    if zone_min == zone_max and same_hemisphere:
        epsg = (32600 if min_lat >= 0 else 32700) + zone_min
        crs = QgsCoordinateReferenceSystem.fromEpsgId(epsg)
        if crs.isValid():
            return crs, {'code': 'utm', 'zone': zone_min, 'epsg': epsg}
        # fall through to Albers if the UTM EPSG is somehow unavailable

    crs = _brazil_albers()
    if crs.isValid():
        return crs, {'code': 'albers', 'epsg': BRAZIL_ALBERS_EPSG}

    return None, {'code': 'no_metric_crs'}


# --- Delaunay network -------------------------------------------------------

def _as_layer(processing_output):
    """Normalise a Processing OUTPUT into a QgsVectorLayer."""
    if isinstance(processing_output, QgsVectorLayer):
        return processing_output
    # Some QGIS builds return a layer id/path string for TEMPORARY_OUTPUT.
    layer = QgsVectorLayer(processing_output, 'tmp', 'ogr')
    return layer


def _memory_layer(wkb_type, crs, name):
    """Memory layer with ``crs`` set explicitly (robust to authid-less CRSs).

    A proj4-built CRS (the Brazil Albers fallback) can have an empty authid(),
    which would leave a ``crs=...`` URI without a valid CRS — so set it after
    construction instead.
    """
    layer = QgsVectorLayer(wkb_type, name, 'memory')
    layer.setCrs(crs)
    return layer


def points_to_layer(points, crs, name='centroids_metric'):
    """Build an in-memory point layer from ``QgsPointXY`` points in ``crs``."""
    layer = _memory_layer('Point', crs, name)
    dp = layer.dataProvider()
    feats = []
    for p in points:
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(p)))
        feats.append(f)
    dp.addFeatures(feats)
    layer.updateExtents()
    return layer


def build_delaunay_edges(point_layer):
    """Build the unique-edge line network from a Delaunay triangulation.

    :param point_layer: ``QgsVectorLayer`` of points (centroids), already in
        the metric CRS that will be used for routing.
    :returns: ``QgsVectorLayer`` of line segments (one feature per edge).
    """
    tri = processing.run('native:delaunaytriangulation', {
        'INPUT': point_layer, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    lines = processing.run('native:polygonstolines', {
        'INPUT': tri, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    segments = processing.run('native:explodelines', {
        'INPUT': lines, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    # Interior edges are shared by two triangles, so they appear twice; drop
    # the duplicates so the graph stays lean. GEOS equality is direction-
    # independent, so A->B and B->A collapse to one edge.
    deduped = processing.run('native:deleteduplicategeometries', {
        'INPUT': segments, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    return _as_layer(deduped)


# --- AoN allocation ---------------------------------------------------------

def allocate_aon(edges_layer, centroid_points, od_pairs, metric_crs):
    """Run All-or-Nothing allocation over the Delaunay graph.

    :param edges_layer: line ``QgsVectorLayer`` (Delaunay edges), in
        ``metric_crs``.
    :param centroid_points: ``list[QgsPointXY]`` — one per zone, in
        ``metric_crs``; index is the zone index referenced by ``od_pairs``.
    :param od_pairs: ``list[(o_idx, d_idx, flow)]`` with indices into
        ``centroid_points``.
    :param metric_crs: ``QgsCoordinateReferenceSystem`` (metric) for the graph.
    :returns: (edge_flows, stats) where ``edge_flows`` is a list of
        ``(p1, p2, flow_ab, flow_ba)`` per undirected edge — ``p1``/``p2`` are
        the segment endpoints A/B (lower/higher vertex id) and the geometry
        runs ``p1 -> p2``; ``flow_ab`` is the volume travelling p1->p2,
        ``flow_ba`` the volume travelling p2->p1. ``stats`` is a dict with
        ``allocated``, ``unreachable`` and ``skipped`` counts.
    """
    director = QgsVectorLayerDirector(
        edges_layer, -1, '', '', '', QgsVectorLayerDirector.DirectionBoth)
    director.addStrategy(QgsNetworkDistanceStrategy())  # cost = edge length

    builder = QgsGraphBuilder(metric_crs)
    tied_points = director.makeGraph(builder, centroid_points)
    graph = builder.graph()

    # Accumulate by undirected vertex pair so the two directed edges of an
    # undirected pair {u, v} are never double-counted (Section 6 note). For
    # each pair we keep both directions: [flow A->B (lo->hi), flow B->A].
    flow_by_pair = {}          # (lo, hi) -> [ab, ba]
    stats = {'allocated': 0, 'unreachable': 0, 'skipped': 0}

    # Group OD pairs by origin so Dijkstra runs once per distinct origin
    # instead of once per pair.
    by_origin = {}
    for o_idx, d_idx, flow in od_pairs:
        if o_idx == d_idx or o_idx is None or d_idx is None:
            stats['skipped'] += 1
            continue
        by_origin.setdefault(o_idx, []).append((d_idx, flow))

    for o_idx, dests in by_origin.items():
        start = graph.findVertex(tied_points[o_idx])
        if start == -1:
            stats['skipped'] += len(dests)
            continue
        tree, _costs = QgsGraphAnalyzer.dijkstra(graph, start, 0)

        for d_idx, flow in dests:
            end = graph.findVertex(tied_points[d_idx])
            if end == -1 or end >= len(tree) or tree[end] == -1:
                stats['unreachable'] += 1
                continue
            # Walk the shortest-path tree from destination back to origin,
            # adding the flow to every edge on the way (the whole AoN). The
            # directed edge's fromVertex -> toVertex is the real travel
            # direction, so we know which side of the segment to credit.
            v = end
            f = float(flow)
            while v != start:
                edge = graph.edge(tree[v])
                a, b = edge.fromVertex(), edge.toVertex()  # travel a -> b
                if a <= b:
                    key, forward = (a, b), True   # travelling lo -> hi
                else:
                    key, forward = (b, a), False  # travelling hi -> lo
                pair = flow_by_pair.setdefault(key, [0.0, 0.0])
                pair[0 if forward else 1] += f
                v = a
            stats['allocated'] += 1

    edge_flows = []
    for (lo, hi), (ab, ba) in flow_by_pair.items():
        p1 = graph.vertex(lo).point()
        p2 = graph.vertex(hi).point()
        edge_flows.append((p1, p2, ab, ba))
    return edge_flows, stats


def edge_flows_to_layer(edge_flows, crs, directional=False, name='aon_flows'):
    """Materialise ``edge_flows`` into a memory line layer.

    Always writes a ``flow`` field with the total (both directions), so the
    proportional-width styling works in either mode. When ``directional`` is
    True it also writes ``flow_ab`` (volume along the segment's A->B
    orientation, i.e. p1->p2) and ``flow_ba`` (the reverse, p2->p1). AB/BA is
    the conventional link-direction naming and avoids reading these as the
    matrix's origin/destination.
    """
    from qgis.core import QgsField
    from qgis.PyQt.QtCore import QVariant

    out = _memory_layer('LineString', crs, name)
    dp = out.dataProvider()
    fields = [QgsField('flow', QVariant.Double)]
    if directional:
        fields += [QgsField('flow_ab', QVariant.Double),
                   QgsField('flow_ba', QVariant.Double)]
    dp.addAttributes(fields)
    out.updateFields()

    feats = []
    for p1, p2, ab, ba in edge_flows:
        f = QgsFeature(out.fields())
        f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(p1), QgsPointXY(p2)]))
        f['flow'] = float(ab + ba)
        if directional:
            f['flow_ab'] = float(ab)
            f['flow_ba'] = float(ba)
        feats.append(f)
    dp.addFeatures(feats)
    out.updateExtents()
    return out
