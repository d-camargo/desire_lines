# coding=utf-8
"""Testes de regressão pela porta do painel (run_assignment) para o caso de nós próximos e Sioux Falls (D5)."""

import math
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QVariant
try:
    from qgis.PyQt.QtCore import QMetaType
except ImportError:
    QMetaType = None

from desire_lines.traffic.network import Arc, CONNECTOR_LINK_ID
from desire_lines.traffic_panel import TrafficAssignmentPanel

from test.close_nodes import (
    CENTROIDS,
    EXPECTED_ANCHORS,
    EXPECTED_CONNECTOR_LENGTHS,
    LINKS,
    NODES,
    OD_PAIRS,
    _create_field,
    assert_only_network,
    centroid_layer,
    od_layer,
    road_layer,
)
from test.sioux_falls import (
    init_processing,
    load_links,
    load_nodes,
    od_all_pairs,
    road_layer as sioux_falls_road_layer,
)
from test.utilities import get_qgis_app

get_qgis_app()


def _sioux_falls_centroids_layer():
    """Cria uma camada Point em memória EPSG:4326 com os 24 nós de Sioux Falls."""
    layer = QgsVectorLayer('Point?crs=EPSG:4326', 'sioux_falls_centroids', 'memory')
    dp = layer.dataProvider()
    dp.addAttributes([_create_field('zone', 'int')])
    layer.updateFields()

    nodes = load_nodes()
    features = []
    for zid, (x, y) in nodes.items():
        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        feat['zone'] = zid
        features.append(feat)

    dp.addFeatures(features)
    layer.updateExtents()
    return layer


def _sioux_falls_od_layer():
    """Cria uma camada de tabela sem geometria com os 552 pares OD de Sioux Falls."""
    layer = QgsVectorLayer('none', 'sioux_falls_od', 'memory')
    dp = layer.dataProvider()
    dp.addAttributes([
        _create_field('orig', 'int'),
        _create_field('dest', 'int'),
        _create_field('trips', 'double'),
    ])
    layer.updateFields()

    features = []
    for orig, dest, trips in od_all_pairs(demand=1.0):
        feat = QgsFeature(layer.fields())
        feat['orig'] = orig
        feat['dest'] = dest
        feat['trips'] = trips
        features.append(feat)

    dp.addFeatures(features)
    return layer


