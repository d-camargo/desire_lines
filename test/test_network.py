# coding=utf-8
"""Testes unitários para o módulo de rede (network.py)."""

import unittest
from unittest.mock import MagicMock, patch
from desire_lines.traffic import graph, network
from desire_lines.traffic.network import (
    Arc,
    node_key,
    extract_points,
    calculate_length_m,
    calculate_free_flow_time,
    build_directed_arcs,
    build_network,
    clip_and_clean,
    connect_centroids,
    reproject_layer,
)


class TestNetworkModule(unittest.TestCase):
    """Testes unitários do módulo network.py."""

    def test_node_key(self):
        """Testa o arredondamento de coordenadas em node_key."""
        pt1 = (100.12345, 200.67891)
        self.assertEqual(node_key(pt1, precision=3), (100.123, 200.679))
        self.assertEqual(node_key(pt1, precision=1), (100.1, 200.7))

    def test_extract_points(self):
        """Testa extração de pontos a partir de listas e dicts GeoJSON."""
        pts = [(0, 0), (100, 0), (100, 100)]
        self.assertEqual(extract_points(pts), [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])

        geojson_line = {
            'type': 'LineString',
            'coordinates': [[0, 0], [10, 20]],
        }
        self.assertEqual(extract_points(geojson_line), [(0.0, 0.0), (10.0, 20.0)])

    def test_calculate_length_m(self):
        """Testa cálculo de comprimento em metros."""
        pts = [(0.0, 0.0), (300.0, 400.0)]
        self.assertAlmostEqual(calculate_length_m(pts), 500.0)

    def test_calculate_free_flow_time(self):
        """Testa tempo de viagem a fluxo livre (t0 em minutos)."""
        # 10 km a 100 km/h = 0.1h = 6 minutos
        t0 = calculate_free_flow_time(10000.0, 100.0)
        self.assertAlmostEqual(t0, 6.0)

    def test_build_directed_arcs(self):
        """Testa criação de arcos direto e reverso para um link (D5)."""
        pts = [(0.0, 0.0), (1000.0, 0.0)]
        feature = {
            'tipo_pista': 'duplicada',
            'faixas': 2,
            'vel_livre': 100.0,
        }
        fw, bw = build_directed_arcs(link_id=1, points=pts, feature=feature)

        self.assertEqual(fw.link_id, 1)
        self.assertEqual(fw.from_node, (0.0, 0.0))
        self.assertEqual(fw.to_node, (1000.0, 0.0))
        self.assertTrue(fw.forward)

        self.assertEqual(bw.link_id, 1)
        self.assertEqual(bw.from_node, (1000.0, 0.0))
        self.assertEqual(bw.to_node, (0.0, 0.0))
        self.assertFalse(bw.forward)

        # 1 km a 100 km/h = 0.6 minutos
        self.assertAlmostEqual(fw.t0, 0.6)
        self.assertAlmostEqual(bw.t0, 0.6)
        self.assertEqual(fw.sources['vel_livre'], 'oficial')

    def test_build_network(self):
        """Testa a construção da rede completa a partir de uma lista de feições."""
        features = [
            {
                'id': 10,
                'geometry': [(0, 0), (1000, 0)],
                'pista': 'simples',
            },
            {
                'id': 20,
                'geometry': [(1000, 0), (2000, 0)],
                'pista': 'duplicada',
                'faixas': 2,
            },
        ]

        arcs = build_network(features)
        # 2 links * 2 sentidos = 4 arcos
        self.assertEqual(len(arcs), 4)

        fw_ids = [arc.arc_id for arc in arcs if arc.forward]
        self.assertEqual(fw_ids, [(10, 'fw'), (20, 'fw')])

    @patch('desire_lines.traffic.network._run_processing_alg')
    def test_reproject_layer(self, mock_run):
        """Testa que reproject_layer chama native:reprojectlayer com TARGET_CRS."""
        mock_run.return_value = {'OUTPUT': 'camada_reprojetada'}
        result = reproject_layer('camada_orig', 'EPSG:32614')

        self.assertEqual(result, 'camada_reprojetada')
        mock_run.assert_called_once_with('native:reprojectlayer', {
            'INPUT': 'camada_orig',
            'TARGET_CRS': 'EPSG:32614',
            'OUTPUT': 'TEMPORARY_OUTPUT',
        })

    @patch('desire_lines.traffic.network._run_processing_alg')
    def test_clip_and_clean_raises_value_error_on_geographic_crs(self, mock_run):
        """Testa que clip_and_clean com camada de crs().isGeographic() == True levanta ValueError e não chama Processing."""
        mock_layer = MagicMock()
        mock_layer.crs.return_value.isGeographic.return_value = True

        with self.assertRaises(ValueError):
            clip_and_clean(
                road_layer=mock_layer,
                bbox=(0, 0, 100, 100),
            )

        mock_run.assert_not_called()

    @patch('desire_lines.traffic.network._run_processing_alg')
    def test_clip_and_clean_pipeline_order(self, mock_run):
        """Testa que clip_and_clean encadeia recorte -> snap -> multipart->single, com o bbox expandido pelo buffer."""
        mock_run.side_effect = [
            {'OUTPUT': 'clipped'},
            {'OUTPUT': 'snapped'},
            {'OUTPUT': 'single'},
        ]

        result = clip_and_clean(
            road_layer='malha_bruta', bbox=(0, 0, 100, 100), buffer_m=10, snap_tol_m=0.5,
        )

        self.assertEqual(result, 'single')
        alg_ids = [call.args[0] for call in mock_run.call_args_list]
        self.assertEqual(alg_ids, [
            'native:extractbyextent', 'native:snapgeometries', 'native:multiparttosingleparts',
        ])

        extent = mock_run.call_args_list[0].args[1]['EXTENT']
        self.assertAlmostEqual(extent.xMinimum(), -10)
        self.assertAlmostEqual(extent.xMaximum(), 110)

        self.assertEqual(mock_run.call_args_list[1].args[1]['TOLERANCE'], 0.5)

    def test_connect_centroids_links_to_nearest_node(self):
        """Testa que um centróide fora da malha gera conector até o nó mais próximo."""
        arcs, _ = build_directed_arcs(link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)])
        centroids = [(10.0, 40.0)]  # a 40 m do nó (0, 0)

        connector_arcs, zone_node, unconnected = connect_centroids(
            [arcs, _], centroids, max_dist_m=50.0,
        )

        self.assertEqual(unconnected, [])
        self.assertEqual(zone_node[0], (0.0, 0.0))
        self.assertEqual(len(connector_arcs), 2)

        fw = next(a for a in connector_arcs if a.forward)
        bw = next(a for a in connector_arcs if not a.forward)
        self.assertEqual(fw.link_id, network.CONNECTOR_LINK_ID)
        self.assertEqual(fw.from_node, (network.CONNECTOR_LINK_ID, 0))
        self.assertEqual(fw.to_node, (0.0, 0.0))
        self.assertEqual(bw.from_node, (0.0, 0.0))
        self.assertEqual(bw.to_node, (network.CONNECTOR_LINK_ID, 0))
        self.assertEqual(fw.geometry, [(10.0, 40.0), (0.0, 0.0)])
        self.assertEqual(bw.geometry, [(0.0, 0.0), (10.0, 40.0)])
        self.assertAlmostEqual(fw.length, (10.0 ** 2 + 40.0 ** 2) ** 0.5)  # hypot(10, 40)

    def test_connect_centroids_same_coordinate_does_not_bridge_disconnected_nodes(self):
        """Testa que dois centróides na mesma coordenada não criam caminho no grafo entre dois nós desconectados (D5)."""
        # Malha sem ligação entre os nós (10.0, 0.0) e (100.0, 0.0)
        arcs1 = build_directed_arcs(link_id=1, points=[(0.0, 0.0), (10.0, 0.0)])
        arcs2 = build_directed_arcs(link_id=2, points=[(100.0, 0.0), (110.0, 0.0)])
        road_arcs = list(arcs1) + list(arcs2)

        # Dois centróides na MESMA coordenada (50.0, 0.0)
        c = (50.0, 0.0)
        far = (999999.0, 999999.0)

        # Centróide 0 perto de nó (10.0, 0.0); centróide 1 perto de nó (100.0, 0.0)
        conns0, _, _ = connect_centroids(list(arcs1), [c, far], max_dist_m=60.0)
        conns1, _, _ = connect_centroids(list(arcs2), [far, c], max_dist_m=60.0)

        self.assertEqual(len(conns0), 2)
        self.assertEqual(len(conns1), 2)

        # Nós virtuais distintos por zona (D5)
        fw0 = next(a for a in conns0 if a.forward)
        fw1 = next(a for a in conns1 if a.forward)
        self.assertEqual(fw0.from_node, (network.CONNECTOR_LINK_ID, 0))
        self.assertEqual(fw1.from_node, (network.CONNECTOR_LINK_ID, 1))

        # Geometria continua com a coordenada real
        self.assertEqual(fw0.geometry[0], c)
        self.assertEqual(fw1.geometry[0], c)

        g = graph.build_graph(road_arcs + conns0 + conns1)
        path, _ = g.path_to((10.0, 0.0), (100.0, 0.0))
        self.assertIsNone(path)

    def test_connect_centroids_beyond_max_dist_is_unconnected_without_exception(self):
        """Testa que um centróide além de max_dist_m é reportado como não conectado, sem lançar exceção."""
        arcs, bw = build_directed_arcs(link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)])
        centroids = [(0.0, 500.0)]  # a 500 m do nó mais próximo

        connector_arcs, zone_node, unconnected = connect_centroids(
            [arcs, bw], centroids, max_dist_m=50.0,
        )

        self.assertEqual(connector_arcs, [])
        self.assertEqual(zone_node, {})
        self.assertEqual(unconnected, [0])


if __name__ == '__main__':
    unittest.main()
