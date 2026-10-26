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
from unittest.mock import patch, MagicMock

from qgis.PyQt.QtWidgets import QDialogButtonBox, QDialog, QScrollArea, QApplication

from desire_lines.traffic_panel import TrafficAssignmentPanel
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


class TrafficAssignmentPanelTest(unittest.TestCase):
    """Test traffic panel works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = TrafficAssignmentPanel(None)
    def test_params_rows_cover_the_catalogue(self):
        """Every D7 parameter gets a global editor and a field-override combo."""
        widgets = self.dialog._traffic_param_widgets
        self.assertEqual(set(widgets), set(traffic_params.PARAMS))

    def test_all_tab_pages_are_resizable_scroll_areas(self):
        """Both pages of taTabs are (or contain) a QScrollArea with widgetResizable (D4)."""
        tabs = self.dialog.taTabs
        self.assertEqual(tabs.count(), 2)
        for i in range(tabs.count()):
            page = tabs.widget(i)
            scroll = page if isinstance(page, QScrollArea) else page.findChild(QScrollArea)
            self.assertIsNotNone(scroll)
            self.assertIsInstance(scroll, QScrollArea)
            self.assertTrue(scroll.widgetResizable())

    def test_hcm_params_group_tab_placement(self):
        """The HCM Parameters page contains taParamsGroup and Allocation does not (D3)."""
        tabs = self.dialog.taTabs
        alloc_page = None
        params_page = None
        for i in range(tabs.count()):
            title = tabs.tabText(i)
            if 'Alocação' in title:
                alloc_page = tabs.widget(i)
            elif 'Parâmetros' in title:
                params_page = tabs.widget(i)

        self.assertIsNotNone(alloc_page)
        self.assertIsNotNone(params_page)

        params_group = self.dialog.taParamsGroup
        self.assertTrue(params_page.isAncestorOf(params_group))
        self.assertFalse(alloc_page.isAncestorOf(params_group))

    def test_scroll_area_overflow_and_last_param_reachable(self):
        """When resized small, scroll inner height exceeds viewport and vbar max > 0."""
        self.dialog.resize(400, 300)
        self.dialog.show()
        self.dialog.taTabs.setCurrentIndex(1)
        QApplication.processEvents()

        scroll = self.dialog.tabParamsScroll
        inner = scroll.widget()
        self.assertIsNotNone(inner)

        visible_height = scroll.viewport().height()
        self.assertGreater(inner.sizeHint().height(), visible_height)

        last_param_key = list(traffic_params.PARAMS)[-1]
        self.assertIn(last_param_key, self.dialog._traffic_param_widgets)
        editor, field_combo = self.dialog._traffic_param_widgets[last_param_key]
        self.assertIsNotNone(editor)
        self.assertIsNotNone(field_combo)

        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)

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

    def test_output_path_strips_layername(self):
        """_output_path strips pipe-layername suffix from file path (D6)."""
        self.dialog.taOutputFile.setFilePath('/tmp/x/out.gpkg|layername=alocacao')
        self.assertEqual(self.dialog._output_path(), '/tmp/x/out.gpkg')

    def test_output_path_strips_layername_without_extension(self):
        """_output_path strips pipe-layername and appends .gpkg if missing (D6)."""
        self.dialog.taOutputFile.setFilePath('/tmp/x/out|layername=a')
        self.assertEqual(self.dialog._output_path(), '/tmp/x/out.gpkg')

    def test_publish_traffic_layer_defaults_table_to_mem_name(self):
        """_publish_traffic_layer with table=None passes mem.name() to _write_layer_to_gpkg (D6)."""
        self.dialog._write_layer_to_gpkg = MagicMock(return_value=None)
        self.dialog._publish_traffic_layer(
            arcs=[], flows=[], stats={'metodo': 'msa'}, crs=None, table=None)
        self.dialog._write_layer_to_gpkg.assert_called_once()
        self.assertEqual(
            self.dialog._write_layer_to_gpkg.call_args[0][1], 'alocacao_msa')

    def test_panel_has_no_clip_to_centroids(self):
        """The panel no longer has taClipToCentroids (D5)."""
        self.assertFalse(hasattr(self.dialog, 'taClipToCentroids'))

    def test_recorte_tipo_has_six_items_with_d5_data(self):
        """taRecorteTipo has 6 items with D5 data."""
        combo = self.dialog.taRecorteTipo
        self.assertEqual(combo.count(), 6)
        datas = [combo.itemData(i) for i in range(combo.count())]
        self.assertEqual(datas, ['centroides', 'uf', 'rm', 'micro', 'meso', 'macsaud'])

    @patch('desire_lines.traffic_panel.gisbr_bridge.listar_recortes')
    def test_reload_recortes_populates_ta_recorte(self, mock_listar):
        """With listar_recortes mocked, choosing 'rm' with UF 'MG' populates taRecorte."""
        mock_listar.return_value = [('04501', 'Grande BH'), ('04502', 'Vale do Aço')]
        self.dialog.taUf.setText('MG')
        rm_idx = self.dialog.taRecorteTipo.findData('rm')
        self.dialog.taRecorteTipo.setCurrentIndex(rm_idx)

        mock_listar.assert_called_with('rm', 'MG')
        self.assertEqual(self.dialog.taRecorte.count(), 2)
        self.assertEqual(self.dialog.taRecorte.itemData(0), '04501')
        self.assertEqual(self.dialog.taRecorte.itemText(0), 'Grande BH')

    @patch('desire_lines.traffic_panel.gisbr_bridge.extensao_recorte')
    def test_gisbr_bbox_decides_bbox_for_uf_and_micro(self, mock_extensao):
        """_gisbr_bbox returns None for 'uf' and the extensao_recorte tuple for 'micro'."""
        uf_idx = self.dialog.taRecorteTipo.findData('uf')
        self.dialog.taRecorteTipo.setCurrentIndex(uf_idx)
        self.assertIsNone(self.dialog._gisbr_bbox(CENTROIDS, 50.0))

        mock_extensao.return_value = (100.0, 200.0, 300.0, 400.0)
        micro_idx = self.dialog.taRecorteTipo.findData('micro')
        self.dialog.taRecorteTipo.setCurrentIndex(micro_idx)
        self.dialog.taRecorte.clear()
        self.dialog.taRecorte.addItem('Microrregião de BH', '3101')
        self.dialog.taRecorte.setCurrentIndex(0)

        bbox = self.dialog._gisbr_bbox(CENTROIDS, 50.0)
        mock_extensao.assert_called_with('micro', '3101')
        self.assertEqual(bbox, (100.0, 200.0, 300.0, 400.0))

    def test_tab_state_regional_recorte_controls_and_readiness(self):
        """taRecorte is enabled only with GisBR + regional type, and network_ready requires currentData."""
        with patch('desire_lines.traffic.gisbr_bridge.is_available', return_value=True):
            self.dialog.taNetFromGisbr.setChecked(True)
            self.dialog.taUf.setText('MG')

            # Non-regional (uf): taRecorte disabled, network is ready
            self.dialog.taRecorteTipo.setCurrentIndex(self.dialog.taRecorteTipo.findData('uf'))
            self.dialog._update_traffic_tab_state()
            self.assertFalse(self.dialog.taRecorte.isEnabled())
            self.assertFalse(self.dialog.taLabelRecorte.isEnabled())
            self.assertTrue(self.dialog.taRunCapacity.isEnabled())

            # Regional (rm) with empty taRecorte: taRecorte enabled, network NOT ready
            self.dialog.taRecorte.clear()
            self.dialog.taRecorteTipo.setCurrentIndex(self.dialog.taRecorteTipo.findData('rm'))
            self.dialog._update_traffic_tab_state()
            self.assertTrue(self.dialog.taRecorte.isEnabled())
            self.assertTrue(self.dialog.taLabelRecorte.isEnabled())
            self.assertFalse(self.dialog.taRunCapacity.isEnabled())

            # Regional with item selected in taRecorte: network ready
            self.dialog.taRecorte.addItem('Grande BH', '04501')
            self.dialog.taRecorte.setCurrentIndex(0)
            self.dialog._update_traffic_tab_state()
            self.assertTrue(self.dialog.taRunCapacity.isEnabled())

    @patch('desire_lines.traffic_panel.gisbr_bridge.extensao_recorte',
           side_effect=RuntimeError('Falha ao obter recorte'))
    def test_gisbr_bbox_runtime_error_pushes_critical_message(self, mock_extensao):
        """RuntimeError in extensao_recorte produces a critical message and returns."""
        with patch('desire_lines.traffic.gisbr_bridge.is_available', return_value=True):
            self.dialog.taNetFromGisbr.setChecked(True)
            self.dialog.taUf.setText('MG')
            self.dialog.taRecorteTipo.setCurrentIndex(self.dialog.taRecorteTipo.findData('rm'))
            self.dialog.taRecorte.addItem('Grande BH', '04501')
            self.dialog.taRecorte.setCurrentIndex(0)

            self.dialog.run_capacity()
            self.assertEqual(self.dialog.last_message[0], 'critical')
            self.assertIn('Falha ao obter recorte', self.dialog.last_message[1])

    # --- D1/D4: metric working CRS ------------------------------------------

    # Sioux Falls area (UTM zone 14N): an L of two links and a centroid near
    # each end, all in EPSG:4326.
    GEO_LINES = [
        [(-96.770, 43.610), (-96.760, 43.610)],
        [(-96.760, 43.610), (-96.760, 43.620)],
    ]
    GEO_CENTROIDS = [(-96.7701, 43.6101), (-96.7601, 43.6199)]

    @staticmethod
    def _line_layer(authid, lines):
        """Memory LineString layer in ``authid`` with one feature per line."""
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer
        layer = QgsVectorLayer('LineString?crs={}'.format(authid), 'roads', 'memory')
        feats = []
        for line in lines:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPolylineXY(
                [QgsPointXY(x, y) for x, y in line]))
            feats.append(feat)
        layer.dataProvider().addFeatures(feats)
        layer.updateExtents()
        return layer

    @staticmethod
    def _to_crs(points, src, dst):
        from qgis.core import (QgsCoordinateReferenceSystem,
                               QgsCoordinateTransform, QgsPointXY, QgsProject)
        xform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(src),
                                       QgsCoordinateReferenceSystem(dst),
                                       QgsProject.instance())
        return [(p.x(), p.y()) for p in
                (xform.transform(QgsPointXY(x, y)) for x, y in points)]

    def test_geographic_layer_is_reprojected_to_utm(self):
        """A 4326 layer and 4326 centroids end up in UTM 14N, in metres (D1, D4)."""
        from qgis.core import QgsCoordinateReferenceSystem
        from test.sioux_falls import init_processing
        init_processing()
        layer = self._line_layer('EPSG:4326', self.GEO_LINES)
        with patch.object(network, 'reproject_layer',
                          wraps=network.reproject_layer) as spy:
            g, _arcs, zone_node, unconnected = self.dialog.build_traffic_network(
                road_layer=layer, centroids=self.GEO_CENTROIDS, zone_keys=[1, 2],
                max_dist_m=50.0,
                centroids_crs=QgsCoordinateReferenceSystem('EPSG:4326'))
        spy.assert_called_once()
        self.assertEqual(self.dialog.traffic_crs.authid(), 'EPSG:32614')
        self.assertIsNotNone(g)
        self.assertEqual(unconnected, [])
        expected = self._to_crs(
            [self.GEO_LINES[0][0], self.GEO_LINES[1][1]], 'EPSG:4326', 'EPSG:32614')
        for key, (ex, ey) in zip((1, 2), expected):
            x, y = zone_node[key]
            self.assertGreater(abs(x), 1000.0)      # metres, not degrees
            self.assertAlmostEqual(x, ex, delta=1.0)
            self.assertAlmostEqual(y, ey, delta=1.0)

    def test_metric_layer_is_not_reprojected(self):
        """A layer already in a projected CRS is used as is (D1)."""
        layer = self._line_layer('EPSG:32614', [
            [(700000.0, 4830000.0), (700100.0, 4830000.0)],
            [(700100.0, 4830000.0), (700100.0, 4830100.0)],
        ])
        with patch.object(network, 'reproject_layer') as mock_reproject:
            g, _arcs, zone_node, _unc = self.dialog.build_traffic_network(
                road_layer=layer, centroids=[(700000.0, 4830001.0)],
                max_dist_m=50.0)
        mock_reproject.assert_not_called()
        self.assertIsNotNone(g)
        self.assertEqual(self.dialog.traffic_crs.authid(), 'EPSG:32614')
        self.assertEqual(zone_node, {0: (700000.0, 4830000.0)})

    def test_clip_buffer_uses_centroids_in_work_crs(self):
        """With clip_buffer_m, clip_and_clean gets a bbox in the working CRS (D4)."""
        from qgis.core import QgsCoordinateReferenceSystem
        from test.sioux_falls import init_processing
        init_processing()
        layer = self._line_layer('EPSG:4326', self.GEO_LINES)
        with patch.object(network, 'clip_and_clean',
                          side_effect=lambda lyr, bbox: lyr) as mock_clip:
            self.dialog.build_traffic_network(
                road_layer=layer, centroids=self.GEO_CENTROIDS,
                max_dist_m=50.0, clip_buffer_m=100.0,
                centroids_crs=QgsCoordinateReferenceSystem('EPSG:4326'))
        mock_clip.assert_called_once()
        clipped_layer, bbox = mock_clip.call_args[0]
        self.assertEqual(clipped_layer.crs().authid(), 'EPSG:32614')
        pts = self._to_crs(self.GEO_CENTROIDS, 'EPSG:4326', 'EPSG:32614')
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        for got, want in zip(bbox, (min(xs) - 100.0, min(ys) - 100.0,
                                    max(xs) + 100.0, max(ys) + 100.0)):
            self.assertAlmostEqual(got, want, delta=0.01)



if __name__ == "__main__":
    suite = unittest.makeSuite(TrafficAssignmentPanelTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