class TestCloseNodesRegression(unittest.TestCase):
    """Regressão de alocação ponta a ponta pela porta do painel (run_assignment)."""

    def setUp(self):
        """Inicializa o Processing e listas de limpeza."""
        init_processing()
        self._tmpdirs = []
        self._layers_to_remove = []

    def tearDown(self):
        """Remove todas as camadas e limpa diretórios temporários."""
        for lyr in self._layers_to_remove:
            if lyr and lyr.id():
                QgsProject.instance().removeMapLayer(lyr.id())
        QgsProject.instance().removeAllMapLayers()
        for td in self._tmpdirs:
            td.cleanup()

    def _run_assignment_through_panel(
        self,
        road_lyr,
        centroid_lyr,
        od_lyr,
        method_idx=0,
        max_iter=20,
        max_dist=5000.0,
        id_field='id',
        zone_field='zone',
        origin_field='orig',
        dest_field='dest',
        value_field='trips',
    ):
        """Helper comum: registra camadas, configura o painel, dubla o iface e executa run_assignment."""
        QgsProject.instance().addMapLayers([road_lyr, centroid_lyr, od_lyr])
        self._layers_to_remove.extend([road_lyr, centroid_lyr, od_lyr])

        panel = TrafficAssignmentPanel(None)
        panel.taNetFromLayer.setChecked(True)
        panel.taNetworkCombo.setLayer(road_lyr)
        panel.taCentroidsCombo.setLayer(centroid_lyr)
        panel.taMatrixCombo.setLayer(od_lyr)

        panel.taIdField.setField(id_field)
        panel.taZoneIdField.setField(zone_field)
        panel.taOriginField.setField(origin_field)
        panel.taDestField.setField(dest_field)
        panel.taValueField.setField(value_field)

        panel.taMethod.setCurrentIndex(method_idx)
        if method_idx == 1:
            panel.taMaxIter.setValue(max_iter)
        panel.taMaxDist.setValue(max_dist)

        tmpdir = tempfile.TemporaryDirectory()
        self._tmpdirs.append(tmpdir)
        out_gpkg = os.path.join(tmpdir.name, 'assignment_output.gpkg')
        panel.taOutputFile.setFilePath(out_gpkg)

        mock_iface = MagicMock()
        with patch('desire_lines.traffic_panel.iface', mock_iface), \
             patch('desire_lines.ui_common.iface', mock_iface):
            panel.run_assignment()

        table = 'alocacao_aon' if method_idx == 0 else 'alocacao_msa'
        out_layer = QgsVectorLayer(f"{out_gpkg}|layername={table}", table, 'ogr')
        self.assertTrue(out_layer.isValid(), f"Camada GeoPackage {table} não é válida")
        return out_layer, panel

    def _assert_diego_case_results(self, out_layer, panel):
        """Validações comuns de asserção geométrica, âncoras, tipos e volumes do caso do Diego."""
        # 1. Asserção de que só há malha original/dividida (sem conectores)
        assert_only_network(out_layer, LINKS)

        # 2. Âncoras registradas no painel
        self.assertEqual(panel.traffic_anchors, EXPECTED_ANCHORS)

        # 3. Contagem por tipo e por link
        features = list(out_layer.getFeatures())
        self.assertEqual(len(features), 18)

        divididos = [f for f in features if f['tipo'] == 'link_dividido']
        links = [f for f in features if f['tipo'] == 'link']
        conectores = [f for f in features if f['tipo'] == 'conector']

        self.assertEqual(len(divididos), 12)  # L1 (4), L2 (4), L4 (4)
        self.assertEqual(len(links), 6)        # L3 (2), L5 (2), L6 (2)
        self.assertEqual(len(conectores), 0)

        # Verifica 2 pedaços por link dividido e sentido (4 feições por link dividido)
        for lid in ('L1', 'L2', 'L4'):
            feats_lid = [f for f in divididos if f['link_id'] == lid]
            self.assertEqual(len(feats_lid), 4, f"Link {lid} deve ter 4 feições divididas")
            fw_feats = [f for f in feats_lid if f['sentido'] == 'fw']
            bw_feats = [f for f in feats_lid if f['sentido'] == 'bw']
            self.assertEqual(len(fw_feats), 2, f"Link {lid} deve ter 2 pedaços fw")
            self.assertEqual(len(bw_feats), 2, f"Link {lid} deve ter 2 pedaços bw")

        # Links intactos: 2 feições (1 fw, 1 bw)
        for lid in ('L3', 'L5', 'L6'):
            feats_lid = [f for f in links if f['link_id'] == lid]
            self.assertEqual(len(feats_lid), 2, f"Link {lid} deve ter 2 feições")
            self.assertEqual(sorted([f['sentido'] for f in feats_lid]), ['bw', 'fw'])

        # 4. Volumes do D5
        # L1: pedaço leste (P->B, x em [5000, 10000]) tem volume 100 fw; pedaço oeste tem volume 0
        l1_east_fw = [f for f in divididos if f['link_id'] == 'L1' and f['sentido'] == 'fw'
                      and f.geometry().boundingBox().xMinimum() >= 4999.0]
        self.assertEqual(len(l1_east_fw), 1)
        self.assertAlmostEqual(l1_east_fw[0]['volume'], 100.0)

        l1_other = [f for f in divididos if f['link_id'] == 'L1' and f is not l1_east_fw[0]]
        for f in l1_other:
            self.assertAlmostEqual(f['volume'], 0.0, msg=f"L1 outro {f['arc_id']} deve ter volume 0")

        # L5: volume 100 no sentido fw (B->U), 0 no sentido bw
        l5_fw = [f for f in links if f['link_id'] == 'L5' and f['sentido'] == 'fw']
        l5_bw = [f for f in links if f['link_id'] == 'L5' and f['sentido'] == 'bw']
        self.assertEqual(len(l5_fw), 1)
        self.assertEqual(len(l5_bw), 1)
        self.assertAlmostEqual(l5_fw[0]['volume'], 100.0)
        self.assertAlmostEqual(l5_bw[0]['volume'], 0.0)

        # L4: pedaço leste (U->Q, x em [7500, 10000]) tem volume 100 bw
        #     pedaço oeste (T->Q, x em [5000, 7500]) tem volume 50 fw
        l4_east_bw = [f for f in divididos if f['link_id'] == 'L4' and f['sentido'] == 'bw'
                      and f.geometry().boundingBox().xMinimum() >= 7499.0]
        self.assertEqual(len(l4_east_bw), 1)
        self.assertAlmostEqual(l4_east_bw[0]['volume'], 100.0)

        l4_west_fw = [f for f in divididos if f['link_id'] == 'L4' and f['sentido'] == 'fw'
                      and f.geometry().boundingBox().xMaximum() <= 7501.0]
        self.assertEqual(len(l4_west_fw), 1)
        self.assertAlmostEqual(l4_west_fw[0]['volume'], 50.0)

        l4_other = [f for f in divididos if f['link_id'] == 'L4' and f not in (l4_east_bw[0], l4_west_fw[0])]
        for f in l4_other:
            self.assertAlmostEqual(f['volume'], 0.0, msg=f"L4 outro {f['arc_id']} deve ter volume 0")

        # L2: pedaço superior (R->T, y em [320, 5000]) tem volume 50 fw
        #     pedaço inferior (N1->R, y em [300, 320]) tem volume 0
        l2_sup_fw = [f for f in divididos if f['link_id'] == 'L2' and f['sentido'] == 'fw'
                     and f.geometry().boundingBox().yMinimum() >= 319.0]
        self.assertEqual(len(l2_sup_fw), 1)
        self.assertAlmostEqual(l2_sup_fw[0]['volume'], 50.0)

        l2_other = [f for f in divididos if f['link_id'] == 'L2' and f is not l2_sup_fw[0]]
        for f in l2_other:
            self.assertAlmostEqual(f['volume'], 0.0, msg=f"L2 outro {f['arc_id']} deve ter volume 0")

        # L3 e L6: volume 0 em ambos os sentidos
        for lid in ('L3', 'L6'):
            for f in [x for x in links if x['link_id'] == lid]:
                self.assertAlmostEqual(f['volume'], 0.0, msg=f"Link {lid} {f['sentido']} deve ter volume 0")

        # 5. link_id com campo String (os ids 'L1'.. são texto: fallback do D3)
        field = out_layer.fields().field('link_id')
        expected_types = [QVariant.String]
        if hasattr(QMetaType, 'Type') and hasattr(QMetaType.Type, 'QString'):
            expected_types.append(QMetaType.Type.QString)
        self.assertIn(field.type(), expected_types)
        for f in features:
            self.assertIsInstance(f['link_id'], str)
            self.assertTrue(f['link_id'].startswith('L'))

    def test_close_nodes_aon(self):
        """Caso do Diego em AoN pela porta do painel (D5)."""
        r_lyr = road_layer()
        c_lyr = centroid_layer()
        m_lyr = od_layer()
        out_layer, panel = self._run_assignment_through_panel(
            r_lyr, c_lyr, m_lyr, method_idx=0
        )
        self._assert_diego_case_results(out_layer, panel)

    def test_close_nodes_msa(self):
        """Caso do Diego em MSA com taMaxIter=20 pela porta do painel (D5)."""
        r_lyr = road_layer()
        c_lyr = centroid_layer()
        m_lyr = od_layer()
        out_layer, panel = self._run_assignment_through_panel(
            r_lyr, c_lyr, m_lyr, method_idx=1, max_iter=20
        )
        self._assert_diego_case_results(out_layer, panel)

    def _assert_sioux_falls_results(self, out_layer, panel):
        """Validações comuns para a fixture Sioux Falls em EPSG:4326 pela porta do painel (D5)."""
        features = list(out_layer.getFeatures())
        divididos = [f for f in features if f['tipo'] == 'link_dividido']
        highway_links = [f for f in features if f['tipo'] == 'link']
        conectores = [f for f in features if f['tipo'] == 'conector']

        # Nenhum link_dividido
        self.assertEqual(len(divididos), 0)
        # 152 links
        self.assertEqual(len(highway_links), 152)
        # 0 conectores
        self.assertEqual(len(conectores), 0)

        # Transforma os nós de Sioux Falls para o CRS de trabalho do painel
        crs_src = QgsCoordinateReferenceSystem('EPSG:4326')
        crs_dst = panel.traffic_crs
        transform = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())

        nodes_work = {}
        for nid, (x, y) in load_nodes().items():
            pt = transform.transform(QgsPointXY(x, y))
            nodes_work[nid] = (pt.x(), pt.y())

        fixture_links = load_links()
        fixture_pairs = set(tuple(sorted((u, v))) for u, v in fixture_links)
        self.assertEqual(len(fixture_pairs), 38)

        def match_node(pt, tol=2.0):
            for nid, (nx, ny) in nodes_work.items():
                if math.hypot(pt[0] - nx, pt[1] - ny) <= tol:
                    return nid
            return None

        # Confere que os 152 links correspondem exatamente aos 38 pares originais
        pairs_in_layer = set()
        for feat in highway_links:
            pts = feat.geometry().asPolyline()
            u = match_node((pts[0].x(), pts[0].y()))
            v = match_node((pts[-1].x(), pts[-1].y()))
            self.assertIsNotNone(u, f"Vértice inicial {pts[0]} não corresponde a nó de Sioux Falls")
            self.assertIsNotNone(v, f"Vértice final {pts[-1]} não corresponde a nó de Sioux Falls")
            self.assertNotEqual(u, v)
            pairs_in_layer.add(tuple(sorted((u, v))))

        self.assertEqual(pairs_in_layer, fixture_pairs)
        self.assertEqual(len(pairs_in_layer), 38)

    def test_sioux_falls_aon_panel(self):
        """Sioux Falls em EPSG:4326 em AoN pela porta do painel (D5)."""
        r_lyr = sioux_falls_road_layer('EPSG:4326')
        c_lyr = _sioux_falls_centroids_layer()
        m_lyr = _sioux_falls_od_layer()
        out_layer, panel = self._run_assignment_through_panel(
            r_lyr, c_lyr, m_lyr, method_idx=0, id_field='id'
        )
        self._assert_sioux_falls_results(out_layer, panel)

    def test_sioux_falls_msa_panel(self):
        """Sioux Falls em EPSG:4326 em MSA com taMaxIter=20 pela porta do painel (D5)."""
        r_lyr = sioux_falls_road_layer('EPSG:4326')
        c_lyr = _sioux_falls_centroids_layer()
        m_lyr = _sioux_falls_od_layer()
        out_layer, panel = self._run_assignment_through_panel(
            r_lyr, c_lyr, m_lyr, method_idx=1, max_iter=20, id_field='id'
        )
        self._assert_sioux_falls_results(out_layer, panel)

    def test_regression_nearest_node_fails_diego_case(self):
        """Confere que a ancoragem por nó mais próximo (lógica antiga) falha no caso do Diego (D5).

        Com a ancoragem no nó mais próximo:
        - A zona 1 ancora em N1 (5000, 300) em vez de (5000, 0) sobre L1;
        - O volume no pedaço inferior de L2 (N1->R) vira 150 (ou 100) em vez de 0;
        - L1 leste fica com volume 0 em vez de 100.
        """
        def old_anchor_centroids(arcs, centroids, max_dist_m, precision=3):
            nodes = []
            seen = set()
            for arc in arcs:
                if getattr(arc, 'scope', None) == CONNECTOR_LINK_ID:
                    continue
                for node in (arc.from_node, arc.to_node):
                    if node not in seen:
                        seen.add(node)
                        nodes.append(node)

            zone_node = {}
            report = {
                'anchors': {}, 'unconnected': [], 'fallback': [], 'far': [],
                'shared_node': [], 'shared_link': {},
            }
            connector_arcs = []
            for zone_id, centroid in enumerate(centroids):
                cx, cy = centroid
                best_node = None
                best_d = float('inf')
                for node in nodes:
                    d = math.hypot(cx - node[0], cy - node[1])
                    if d < best_d:
                        best_d = d
                        best_node = node
                zone_node[zone_id] = (CONNECTOR_LINK_ID, zone_id)
                report['anchors'][zone_id] = best_node
                connector_arcs.append(Arc(
                    arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'fw'),
                    link_id=CONNECTOR_LINK_ID,
                    from_node=(CONNECTOR_LINK_ID, zone_id),
                    to_node=best_node,
                    length=best_d,
                    t0=0.01,
                    capacity=99999.0,
                    scope=CONNECTOR_LINK_ID,
                    params={},
                    sources={},
                    geometry=[(cx, cy), best_node],
                    forward=True,
                ))
                connector_arcs.append(Arc(
                    arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'bw'),
                    link_id=CONNECTOR_LINK_ID,
                    from_node=best_node,
                    to_node=(CONNECTOR_LINK_ID, zone_id),
                    length=best_d,
                    t0=0.01,
                    capacity=99999.0,
                    scope=CONNECTOR_LINK_ID,
                    params={},
                    sources={},
                    geometry=[best_node, (cx, cy)],
                    forward=False,
                ))
            return list(arcs), connector_arcs, zone_node, report

        r_lyr = road_layer()
        c_lyr = centroid_layer()
        m_lyr = od_layer()

        with patch('desire_lines.traffic.network.anchor_centroids', side_effect=old_anchor_centroids):
            out_layer, panel = self._run_assignment_through_panel(
                r_lyr, c_lyr, m_lyr, method_idx=0
            )

        # A zona 1 ancora em N1(5000, 300) em vez de (5000, 0)
        self.assertEqual(panel.traffic_anchors[1], (5000.0, 300.0))
        self.assertNotEqual(panel.traffic_anchors[1], EXPECTED_ANCHORS[1])

        # L1 não foi dividido e seu volume é 0.0 em vez de 100.0
        l1_feats = [f for f in out_layer.getFeatures() if f['link_id'] == 'L1']
        self.assertEqual(len(l1_feats), 2)  # intacto
        self.assertTrue(all(f['volume'] == 0.0 for f in l1_feats))

        # L2 carrega o tráfego que deveria estar em L1
        l2_fw = [f for f in out_layer.getFeatures() if f['link_id'] == 'L2' and f['sentido'] == 'fw'][0]
        self.assertEqual(l2_fw['volume'], 150.0)


if __name__ == '__main__':
    unittest.main()
