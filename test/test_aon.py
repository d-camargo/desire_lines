# coding=utf-8
"""Tests for the All-or-Nothing (AoN) core (aon.py).

Run inside the QGIS test harness (it needs a QGIS application for the graph
and CRS classes). See AoN_delaunay_desire_lines.md, Section 7.3.
"""
import unittest

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
)

import aon

from .utilities import get_qgis_app
QGIS_APP = get_qgis_app()


class PickMetricCrsTest(unittest.TestCase):
    """pick_metric_crs chooses UTM / Albers / passthrough per the rules."""

    def test_already_metric_is_passthrough(self):
        src = QgsCoordinateReferenceSystem.fromEpsgId(32723)
        crs, reason = aon.pick_metric_crs(src, (200000, 7700000, 250000, 7800000))
        self.assertEqual(crs.authid(), 'EPSG:32723')
        self.assertEqual(reason['code'], 'already_metric')

    def test_geographic_single_zone_gets_utm(self):
        src = QgsCoordinateReferenceSystem.fromEpsgId(4674)  # SIRGAS 2000
        # A small area in Minas Gerais — well inside UTM zone 23S.
        crs, reason = aon.pick_metric_crs(src, (-44.0, -20.0, -43.5, -19.5))
        self.assertEqual(crs.authid(), 'EPSG:32723')
        self.assertEqual(reason['code'], 'utm')
        self.assertEqual(reason.get('zone'), 23)
        self.assertEqual(reason.get('epsg'), 32723)

    def test_geographic_multi_zone_gets_albers(self):
        src = QgsCoordinateReferenceSystem.fromEpsgId(4674)
        # West-to-east span crossing more than one UTM zone.
        crs, reason = aon.pick_metric_crs(src, (-53.0, -22.0, -40.0, -2.0))
        self.assertTrue(crs.isValid())
        self.assertEqual(reason['code'], 'albers')
        self.assertEqual(reason.get('epsg'), 10857)


class AllocateAonTest(unittest.TestCase):
    """allocate_aon accumulates the whole OD flow on the least-cost path."""

    def _edges(self, crs_authid, segments):
        layer = QgsVectorLayer(
            'LineString?crs={}'.format(crs_authid), 'edges', 'memory')
        dp = layer.dataProvider()
        feats = []
        for (x1, y1), (x2, y2) in segments:
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPolylineXY(
                [QgsPointXY(x1, y1), QgsPointXY(x2, y2)]))
            feats.append(f)
        dp.addFeatures(feats)
        layer.updateExtents()
        return layer

    def test_flow_follows_shortest_path(self):
        crs = QgsCoordinateReferenceSystem.fromEpsgId(32723)
        # A simple path A(0,0) - B(10,0) - C(20,0).
        edges = self._edges('EPSG:32723', [((0, 0), (10, 0)),
                                           ((10, 0), (20, 0))])
        points = [QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(20, 0)]
        od_pairs = [(0, 2, 5.0)]  # A -> C, flow 5

        edge_flows, stats = aon.allocate_aon(edges, points, od_pairs, crs)

        self.assertEqual(stats['allocated'], 1)
        self.assertEqual(stats['unreachable'], 0)
        # Both edges of the A-B-C path carry the whole flow (one direction).
        self.assertEqual(len(edge_flows), 2)
        for _p1, _p2, ab, ba in edge_flows:
            self.assertAlmostEqual(ab + ba, 5.0)

    def test_directions_are_kept_separate(self):
        crs = QgsCoordinateReferenceSystem.fromEpsgId(32723)
        edges = self._edges('EPSG:32723', [((0, 0), (10, 0)),
                                           ((10, 0), (20, 0))])
        points = [QgsPointXY(0, 0), QgsPointXY(10, 0), QgsPointXY(20, 0)]
        # 5 units A->C and 3 units C->A over the same corridor.
        od_pairs = [(0, 2, 5.0), (2, 0, 3.0)]

        edge_flows, _stats = aon.allocate_aon(edges, points, od_pairs, crs)
        # Per segment the two senses stay separate: 5 one way, 3 the other.
        # (Which one lands in ab vs ba depends on the segment's vertex-id
        # orientation, so compare orientation-independently.)
        for _p1, _p2, ab, ba in edge_flows:
            self.assertAlmostEqual(min(ab, ba), 3.0)
            self.assertAlmostEqual(max(ab, ba), 5.0)

    def test_unreachable_is_counted(self):
        crs = QgsCoordinateReferenceSystem.fromEpsgId(32723)
        # Two disconnected components: A-B and C-D.
        edges = self._edges('EPSG:32723', [((0, 0), (10, 0)),
                                           ((100, 0), (110, 0))])
        points = [QgsPointXY(0, 0), QgsPointXY(10, 0),
                  QgsPointXY(100, 0), QgsPointXY(110, 0)]
        od_pairs = [(0, 3, 7.0)]  # A -> D, across the gap

        _edge_flows, stats = aon.allocate_aon(edges, points, od_pairs, crs)
        self.assertEqual(stats['allocated'], 0)
        self.assertEqual(stats['unreachable'], 1)


if __name__ == '__main__':
    suite = unittest.makeSuite(PickMetricCrsTest)
    suite.addTests(unittest.makeSuite(AllocateAonTest))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
