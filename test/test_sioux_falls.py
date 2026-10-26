# coding=utf-8
"""Testes de sanidade da fixture Sioux Falls (D8, D9)."""

import math
import unittest
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
)
from desire_lines.traffic.network import (
    build_network,
    clip_and_clean,
    reproject_layer,
)
from desire_lines.traffic_panel import TrafficAssignmentPanel
from desire_lines.traffic import assignment, outputs
from test.sioux_falls import (
    init_processing,
    load_nodes,
    load_links,
    road_layer,
    od_all_pairs,
)


class TestSiouxFallsFixture(unittest.TestCase):
    """Verifica a integridade e sanidade da fixture Sioux Falls."""

    def test_load_nodes(self):
        """nodes.csv contém exatamente 24 nós com coordenadas lon/lat válidas."""
        nodes = load_nodes()
        self.assertEqual(len(nodes), 24)
        self.assertEqual(set(nodes.keys()), set(range(1, 25)))
        for node_id, (x, y) in nodes.items():
            self.assertIsInstance(node_id, int)
            self.assertIsInstance(x, float)
            self.assertIsInstance(y, float)
            # Longitude ~ -96.7° e Latitude ~ 43.5° (Sioux Falls, Dakota do Sul)
            self.assertGreater(x, -97.0)
            self.assertLess(x, -96.5)
            self.assertGreater(y, 43.0)
            self.assertLess(y, 44.0)

    def test_load_links(self):
        """links.csv contém 76 links direcionados e 38 pares não-ordenados."""
        links = load_links()
        self.assertEqual(len(links), 76)

        undirected_pairs = set()
        nodes = load_nodes()
        for init, term in links:
            self.assertIn(init, nodes)
            self.assertIn(term, nodes)
            self.assertNotEqual(init, term)
            undirected_pairs.add(tuple(sorted((init, term))))

        self.assertEqual(len(undirected_pairs), 38)

        # Todo link deve ter sua contraparte de volta (rede simétrica em topologia)
        directed_set = set(links)
        for init, term in links:
            self.assertIn((term, init), directed_set)

    def test_road_layer(self):
        """road_layer cria camada vetorial válida com 76 feições retas."""
        layer = road_layer()
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.featureCount(), 76)
        self.assertEqual(layer.crs().authid(), 'EPSG:4326')

        field_names = [f.name() for f in layer.fields()]
        self.assertIn('init_node', field_names)
        self.assertIn('term_node', field_names)

        nodes = load_nodes()
        for feat in layer.getFeatures():
            geom = feat.geometry()
            self.assertTrue(geom.isGeosValid())
            self.assertEqual(geom.wkbType(), 2)  # LineString

            pts = geom.asPolyline()
            self.assertEqual(len(pts), 2)

            u = feat['init_node']
            v = feat['term_node']
            self.assertIn(u, nodes)
            self.assertIn(v, nodes)

            expected_u = nodes[u]
            expected_v = nodes[v]
            self.assertAlmostEqual(pts[0].x(), expected_u[0], places=6)
            self.assertAlmostEqual(pts[0].y(), expected_u[1], places=6)
            self.assertAlmostEqual(pts[1].x(), expected_v[0], places=6)
            self.assertAlmostEqual(pts[1].y(), expected_v[1], places=6)

    def test_od_all_pairs(self):
        """od_all_pairs gera os 24x23 = 552 pares OD com demanda unitária."""
        od = od_all_pairs(demand=1.0)
        self.assertEqual(len(od), 24 * 23)
        self.assertEqual(len(od), 552)

        nodes = set(load_nodes().keys())
        seen_pairs = set()
        for o, d, flow in od:
            self.assertIn(o, nodes)
            self.assertIn(d, nodes)
            self.assertNotEqual(o, d)
            self.assertEqual(flow, 1.0)
            seen_pairs.add((o, d))

        self.assertEqual(len(seen_pairs), 552)

    def test_init_processing(self):
        """init_processing inicializa o Processing do QGIS com sucesso."""
        init_processing()
        from qgis.core import QgsApplication
        algs = QgsApplication.processingRegistry().algorithms()
        self.assertGreater(len(algs), 0)

    def test_clip_and_clean_raises_on_geographic_crs(self):
        """A fixture em EPSG:4326 levanta ValueError em clip_and_clean."""
        init_processing()
        layer = road_layer('EPSG:4326')
        ext = layer.extent()
        bbox = (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())
        with self.assertRaises(ValueError):
            clip_and_clean(layer, bbox)

    def test_reproject_layer_sioux_falls(self):
        """Fixture reprojetada para EPSG:32614 -> clip_and_clean + build_network dá 152 arcos e 0 espúrios."""
        init_processing()
        layer_4326 = road_layer('EPSG:4326')
        reprojected = reproject_layer(layer_4326, 'EPSG:32614')

        ext = reprojected.extent()
        bbox = (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())
        cleaned = clip_and_clean(reprojected, bbox)
        arcs = build_network(cleaned.getFeatures())

        self.assertEqual(len(arcs), 152)

        crs_src = QgsCoordinateReferenceSystem('EPSG:4326')
        crs_dst = QgsCoordinateReferenceSystem('EPSG:32614')
        transform = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())

        nodes_32614 = {}
        for nid, (x, y) in load_nodes().items():
            pt = transform.transform(QgsPointXY(x, y))
            nodes_32614[nid] = (pt.x(), pt.y())

        valid_pairs = set(tuple(sorted((u, v))) for u, v in load_links())
        self.assertEqual(len(valid_pairs), 38)

        def match_node(pt, tol=1.0):
            for nid, (nx, ny) in nodes_32614.items():
                if math.hypot(pt[0] - nx, pt[1] - ny) <= tol:
                    return nid
            return None

        spurious = 0
        for arc in arcs:
            u = match_node(arc.from_node, tol=1.0)
            v = match_node(arc.to_node, tol=1.0)
            pair = tuple(sorted((u, v))) if (u is not None and v is not None) else None
            if pair not in valid_pairs:
                spurious += 1

        self.assertEqual(spurious, 0)

    def _run_sioux_falls_assignment(self, method, **kwargs):
        """Executa o pipeline ponta a ponta com o painel e retorna a camada de saída e contexto."""
        init_processing()
        panel = TrafficAssignmentPanel(None)
        layer = road_layer('EPSG:4326')
        nodes_4326 = load_nodes()
        zone_keys = list(range(1, 25))
        centroids = [nodes_4326[k] for k in zone_keys]
        centroids_crs = QgsCoordinateReferenceSystem('EPSG:4326')

        g, arcs, zone_node, unconnected = panel.build_traffic_network(
            road_layer=layer,
            centroids=centroids,
            zone_keys=zone_keys,
            centroids_crs=centroids_crs,
            clip_buffer_m=5000,
        )
        self.assertEqual(unconnected, [])
        self.assertEqual(panel.traffic_crs.authid(), 'EPSG:32614')

        od_mapped = [(zone_node[o], zone_node[d], demand) for o, d, demand in od_all_pairs()]

        flows, _history, stats = assignment.assign(
            g, arcs=arcs, od_pairs=od_mapped, method=method, **kwargs
        )
        out_layer = outputs.flows_to_layer(
            arcs, flows, stats=stats, crs=panel.traffic_crs
        )
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.crs().authid(), panel.traffic_crs.authid())

        return out_layer, stats, panel, zone_node

    def _assert_d6_layer(self, out_layer, stats, panel, anchors):
        """Verifica as asserções (a)–(e) do D6 e a integridade da rede sobre a camada."""
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

        def match_node(pt, tol=1.0):
            for nid, (nx, ny) in nodes_work.items():
                if math.hypot(pt[0] - nx, pt[1] - ny) <= tol:
                    return nid
            return None

        features = list(out_layer.getFeatures())
        highway_feats = [f for f in features if f['link_id'] != 'conector']
        connector_feats = [f for f in features if f['link_id'] == 'conector']

        # (a) toda feição com link_id != 'conector' corresponde a um link de entrada e
        # suas extremidades são os dois nós desse link (tolerância 1 m, no work_crs)
        for feat in highway_feats:
            pts = feat.geometry().asPolyline()
            self.assertGreaterEqual(len(pts), 2)
            p0 = (pts[0].x(), pts[0].y())
            p1 = (pts[-1].x(), pts[-1].y())
            u = match_node(p0, tol=1.0)
            v = match_node(p1, tol=1.0)
            self.assertIsNotNone(u, f"Extremidade {p0} não corresponde a nenhum nó da fixture")
            self.assertIsNotNone(v, f"Extremidade {p1} não corresponde a nenhum nó da fixture")
            self.assertNotEqual(u, v, f"Feição de rodovia com extremidades iguais: {u}")
            pair = tuple(sorted((u, v)))
            self.assertIn(pair, fixture_pairs, f"Arco {pair} é espúrio (não existe na fixture)")

        # (b) há exatamente 2 arcos (fw/bw) por link de entrada — 152 em Sioux Falls
        self.assertEqual(len(highway_feats), 152)
        by_link = {}
        for feat in highway_feats:
            by_link.setdefault(feat['link_id'], []).append(feat['sentido'])
        self.assertEqual(len(by_link), 76)
        for lid, sentidos in by_link.items():
            self.assertEqual(sorted(sentidos), ['bw', 'fw'])

        # (c) há exatamente 2 conectores por zona conectada — 48 em Sioux Falls —, cada um
        # ligando o centróide da zona ao zone_node[zona] e nada mais
        self.assertEqual(len(connector_feats), 48)
        zone_keys = list(range(1, 25))
        zone_connectors = {z: [] for z in zone_keys}
        for feat in connector_feats:
            pts = feat.geometry().asPolyline()
            self.assertEqual(len(pts), 2)
            p0 = (pts[0].x(), pts[0].y())
            p1 = (pts[-1].x(), pts[-1].y())
            matched_z = None
            for z in zone_keys:
                c_pt = nodes_work[z]
                zn_pt = anchors[z]
                fw_match = (math.hypot(p0[0] - c_pt[0], p0[1] - c_pt[1]) <= 1.0 and
                            math.hypot(p1[0] - zn_pt[0], p1[1] - zn_pt[1]) <= 1.0)
                bw_match = (math.hypot(p0[0] - zn_pt[0], p0[1] - zn_pt[1]) <= 1.0 and
                            math.hypot(p1[0] - c_pt[0], p1[1] - c_pt[1]) <= 1.0)
                if fw_match or bw_match:
                    matched_z = z
                    break
            self.assertIsNotNone(matched_z, f"Conector {p0}->{p1} não corresponde a nenhuma zona")
            zone_connectors[matched_z].append(feat)

        for z in zone_keys:
            conns = zone_connectors[z]
            self.assertEqual(len(conns), 2, f"Zona {z} deve ter exatamente 2 conectores")
            self.assertEqual(sorted([c['sentido'] for c in conns]), ['bw', 'fw'])

        # (d) nenhum arco é laço (extremidades iguais) fora dos conectores de comprimento zero
        for feat in features:
            pts = feat.geometry().asPolyline()
            p0 = (pts[0].x(), pts[0].y())
            p1 = (pts[-1].x(), pts[-1].y())
            dist = math.hypot(p0[0] - p1[0], p0[1] - p1[1])
            if dist <= 1.0:
                self.assertEqual(feat['link_id'], 'conector', f"Laço em arco que não é conector: {feat['link_id']}")
                self.assertAlmostEqual(feat['comp_m'], 0.0, delta=1.0)
            else:
                self.assertGreater(dist, 1.0)

        # (e) todo arco com fluxo > 0 satisfaz (a) ou (c)
        flow_gt0 = [f for f in features if float(f['volume']) > 0.0]
        self.assertGreater(len(flow_gt0), 0)
        for feat in flow_gt0:
            if feat['link_id'] != 'conector':
                pts = feat.geometry().asPolyline()
                u = match_node((pts[0].x(), pts[0].y()), tol=1.0)
                v = match_node((pts[-1].x(), pts[-1].y()), tol=1.0)
                self.assertIsNotNone(u)
                self.assertIsNotNone(v)
                self.assertIn(tuple(sorted((u, v))), fixture_pairs)
            else:
                self.assertIn(feat, connector_feats)

        # Mais um caso: os 38 pares da fixture aparecem todos na camada e stats['unreachable'] == 0
        pairs_in_layer = set()
        for feat in highway_feats:
            pts = feat.geometry().asPolyline()
            u = match_node((pts[0].x(), pts[0].y()), tol=1.0)
            v = match_node((pts[-1].x(), pts[-1].y()), tol=1.0)
            pairs_in_layer.add(tuple(sorted((u, v))))

        self.assertEqual(pairs_in_layer, fixture_pairs)
        self.assertEqual(len(pairs_in_layer), 38)
        self.assertEqual(stats['unreachable'], 0)
        self.assertEqual(stats['allocated'], 552)

    def test_end_to_end_aon(self):
        """Regressão ponta a ponta Sioux Falls com AoN (D6)."""
        out_layer, stats, panel, _zone_node = self._run_sioux_falls_assignment('aon')
        self._assert_d6_layer(out_layer, stats, panel, panel.traffic_anchors)

    def test_end_to_end_msa(self):
        """Regressão ponta a ponta Sioux Falls com MSA max_iter=20 (D6)."""
        out_layer, stats, panel, _zone_node = self._run_sioux_falls_assignment(
            'msa', max_iter=20)
        self._assert_d6_layer(out_layer, stats, panel, panel.traffic_anchors)

