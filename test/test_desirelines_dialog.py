# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'dg.camargo@proton.me'
__date__ = '2024-07-13'
__copyright__ = 'Copyright 2024, Diego Camargo'

import unittest
from unittest.mock import patch

from qgis.PyQt.QtWidgets import QDialogButtonBox, QDialog

from desire_lines.desirelines_dialog import DesireLinesDialog
from desire_lines.traffic import assignment, network
from desire_lines.traffic import params as traffic_params

from .utilities import get_qgis_app
QGIS_APP = get_qgis_app()

# Two links forming an L, in a metric CRS, with a centroid near each end.
ROADS = [
    {'id': 1, 'geometry': [(0, 0), (100, 0)]},
    {'id': 2, 'geometry': [(100, 0), (100, 100)]},
]
CENTROIDS = [(0.0, 1.0), (100.0, 99.0)]


class DesireLinesDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = DesireLinesDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.DialogCode.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.DialogCode.Rejected)

    def test_fourth_tab_exists(self):
        """The 4th tab exists with the widgets step 16 asks for."""
        self.assertEqual(self.dialog.tabWidget.count(), 4)
        self.assertEqual(self.dialog.tabWidget.tabText(3), "Alocação em rodovias")
        for name in ('taNetworkCombo', 'taIdField', 'taMatrixCombo',
                     'taCentroidsCombo', 'taZoneIdField', 'taMethod',
                     'taMaxIter', 'taGapTol', 'taRunCapacity', 'taRunAssign',
                     'taGisbrWarning', 'taScopeNote', 'taParamsGroup'):
            self.assertTrue(hasattr(self.dialog, name), name)

    def test_params_rows_cover_the_catalogue(self):
        """Every D7 parameter gets a global editor and a field-override combo."""
        widgets = self.dialog._traffic_param_widgets
        self.assertEqual(set(widgets), set(traffic_params.PARAMS))

    def test_buttons_start_disabled(self):
        """With no layer selected neither action is available (step 17)."""
        self.dialog.taNetFromLayer.setChecked(True)
        self.dialog.taNetworkCombo.setLayer(None)
        self.dialog._update_traffic_tab_state()
        self.assertFalse(self.dialog.taRunCapacity.isEnabled())
        self.assertFalse(self.dialog.taRunAssign.isEnabled())

    def test_aon_disables_iteration_fields(self):
        """Switching the method combo to AoN greys out iterations/gap (D10)."""
        self.dialog.taMethod.setCurrentIndex(1)          # MSA
        self.assertEqual(self.dialog._traffic_method(), 'msa')
        self.assertTrue(self.dialog.taMaxIter.isEnabled())
        self.assertTrue(self.dialog.taGapTol.isEnabled())
        self.dialog.taMethod.setCurrentIndex(0)          # AoN
        self.assertEqual(self.dialog._traffic_method(), 'aon')
        self.assertFalse(self.dialog.taMaxIter.isEnabled())
        self.assertFalse(self.dialog.taGapTol.isEnabled())

    def test_gisbr_warning_shown_when_missing(self):
        """The GisBR warning is visible and the download option is off (D6)."""
        with patch('desire_lines.traffic.gisbr_bridge.is_available',
                   return_value=False):
            self.dialog._update_traffic_tab_state()
            self.assertTrue(self.dialog.taGisbrWarning.isVisible()
                            or not self.dialog.isVisible())
            self.assertFalse(self.dialog.taNetFromGisbr.isEnabled())
            self.assertTrue(self.dialog.taNetFromLayer.isChecked())

    def test_build_traffic_network_builds_graph(self):
        """The graph gets one arc pair per link plus one per centroid (step 18)."""
        g, arcs, zone_node, unconnected = self.dialog.build_traffic_network(
            road_layer=ROADS, centroids=CENTROIDS, max_dist_m=50.0)
        self.assertEqual(len(g.arcs), 8)   # 4 directed road arcs + 4 connectors
        self.assertEqual(len(arcs), 8)
        self.assertEqual(len(zone_node), 2)
        self.assertEqual(unconnected, [])
        for node in ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0)):
            self.assertTrue(g.has_node(node), node)

    def test_zone_keys_label_the_zone_node_map(self):
        """zone_node is keyed by the traffic id, not by the list index."""
        _g, _arcs, zone_node, _unc = self.dialog.build_traffic_network(
            road_layer=ROADS, centroids=CENTROIDS, zone_keys=[7, 9],
            max_dist_m=50.0)
        self.assertEqual(sorted(zone_node), [7, 9])

    def test_edge_case_gisbr_network_failure(self):
        """A failed GisBR download is reported, not raised (step 19)."""
        with patch('desire_lines.traffic.gisbr_bridge.fetch_road_network',
                   side_effect=RuntimeError("Connection refused")):
            g, arcs, _zn, _unc = self.dialog.build_traffic_network(
                fetch_gisbr=True)
        self.assertIsNone(g)
        self.assertEqual(arcs, [])
        self.assertEqual(self.dialog.last_message[0], 'critical')

    def test_edge_case_empty_road_network(self):
        """An empty network after clipping is reported, not raised (step 19)."""
        g, arcs, _zn, _unc = self.dialog.build_traffic_network(road_layer=[])
        self.assertIsNone(g)
        self.assertEqual(arcs, [])
        self.assertEqual(self.dialog.last_message[0], 'critical')

    def test_edge_case_invalid_capacity_drops_the_arc(self):
        """A non-positive capacity drops the arc and warns (step 19).

        It is never replaced by a stand-in value: a made-up capacity would
        surface as a real v/c and a real LOS F on what is actually missing data.
        """
        built = network.build_network(ROADS)
        built[0].capacity = 0.0
        with patch('desire_lines.traffic.network.build_network',
                   return_value=built):
            g, arcs, _zn, _unc = self.dialog.build_traffic_network(
                road_layer=ROADS, centroids=CENTROIDS, max_dist_m=50.0)
        self.assertIsNotNone(g)
        self.assertTrue(all(a.capacity > 0.0 for a in arcs))
        self.assertEqual(self.dialog.last_message[0], 'warning')

    def test_all_capacities_invalid_is_critical(self):
        """With no usable arc left the run stops with a critical message."""
        built = network.build_network(ROADS)
        for arc in built:
            arc.capacity = 0.0
        with patch('desire_lines.traffic.network.build_network',
                   return_value=built):
            g, arcs, _zn, _unc = self.dialog.build_traffic_network(
                road_layer=ROADS, centroids=CENTROIDS, max_dist_m=50.0)
        self.assertIsNone(g)
        self.assertEqual(arcs, [])
        self.assertEqual(self.dialog.last_message[0], 'critical')

    def test_edge_case_unconnected_centroids(self):
        """Centroids out of reach are reported, not raised (step 19)."""
        g, _arcs, zone_node, unconnected = self.dialog.build_traffic_network(
            road_layer=ROADS[:1], centroids=[(500.0, 500.0)], max_dist_m=10.0)
        self.assertIsNotNone(g)
        self.assertEqual(unconnected, [0])
        self.assertEqual(zone_node, {})
        self.assertEqual(self.dialog.last_message[0], 'critical')

    def test_edge_case_unmatched_od_demand(self):
        """OD rows with unknown zone ids are counted, not raised (step 19)."""
        _g, _arcs, zone_node, _unc = self.dialog.build_traffic_network(
            road_layer=ROADS, centroids=CENTROIDS, max_dist_m=50.0)
        od_pairs, unmatched = self.dialog.read_od_pairs(
            [{'origem': 999, 'destino': 888, 'fluxo': 100}], zone_node,
            origin_field='origem', dest_field='destino', value_field='fluxo')
        self.assertEqual(od_pairs, [])
        self.assertEqual(unmatched, 1)

    def test_read_od_pairs_maps_zones_to_nodes(self):
        """Matching rows become (origin node, dest node, demand) triples."""
        _g, _arcs, zone_node, _unc = self.dialog.build_traffic_network(
            road_layer=ROADS, centroids=CENTROIDS, zone_keys=[1, 2],
            max_dist_m=50.0)
        od_pairs, unmatched = self.dialog.read_od_pairs(
            [{'origem': 1, 'destino': 2, 'fluxo': 250}], zone_node,
            origin_field='origem', dest_field='destino', value_field='fluxo')
        self.assertEqual(unmatched, 0)
        self.assertEqual(od_pairs,
                         [(zone_node[1], zone_node[2], 250.0)])

    def test_both_methods_run_over_the_same_network(self):
        """AoN and MSA share the network and differ only in the result (D10)."""
        g, arcs, zone_node, _unc = self.dialog.build_traffic_network(
            road_layer=ROADS, centroids=CENTROIDS, zone_keys=[1, 2],
            max_dist_m=50.0)
        od_pairs, _ = self.dialog.read_od_pairs(
            [{'origem': 1, 'destino': 2, 'fluxo': 500}], zone_node,
            origin_field='origem', dest_field='destino', value_field='fluxo')
        for method in ('aon', 'msa'):
            flows, _hist, stats = assignment.assign(
                g, arcs, od_pairs, method=method, max_iter=5, gap_tol=0.01)
            self.assertEqual(stats['metodo'], method)
            self.assertEqual(len(flows), len(arcs))
            self.assertEqual(stats['allocated'], 1)
        self.assertIsNotNone(self.dialog._provenance_note(arcs))


if __name__ == "__main__":
    suite = unittest.makeSuite(DesireLinesDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
