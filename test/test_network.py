# coding=utf-8
"""Testes unitários para o módulo de rede (network.py)."""

import math
import unittest
from unittest.mock import MagicMock, patch
from desire_lines.traffic import assignment, graph, network
from desire_lines.traffic.network import (
    Arc,
    node_key,
    extract_points,
    calculate_length_m,
    calculate_free_flow_time,
    build_directed_arcs,
    build_network,
    clip_and_clean,
    anchor_centroids,
    reproject_layer,
    coords_crs_mismatch,
    DEGREES_SUSPECT_SPAN,
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

    def test_anchor_centroids_projects_onto_link_and_splits_it(self):
        """Centróide a 200 m do meio do link: 2 pedaços proporcionais e conector de 200 m (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'vel_livre': 100.0})

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(500.0, -200.0)], max_dist_m=5000.0)

        # 2 pedaços x 2 sentidos, arc_id=(link_id, sentido, k) na ordem do fw
        self.assertEqual(
            [a.arc_id for a in net_arcs],
            [(1, 'fw', 0), (1, 'bw', 0), (1, 'fw', 1), (1, 'bw', 1)],
        )
        piece_fw_0, piece_bw_0, piece_fw_1, _piece_bw_1 = net_arcs
        self.assertEqual(piece_fw_0.geometry, [(0.0, 0.0), (500.0, 0.0)])
        self.assertEqual(piece_fw_1.geometry, [(500.0, 0.0), (1000.0, 0.0)])
        self.assertEqual(_piece_bw_1.geometry, [(1000.0, 0.0), (500.0, 0.0)])
        # comprimentos e t0 proporcionais: 1000 m a 100 km/h = 0,6 min -> 0,3 por metade
        for piece in (piece_fw_0, piece_fw_1):
            self.assertAlmostEqual(piece.length, 500.0)
            self.assertAlmostEqual(piece.t0, 0.3)
        self.assertAlmostEqual(piece_bw_0.t0, bw.t0 * 0.5)
        # capacidade/escopo/parâmetros vêm do arco original
        self.assertEqual(piece_fw_0.capacity, fw.capacity)
        self.assertEqual(piece_fw_0.scope, fw.scope)
        self.assertEqual(piece_fw_0.params, fw.params)
        self.assertEqual(piece_fw_0.sources, fw.sources)

        # conector de 200 m até o pé da projeção; zona aponta para o nó virtual (D2)
        self.assertEqual(zone_node, {0: (network.CONNECTOR_LINK_ID, 0)})
        conn_fw = next(a for a in connector_arcs if a.forward)
        conn_bw = next(a for a in connector_arcs if not a.forward)
        self.assertEqual(conn_fw.from_node, (network.CONNECTOR_LINK_ID, 0))
        self.assertEqual(conn_fw.to_node, (500.0, 0.0))
        self.assertEqual(conn_bw.from_node, (500.0, 0.0))
        self.assertEqual(conn_bw.to_node, (network.CONNECTOR_LINK_ID, 0))
        self.assertAlmostEqual(conn_fw.length, 200.0)
        self.assertEqual(conn_fw.geometry, [(500.0, -200.0), (500.0, 0.0)])

        self.assertEqual(report['anchors'], {0: (500.0, 0.0)})
        self.assertEqual(report['unconnected'], [])
        self.assertEqual(report['fallback'], [])
        self.assertEqual(report['far'], [])
        self.assertEqual(report['shared_node'], [])
        self.assertEqual(report['shared_link'], {})

    def test_anchor_centroids_near_link_end_anchors_at_node_without_splitting(self):
        """Centróide a 0,3 m da ponta ancora no nó da ponta, sem dividir o link (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'vel_livre': 100.0})

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(1000.3, 0.0)], max_dist_m=50.0)

        # link sai intacto, com os mesmos objetos
        self.assertEqual(len(net_arcs), 2)
        self.assertIs(net_arcs[0], fw)
        self.assertIs(net_arcs[1], bw)

        conn_fw = next(a for a in connector_arcs if a.forward)
        self.assertEqual(conn_fw.to_node, (1000.0, 0.0))
        self.assertAlmostEqual(conn_fw.length, 0.3)
        self.assertEqual(report['anchors'], {0: (1000.0, 0.0)})

    def test_anchor_centroids_two_zones_same_link_three_pieces_and_shared_link(self):
        """Dois centróides em pontos distintos do mesmo link: 3 pedaços e shared_link (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'vel_livre': 100.0})

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(300.0, 10.0), (600.0, 20.0)], max_dist_m=5000.0)

        fw_ids = [a.arc_id for a in net_arcs if a.forward]
        self.assertEqual(fw_ids, [(1, 'fw', 0), (1, 'fw', 1), (1, 'fw', 2)])
        pieces = {a.arc_id: a for a in net_arcs}
        self.assertAlmostEqual(pieces[(1, 'fw', 0)].length, 300.0)
        self.assertAlmostEqual(pieces[(1, 'fw', 1)].length, 300.0)
        self.assertAlmostEqual(pieces[(1, 'fw', 2)].length, 400.0)
        # t0 proporcional: 0,18 / 0,18 / 0,24 min
        self.assertAlmostEqual(pieces[(1, 'fw', 0)].t0, 0.18)
        self.assertAlmostEqual(pieces[(1, 'fw', 2)].t0, 0.24)

        self.assertEqual(report['shared_link'], {1: [0, 1]})
        self.assertEqual(report['shared_node'], [])
        conn_by_zone = {
            z: [a for a in connector_arcs if a.forward
                and a.arc_id == (f'{network.CONNECTOR_LINK_ID}-{z}', 'fw')]
            for z in (0, 1)
        }
        self.assertAlmostEqual(conn_by_zone[0][0].length, 10.0)
        self.assertAlmostEqual(conn_by_zone[1][0].length, 20.0)

    def test_anchor_centroids_same_point_single_node_and_shared_node(self):
        """Dois centróides no mesmo ponto: um único nó de âncora e shared_node (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'vel_livre': 100.0})

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(500.0, 30.0), (500.0, 30.0)], max_dist_m=5000.0)

        fw_ids = [a.arc_id for a in net_arcs if a.forward]
        self.assertEqual(fw_ids, [(1, 'fw', 0), (1, 'fw', 1)])
        self.assertEqual(net_arcs[0].to_node, (500.0, 0.0))
        self.assertEqual(net_arcs[2].from_node, (500.0, 0.0))
        self.assertEqual(report['shared_node'], [[0, 1]])
        self.assertEqual(report['shared_link'], {})
        self.assertEqual(report['anchors'], {0: (500.0, 0.0), 1: (500.0, 0.0)})
        self.assertEqual(len(connector_arcs), 4)   # 2 por zona
        for arc in connector_arcs:
            self.assertAlmostEqual(arc.length, 30.0)

    def test_anchor_centroids_close_nodes_case_anchors_on_l2(self):
        """Caso N1/N2 do D5: (5001.5, 320) projeta em L2 a 1,5 m, não em N1/N2."""
        l2_fw, l2_bw = build_directed_arcs(
            link_id='L2', points=[(5000.0, 300.0), (5000.0, 5000.0)])
        l3_fw, l3_bw = build_directed_arcs(
            link_id='L3', points=[(5003.0, 300.0), (10000.0, 5000.0)])

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [l2_fw, l2_bw, l3_fw, l3_bw], [(5001.5, 320.0)], max_dist_m=5000.0)

        # âncora no pé da projeção sobre L2, não nos nós N1 (5000,300)/N2 (5003,300)
        self.assertEqual(report['anchors'], {0: (5000.0, 320.0)})
        conn_fw = next(a for a in connector_arcs if a.forward)
        self.assertEqual(conn_fw.to_node, (5000.0, 320.0))
        self.assertAlmostEqual(conn_fw.length, 1.5)

        # L2 dividido em 2 pedaços; L3 intacto, com os mesmos objetos
        self.assertEqual(
            [a.arc_id for a in net_arcs],
            [('L2', 'fw', 0), ('L2', 'bw', 0), ('L2', 'fw', 1), ('L2', 'bw', 1),
             ('L3', 'fw'), ('L3', 'bw')],
        )
        self.assertIs(net_arcs[4], l3_fw)
        self.assertIs(net_arcs[5], l3_bw)
        self.assertEqual(report['fallback'], [])

    def test_anchor_centroids_equidistant_parallel_links_fall_back_to_node(self):
        """Links paralelos equidistantes: fallback no nó mais próximo (D1)."""
        a1_fw, a1_bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)])
        a2_fw, a2_bw = build_directed_arcs(
            link_id=2, points=[(500.0, 100.0), (1000.0, 100.0)])

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [a1_fw, a1_bw, a2_fw, a2_bw], [(600.0, 50.0)], max_dist_m=5000.0)

        self.assertEqual(report['fallback'], [0])
        self.assertEqual(report['anchors'], {0: (500.0, 100.0)})
        # malha intacta (mesmos objetos) e conector até o nó mais próximo
        self.assertIs(net_arcs[0], a1_fw)
        self.assertIs(net_arcs[1], a1_bw)
        self.assertIs(net_arcs[2], a2_fw)
        self.assertIs(net_arcs[3], a2_bw)
        conn_fw = next(a for a in connector_arcs if a.forward)
        self.assertEqual(conn_fw.to_node, (500.0, 100.0))
        self.assertAlmostEqual(conn_fw.length, math.hypot(100.0, 50.0))

    def test_anchor_centroids_beyond_max_dist_is_unconnected_without_exception(self):
        """Centróide além de max_dist_m é reportado em unconnected, sem lançar exceção (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)])

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(0.0, 500.0)], max_dist_m=50.0)

        self.assertEqual(connector_arcs, [])
        self.assertEqual(zone_node, {})
        self.assertIs(net_arcs[0], fw)
        self.assertIs(net_arcs[1], bw)
        self.assertEqual(len(report['unconnected']), 1)
        zone_idx, dist = report['unconnected'][0]
        self.assertEqual(zone_idx, 0)
        self.assertAlmostEqual(dist, 500.0)
        self.assertEqual(report['anchors'], {})

    def test_anchor_centroids_connector_longer_than_warn_m_is_far(self):
        """Conector de 1500 m (> CONNECTOR_WARN_M) vira report['far'] (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)])

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(500.0, -1500.0)], max_dist_m=5000.0)

        self.assertEqual(zone_node, {0: (network.CONNECTOR_LINK_ID, 0)})
        self.assertEqual(report['far'], [(0, 1500.0)])
        self.assertEqual(report['unconnected'], [])
        conn_fw = next(a for a in connector_arcs if a.forward)
        self.assertAlmostEqual(conn_fw.length, 1500.0)

    def test_anchor_centroids_connector_routes_and_pieces_carry_the_flow(self):
        """assign() com method='aon': fluxo nos 2 conectores e nos pedaços certos (D2)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'vel_livre': 100.0})

        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw, bw], [(300.0, -100.0), (700.0, 100.0)], max_dist_m=5000.0)

        self.assertEqual(zone_node,
                         {0: (network.CONNECTOR_LINK_ID, 0),
                          1: (network.CONNECTOR_LINK_ID, 1)})

        all_arcs = net_arcs + connector_arcs
        g = graph.build_graph(all_arcs)
        flows, _historico, stats = assignment.assign(
            g, all_arcs, od_pairs=[(0, 1, 100.0)], method='aon',
            zone_node=zone_node)

        self.assertEqual(stats['allocated'], 1)

        def flow_of(arc_id):
            return flows[g.index_of(arc_id)]

        self.assertEqual(
            flow_of((f'{network.CONNECTOR_LINK_ID}-0', 'fw')), 100.0)
        self.assertEqual(flow_of((1, 'fw', 1)), 100.0)   # pedaço 300 m -> 700 m
        self.assertEqual(
            flow_of((f'{network.CONNECTOR_LINK_ID}-1', 'bw')), 100.0)
        for arc_id in [
            (1, 'fw', 0), (1, 'fw', 2),
            (1, 'bw', 0), (1, 'bw', 1), (1, 'bw', 2),
            (f'{network.CONNECTOR_LINK_ID}-0', 'bw'),
            (f'{network.CONNECTOR_LINK_ID}-1', 'fw'),
        ]:
            self.assertEqual(flow_of(arc_id), 0.0, arc_id)

    def test_anchor_centroids_link_without_centroid_keeps_same_arcs(self):
        """Link sem centróide sai como o mesmo objeto Arc (D1)."""
        a_fw, a_bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (100.0, 0.0)])
        b_fw, b_bw = build_directed_arcs(
            link_id=2, points=[(100.0, 0.0), (100.0, 100.0)])

        net_arcs, _connectors, _zone_node, _report = anchor_centroids(
            [a_fw, a_bw, b_fw, b_bw], [(50.0, -20.0)], max_dist_m=5000.0)

        # link 1 dividido (2 pedaços x 2 sentidos); link 2 sai com os mesmos objetos
        self.assertEqual(len(net_arcs), 6)
        self.assertIs(net_arcs[4], b_fw)
        self.assertIs(net_arcs[5], b_bw)

    def test_anchor_centroids_coincident_zones_do_not_bridge_disconnected_nodes(self):
        """Zonas coincidentes não criam caminho entre nós de malhas desconectadas (D2)."""
        # Malha sem ligação entre os nós (10.0, 0.0) e (100.0, 0.0)
        arcs1 = build_directed_arcs(link_id=1, points=[(0.0, 0.0), (10.0, 0.0)])
        arcs2 = build_directed_arcs(link_id=2, points=[(100.0, 0.0), (110.0, 0.0)])
        road_arcs = list(arcs1) + list(arcs2)

        # Dois centróides na MESMA coordenada (50.0, 0.0): ambos ancoram na
        # ponta (10, 0) do link 1, cada um no seu nó virtual.
        _net, connectors, zone_node, report = anchor_centroids(
            road_arcs, [(50.0, 0.0), (50.0, 0.0)], max_dist_m=60.0)

        self.assertEqual(len(connectors), 4)
        self.assertEqual(
            sorted(zone_node.values()),
            [(network.CONNECTOR_LINK_ID, 0), (network.CONNECTOR_LINK_ID, 1)])
        self.assertEqual(report['shared_node'], [[0, 1]])

        g = graph.build_graph(road_arcs + connectors)
        path, _cost = g.path_to((10.0, 0.0), (100.0, 0.0))
        self.assertIsNone(path)

    def test_coords_crs_mismatch(self):
        """Testa guarda de incompatibilidade entre CRS e coordenadas (D8)."""
        self.assertEqual(DEGREES_SUSPECT_SPAN, 10.0)

        # Lon/lat com CRS projetado (False) -> 'degrees_in_projected', com geográfico (True) -> None
        self.assertEqual(
            coords_crs_mismatch((-96.84, 43.49, -96.69, 43.62), False),
            'degrees_in_projected',
        )
        self.assertIsNone(
            coords_crs_mismatch((-96.84, 43.49, -96.69, 43.62), True)
        )

        # Metros com CRS geográfico (True) -> 'out_of_geographic_range', com projetado (False) -> None
        self.assertEqual(
            coords_crs_mismatch((50000, 50000, 420000, 510000), True),
            'out_of_geographic_range',
        )
        self.assertIsNone(
            coords_crs_mismatch((50000, 50000, 420000, 510000), False)
        )

        # Metros normais em CRS projetado (False) -> None
        self.assertIsNone(
            coords_crs_mismatch((680000, 4820000, 700000, 4835000), False)
        )

        # Extent degenerado (ponto) em projetado (False) -> None
        self.assertIsNone(
            coords_crs_mismatch((-96.7, 43.6, -96.7, 43.6), False)
        )

        # Extent com span grande fora do limite geográfico em projetado (False) -> None
        self.assertIsNone(
            coords_crs_mismatch((0, 0, 500, 300), False)
        )

    def test_build_directed_arcs_capacidade_and_scope(self):
        """Capacidade > 0 substitui HCM e mantém scope; 0 cai no HCM (D1)."""
        # Rural com capacidade informada > 0
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'capacidade': 2500.0})
        self.assertEqual(fw.capacity, 2500.0)
        self.assertEqual(bw.capacity, 2500.0)
        self.assertEqual(fw.scope, 'rodoviario')
        self.assertEqual(bw.scope, 'rodoviario')

        # Trecho urbano com capacidade informada > 0 mantém scope 'urbano'
        fw_u, bw_u = build_directed_arcs(
            link_id=2, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'capacidade': 3000.0, 'urbano': True})
        self.assertEqual(fw_u.capacity, 3000.0)
        self.assertEqual(fw_u.scope, 'urbano')
        self.assertEqual(bw_u.capacity, 3000.0)
        self.assertEqual(bw_u.scope, 'urbano')

        # Capacidade = 0 cai no HCM
        fw_0, _ = build_directed_arcs(
            link_id=3, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'capacidade': 0.0})
        fw_def, _ = build_directed_arcs(
            link_id=4, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={})
        self.assertEqual(fw_0.capacity, fw_def.capacity)
        self.assertGreater(fw_0.capacity, 0.0)
        self.assertEqual(fw_0.scope, 'rodoviario')

    def test_build_directed_arcs_tempo_livre(self):
        """tempo_livre > 0 vira t0 exato; 0 cai em comprimento ÷ vel_livre (D1)."""
        # tempo_livre > 0
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'tempo_livre': 4.5, 'vel_livre': 60.0})
        self.assertAlmostEqual(fw.t0, 4.5)
        self.assertAlmostEqual(bw.t0, 4.5)

        # tempo_livre = 0 calcula via comprimento ÷ vel_livre (1 km a 60 km/h = 1.0 min)
        fw_0, _ = build_directed_arcs(
            link_id=2, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'tempo_livre': 0.0, 'vel_livre': 60.0})
        self.assertAlmostEqual(fw_0.t0, 1.0)

    def test_build_directed_arcs_mao_unica_and_build_network(self):
        """mao_unica=True gera só fw; build_network não anexa None (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'mao_unica': True})
        self.assertIsNotNone(fw)
        self.assertIsNone(bw)
        self.assertEqual(fw.arc_id, (1, 'fw'))
        self.assertTrue(fw.forward)

        # build_network não anexa None
        features = [
            {'id': 1, 'geometry': [(0.0, 0.0), (1000.0, 0.0)], 'mao_unica': True},
            {'id': 2, 'geometry': [(1000.0, 0.0), (2000.0, 0.0)], 'mao_unica': False},
        ]
        arcs = build_network(features)
        self.assertEqual(len(arcs), 3)
        self.assertNotIn(None, arcs)
        self.assertEqual([a.arc_id for a in arcs], [(1, 'fw'), (2, 'fw'), (2, 'bw')])

    def test_anchor_centroids_oneway_split_and_aon_routing(self):
        """anchor_centroids com link só-fw dividido no meio gera só pedaços fw
        e o AoN atravessa no sentido certo e não no oposto (D1)."""
        fw, bw = build_directed_arcs(
            link_id=1, points=[(0.0, 0.0), (1000.0, 0.0)],
            feature={'mao_unica': True, 'vel_livre': 100.0})
        self.assertIsNone(bw)

        # Link dividido em 3 pedaços por centróides projetados em x=300 e x=700
        net_arcs, connector_arcs, zone_node, report = anchor_centroids(
            [fw], [(300.0, -100.0), (700.0, 100.0)], max_dist_m=5000.0)

        self.assertEqual(len(net_arcs), 3)
        self.assertTrue(all(a.forward for a in net_arcs))
        self.assertEqual([a.arc_id for a in net_arcs],
                         [(1, 'fw', 0), (1, 'fw', 1), (1, 'fw', 2)])

        all_arcs = net_arcs + connector_arcs
        g = graph.build_graph(all_arcs)

        # Sentido direto (0 -> 1): deve alocar com sucesso pelo pedaço (1, 'fw', 1)
        flows_fwd, _hist, stats_fwd = assignment.assign(
            g, all_arcs, od_pairs=[(0, 1, 100.0)], method='aon',
            zone_node=zone_node)
        self.assertEqual(stats_fwd['allocated'], 1)
        self.assertEqual(stats_fwd['unreachable'], 0)
        idx_fw1 = g.index_of((1, 'fw', 1))
        self.assertEqual(flows_fwd[idx_fw1], 100.0)

        # Sentido oposto (1 -> 0): sem caminho reverso numa via de mão única
        flows_rev, _hist, stats_rev = assignment.assign(
            g, all_arcs, od_pairs=[(1, 0, 100.0)], method='aon',
            zone_node=zone_node)
        self.assertEqual(stats_rev['allocated'], 0)
        self.assertEqual(stats_rev['unreachable'], 1)
        self.assertEqual(flows_rev[idx_fw1], 0.0)
        self.assertEqual(sum(flows_rev), 0.0)


if __name__ == '__main__':
    unittest.main()
